"""Zotero side: enumerate items from the local SQLite (read-only); write notes/tags via pyzotero."""
from __future__ import annotations
import html as html_mod
import json, os, re, sqlite3
from dataclasses import dataclass
from pathlib import Path
from pyzotero import zotero
from pyzotero.zotero_errors import PreConditionFailedError as PreConditionFailed  # HTTP 412
from . import NOTE_TITLE
from .normalize import DocRecord

DEFAULT_ZOTERO_SQLITE = Path("/Users/andrew.mueller/Library/CloudStorage/OneDrive-UniversityofDenver/Zotero/zotero.sqlite")
DEFAULT_PREFS = next(iter(Path.home().glob("Library/Application Support/Zotero/Profiles/*/prefs.js")), None)


class WriteConflict(RuntimeError):
    pass


@dataclass
class ZoteroItem:
    key: str
    title: str
    year: int | None
    tags: list[str]


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def resolve_library(spec: str, zotero_sqlite: Path = DEFAULT_ZOTERO_SQLITE) -> tuple[str, str, int]:
    if spec == "user":
        user_id = os.environ.get("ZOTERO_USER_ID")
        if not user_id:
            raise RuntimeError("ZOTERO_USER_ID not set (source ~/.secrets.env)")
        return "user", user_id, 1
    m = re.fullmatch(r"group:(\d+)", spec)
    if not m:
        raise ValueError(f"library spec must be 'user' or 'group:<groupID>', got {spec!r}")
    con = _ro(zotero_sqlite)
    row = con.execute("SELECT libraryID FROM groups WHERE groupID=?", (int(m.group(1)),)).fetchone()
    con.close()
    if not row:
        raise ValueError(f"group {m.group(1)} not in local Zotero database")
    return "group", m.group(1), int(row[0])


def enumerate_items(zotero_sqlite: Path, library_id: int, collection_name: str | None) -> list[ZoteroItem]:
    con = _ro(zotero_sqlite)
    sql = """
    SELECT i.itemID, i.key,
      (SELECT v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID
         WHERE d.itemID=i.itemID AND f.fieldName='title') AS title,
      (SELECT v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID
         WHERE d.itemID=i.itemID AND f.fieldName='date') AS date
    FROM items i JOIN itemTypes t ON t.itemTypeID=i.itemTypeID
    WHERE i.libraryID=? AND t.typeName NOT IN ('attachment','note','annotation')
      AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
    """
    params: list = [library_id]
    if collection_name:
        sql += " AND i.itemID IN (SELECT ci.itemID FROM collectionItems ci JOIN collections c ON c.collectionID=ci.collectionID WHERE c.libraryID=? AND c.collectionName=?)"
        params += [library_id, collection_name]
    sql += " ORDER BY i.key"
    items = []
    for item_id, key, title, date in con.execute(sql, params):
        tags = [r[0] for r in con.execute("SELECT t.name FROM itemTags it JOIN tags t ON t.tagID=it.tagID WHERE it.itemID=? ORDER BY t.name", (item_id,))]
        year = int(date[:4]) if date and date[:4].isdigit() else None
        items.append(ZoteroItem(key, title or "", year, tags))
    con.close()
    return items


def check_autosync(prefs_js: Path | None = DEFAULT_PREFS) -> bool | None:
    if not prefs_js or not Path(prefs_js).exists():
        return None
    m = re.search(r'"extensions\.zotero\.sync\.autoSync",\s*(true|false)', Path(prefs_js).read_text())
    return None if not m else m.group(1) == "true"


def _v1_json(doc: DocRecord) -> dict:
    names = [d.name_raw for d in doc.datasets]
    variables = [v.name_raw for d in doc.datasets for v in d.variables]
    units = sorted({d.unit for d in doc.datasets if d.unit})
    years = [y for d in doc.datasets for y in (d.period_start, d.period_end) if y]
    access = sorted({d.access for d in doc.datasets if d.access})
    return {"datasets": names, "variables": variables, "unit": "; ".join(units),
            "timespan": f"{min(years)}-{max(years)}" if years else "", "access": "; ".join(access),
            "source": "full-text", "schema": "v2"}


