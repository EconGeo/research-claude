"""The sidecar SQLite: source of truth for every pass, dataset, variable and evidence row."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .normalize import DocRecord

DEFAULT_SIDECAR = Path(os.environ.get("DATA_TAGS_DB", Path.home() / ".local/share/zotpilot/data_tags.sqlite"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS passes (pass_id INTEGER PRIMARY KEY, library TEXT, collection TEXT, n_docs INTEGER,
    vocab_version INTEGER, model TEXT, started_utc TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, library_id TEXT, title TEXT, year INTEGER,
    pass_id INTEGER, status TEXT, llm_notes TEXT, dropped_json TEXT);
CREATE TABLE IF NOT EXISTS datasets (id INTEGER PRIMARY KEY, doc_id TEXT, pass_id INTEGER, name_raw TEXT, provider TEXT,
    src_slug TEXT, type_slug TEXT, geo_text TEXT, geo_level TEXT, places_json TEXT, period_start INTEGER,
    period_end INTEGER, unit TEXT, access TEXT, confidence REAL, source TEXT);
CREATE TABLE IF NOT EXISTS variables (id INTEGER PRIMARY KEY, dataset_id INTEGER, name_raw TEXT, slug TEXT, role TEXT, dv_class TEXT);
CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, dataset_id INTEGER, chunk_index INTEGER, page_num INTEGER, snippet TEXT);
CREATE TABLE IF NOT EXISTS review_queue (id INTEGER PRIMARY KEY, pass_id INTEGER, kind TEXT, name_raw TEXT, doc_id TEXT,
    suggested_slug TEXT, snippet TEXT, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS zotero_writes (id INTEGER PRIMARY KEY, doc_id TEXT, pass_id INTEGER, tags_json TEXT,
    note_key TEXT, written_utc TEXT, undone_utc TEXT, prev_note_html TEXT, note_created INTEGER);
CREATE INDEX IF NOT EXISTS ix_datasets_doc ON datasets(doc_id);
CREATE INDEX IF NOT EXISTS ix_datasets_type ON datasets(type_slug);
CREATE INDEX IF NOT EXISTS ix_datasets_src ON datasets(src_slug);
"""