def render_note_html(doc: DocRecord, title: str, pass_id: int, vocab_version: int, model: str) -> str:
    esc = html_mod.escape
    parts = [f"<h1>{esc(NOTE_TITLE)}</h1>", f"<p>{esc(json.dumps(_v1_json(doc)))}</p>",
             "<table><tr><th>Dataset</th><th>Type</th><th>Geography</th><th>Period</th><th>Variables</th><th>Pages</th></tr>"]
    for d in doc.datasets:
        period = "–".join(str(y) for y in (d.period_start, d.period_end) if y) or "?"
        geo = esc(d.geo_text or "") + (f" ({d.geo_level})" if d.geo_level else "")
        variables = ", ".join(f"<b>{esc(v.name_raw)}</b>" if v.role == "dependent" else esc(v.name_raw) for v in d.variables)
        pages = ", ".join(f"p. {e.page_num}" if e.page_num is not None else f"chunk {e.chunk_index}" for e in d.evidence)
        name = esc(d.name_raw) + (f" <code>{d.src_slug}</code>" if d.src_slug else " <i>(unlisted)</i>")
        parts.append(f"<tr><td>{name}</td><td>{esc(d.type_slug)}</td><td>{geo}</td><td>{period}</td><td>{variables}</td><td>{pages}</td></tr>")
    parts.append("</table>")
    chunk_ids = ", ".join(str(e.chunk_index) for d in doc.datasets for e in d.evidence)
    parts.append(f"<p><small>ztp-data-tag v2 · pass {pass_id} · vocab v{vocab_version} · {esc(model)} · chunks {chunk_ids} · {esc(title)}</small></p>")
    return "".join(parts)


class ZoteroWriterV2:
    last_note_created: bool | None = None  # set by upsert_note: True if created, False if updated

    def __init__(self, api_key: str, api_id: str, lib_type: str):
        self.last_note_created = None
        self._zot = zotero.Zotero(api_id, lib_type, api_key)

    def _send_update(self, item: dict) -> None:
        """One update_item call. Real pyzotero raises on non-2xx (tested), but a response-like
        return is also checked so a silent 412/403/404 can never pass as success."""
        result = self._zot.update_item(item["data"])
        status = getattr(result, "status_code", None)
        if isinstance(status, int):
            if status == 412:
                raise PreConditionFailed("412")
            if not 200 <= status < 300:
                raise RuntimeError(f"update_item failed with HTTP {status} on {item.get('key')}")

    def _update_with_retry(self, fetch, mutate) -> dict:
        # pyzotero update_item takes the inner item["data"] dict (a full wrapper with extra
        # top-level keys is rejected by check_items); it reads data["key"] and data["version"].
        item = fetch()
        mutate(item)
        try:
            self._send_update(item); return item
        except PreConditionFailed:
            item = fetch(); mutate(item)
            try:
                self._send_update(item); return item
            except PreConditionFailed as exc:
                raise WriteConflict(f"412 twice on {item.get('key')}") from exc

    def _find_note(self, item_key: str) -> dict | None:
        for child in self._zot.children(item_key, itemType="note"):
            if f"<h1>{NOTE_TITLE}</h1>" in (child.get("data") or {}).get("note", ""):
                return child
        return None

    def upsert_note(self, item_key: str, note_html: str) -> str:
        existing = self._find_note(item_key)
        if existing:
            def mutate(n): n["data"]["note"] = note_html
            self._update_with_retry(lambda: self._zot.item(existing["key"]), mutate)
            self.last_note_created = False
            return existing["key"]
        template = self._zot.item_template("note")
        self._zot.url_params = None
        template["parentItem"], template["note"], template["tags"] = item_key, note_html, []
        result = self._zot.create_items([template])
        if not result.get("success"):
            raise RuntimeError(f"note create failed: {result}")
        self.last_note_created = True
        return list(result["success"].values())[0]

    def merge_tags(self, item_key: str, tags: list[str]) -> list[str]:
        added: list[str] = []
        def mutate(item):
            existing = {t["tag"] for t in item["data"].get("tags", [])}
            added[:] = sorted(set(tags) - existing)
            # keep existing tag dicts untouched (preserves "type"); append only new tags
            item["data"]["tags"] = list(item["data"].get("tags", [])) + [{"tag": t} for t in added]
        self._update_with_retry(lambda: self._zot.item(item_key), mutate)
        return added