class Sidecar:
    def __init__(self, path: Path | str = DEFAULT_SIDECAR):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(self.path); self._con.row_factory = sqlite3.Row
        self._con.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Idempotent: add zotero_writes columns that DBs created by earlier versions lack."""
        have = {r[1] for r in self._con.execute("PRAGMA table_info(zotero_writes)")}
        for col, decl in (("undone_utc", "TEXT"), ("prev_note_html", "TEXT"), ("note_created", "INTEGER")):
            if col not in have:
                self._con.execute(f"ALTER TABLE zotero_writes ADD COLUMN {col} {decl}")
        self._con.commit()

    # ---- passes -------------------------------------------------------------
    def begin_pass(self, pass_id: int, library: str, collection: str | None, vocab_version: int, model: str, n_docs: int) -> None:
        con = self._con
        with con:  # atomic: commit on success, roll back on error
            doc_ids = [r[0] for r in con.execute("SELECT doc_id FROM documents WHERE pass_id=?", (pass_id,))]
            for doc_id in doc_ids:
                self._delete_doc_rows(doc_id)
            con.execute("DELETE FROM review_queue WHERE pass_id=? AND status='open'", (pass_id,))
            con.execute("INSERT OR REPLACE INTO passes VALUES (?,?,?,?,?,?,?,?)",
                        (pass_id, library, collection, n_docs, vocab_version, model, datetime.now(timezone.utc).isoformat(timespec="seconds"), ""))

    def passes(self) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM passes ORDER BY pass_id").fetchall()

    # ---- documents ----------------------------------------------------------
    def _delete_doc_rows(self, doc_id: str) -> None:
        con = self._con
        ids = [r[0] for r in con.execute("SELECT id FROM datasets WHERE doc_id=?", (doc_id,))]
        if ids:
            marks = ",".join("?" * len(ids))
            con.execute(f"DELETE FROM variables WHERE dataset_id IN ({marks})", ids)
            con.execute(f"DELETE FROM evidence WHERE dataset_id IN ({marks})", ids)
        con.execute("DELETE FROM datasets WHERE doc_id=?", (doc_id,))
        con.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        con.execute("DELETE FROM review_queue WHERE doc_id=? AND status='open'", (doc_id,))

    def write_doc(self, doc: DocRecord, pass_id: int, title: str, year: int | None, library_id: str) -> None:
        con = self._con
        with con:  # atomic: a failed insert rolls back the whole doc
            self._delete_doc_rows(doc.doc_id)
            con.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                        (doc.doc_id, library_id, title, year, pass_id, doc.status, doc.llm_notes, json.dumps(doc.dropped)))
            for d in doc.datasets:
                cur = con.execute("INSERT INTO datasets (doc_id,pass_id,name_raw,provider,src_slug,type_slug,geo_text,geo_level,"
                                  "places_json,period_start,period_end,unit,access,confidence,source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (doc.doc_id, pass_id, d.name_raw, d.provider, d.src_slug, d.type_slug, d.geo_text, d.geo_level,
                                   json.dumps(d.places), d.period_start, d.period_end, d.unit, d.access, d.confidence, d.source))
                ds_id = cur.lastrowid
                con.executemany("INSERT INTO variables (dataset_id,name_raw,slug,role,dv_class) VALUES (?,?,?,?,?)",
                                [(ds_id, v.name_raw, v.slug, v.role, v.dv_class) for v in d.variables])
                con.executemany("INSERT INTO evidence (dataset_id,chunk_index,page_num,snippet) VALUES (?,?,?,?)",
                                [(ds_id, e.chunk_index, e.page_num, e.snippet) for e in d.evidence])
            con.executemany("INSERT INTO review_queue (pass_id,kind,name_raw,doc_id,suggested_slug,snippet) VALUES (?,?,?,?,?,?)",
                            [(pass_id, r.kind, r.name_raw, doc.doc_id, r.suggested_slug, r.snippet) for r in doc.review])

    def set_doc_status(self, doc_id: str, status: str) -> None:
        self._con.execute("UPDATE documents SET status=? WHERE doc_id=?", (status, doc_id)); self._con.commit()

    def written_tags(self, doc_id: str, pass_id: int, tags: list[str], note_key: str | None,
                     prev_note_html: str | None = None, note_created: bool | None = None) -> int:
        """Log one Zotero write; returns the row id. note_created=None means 'created iff note_key'."""
        created = bool(note_key) if note_created is None else bool(note_created)
        cur = self._con.execute(
            "INSERT INTO zotero_writes (doc_id,pass_id,tags_json,note_key,written_utc,prev_note_html,note_created) VALUES (?,?,?,?,?,?,?)",
            (doc_id, pass_id, json.dumps(tags), note_key, datetime.now(timezone.utc).isoformat(timespec="seconds"),
             prev_note_html, int(created)))
        self._con.commit()
        return cur.lastrowid

    def set_write_tags(self, row_id: int, tags: list[str]) -> None:
        self._con.execute("UPDATE zotero_writes SET tags_json=? WHERE id=?", (json.dumps(tags), row_id)); self._con.commit()

    def mark_undone(self, row_id: int) -> None:
        self._con.execute("UPDATE zotero_writes SET undone_utc=? WHERE id=?",
                          (datetime.now(timezone.utc).isoformat(timespec="seconds"), row_id)); self._con.commit()

    def doc_ids_in_pass(self, pass_id: int) -> list[str]:
        return [r["doc_id"] for r in self.docs_in_pass(pass_id)]

    def empty_doc_ids(self, statuses: tuple[str, ...] = ("ok", "no_candidates")) -> set[str]:
        """Docs processed with a terminal status but no dataset rows: they never get the v2 marker."""
        marks = ",".join("?" * len(statuses))
        rows = self._con.execute(
            f"SELECT doc_id FROM documents d WHERE status IN ({marks}) "
            "AND NOT EXISTS (SELECT 1 FROM datasets WHERE doc_id=d.doc_id)", statuses).fetchall()
        return {r[0] for r in rows}

    def written_doc_ids(self, retry_statuses: tuple[str, ...] = ("write_conflict", "write_error")) -> set[str]:
        """Docs with a Zotero write not yet undone. Docs whose latest sidecar status is a failed
        write are excluded so a later pass retries them."""
        marks = ",".join("?" * len(retry_statuses))
        rows = self._con.execute(
            "SELECT DISTINCT w.doc_id FROM zotero_writes w WHERE w.undone_utc IS NULL "
            f"AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.doc_id=w.doc_id AND d.status IN ({marks}))",
            retry_statuses).fetchall()
        return {r[0] for r in rows}

    # ---- reads --------------------------------------------------------------
    def docs_in_pass(self, pass_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM documents WHERE pass_id=? ORDER BY doc_id", (pass_id,)).fetchall()

    def datasets_for_doc(self, doc_id: str) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM datasets WHERE doc_id=? ORDER BY id", (doc_id,)).fetchall()

    def variables_for(self, dataset_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM variables WHERE dataset_id=? ORDER BY id", (dataset_id,)).fetchall()

    def evidence_for(self, dataset_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM evidence WHERE dataset_id=? ORDER BY chunk_index", (dataset_id,)).fetchall()

    def open_review(self, pass_id: int | None = None) -> list[sqlite3.Row]:
        if pass_id is None:
            return self._con.execute("SELECT * FROM review_queue WHERE status='open' ORDER BY kind, name_raw").fetchall()
        return self._con.execute("SELECT * FROM review_queue WHERE status='open' AND pass_id=? ORDER BY kind, name_raw", (pass_id,)).fetchall()

    def writes_in_pass(self, pass_id: int) -> list[sqlite3.Row]:
        return self._con.execute("SELECT * FROM zotero_writes WHERE pass_id=? ORDER BY id", (pass_id,)).fetchall()

    def query_by_type(self, type_slug: str) -> list[sqlite3.Row]:
        return self._con.execute("""
            SELECT d.doc_id, doc.title, doc.year, d.name_raw, d.src_slug, d.geo_text, d.geo_level, d.period_start, d.period_end,
                   (SELECT group_concat(DISTINCT v.dv_class) FROM variables v WHERE v.dataset_id=d.id AND v.role='dependent') AS dvs
            FROM datasets d JOIN documents doc ON doc.doc_id=d.doc_id
            WHERE d.type_slug=? ORDER BY doc.year, doc.title""", (type_slug,)).fetchall()

    def source_geo_matrix(self) -> list[sqlite3.Row]:
        return self._con.execute("""
            SELECT COALESCE(src_slug, '(unlisted) ' || name_raw) AS src_slug, geo_level, COUNT(DISTINCT doc_id) AS n
            FROM datasets GROUP BY 1, 2 ORDER BY n DESC, 1""").fetchall()

    def topic_crosstab(self, topic_tag: str, doc_tags_lookup) -> list[sqlite3.Row]:
        """doc_tags_lookup(doc_id) -> list[str] of Zotero topic tags (from ChromaReader.doc_meta)."""
        rows = self._con.execute("SELECT DISTINCT doc_id FROM datasets").fetchall()
        keep = [r["doc_id"] for r in rows if topic_tag.lower() in [t.lower() for t in doc_tags_lookup(r["doc_id"])]]
        if not keep:
            return []
        marks = ",".join("?" * len(keep))
        return self._con.execute(f"""
            SELECT COALESCE(src_slug, '(unlisted) ' || name_raw) AS src_slug, type_slug, COUNT(DISTINCT doc_id) AS n
            FROM datasets WHERE doc_id IN ({marks}) GROUP BY 1, 2 ORDER BY n DESC""", keep).fetchall()
