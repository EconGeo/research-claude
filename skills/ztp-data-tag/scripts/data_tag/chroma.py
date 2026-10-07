"""Read-only access to ZotPilot's ChromaDB SQLite file (no chromadb client needed)."""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CHROMA = Path.home() / ".local/share/zotpilot/chroma/chroma.sqlite3"

_CHUNK_SQL = """
SELECT m.id,
       MAX(CASE WHEN m.key='chunk_index'     THEN m.int_value END)    AS chunk_index,
       MAX(CASE WHEN m.key='page_num'        THEN m.int_value END)    AS page_num,
       MAX(CASE WHEN m.key='total_chunks'    THEN m.int_value END)    AS total_chunks,
       MAX(CASE WHEN m.key='section'         THEN m.string_value END) AS section,
       MAX(CASE WHEN m.key='chroma:document' THEN m.string_value END) AS text
FROM embedding_metadata m
WHERE m.id IN (SELECT id FROM embedding_metadata WHERE key='doc_id' AND string_value=?)
GROUP BY m.id
ORDER BY chunk_index
"""

_META_SQL = """
SELECT key, string_value, int_value FROM embedding_metadata
WHERE id = (SELECT MIN(id) FROM embedding_metadata WHERE key='doc_id' AND string_value=?)
  AND key IN ('doc_title','year','publication','doi','tags','collections')
"""


@dataclass
class Chunk:
    doc_id: str
    chunk_index: int
    page_num: int | None
    section: str
    text: str
    total_chunks: int | None = None


class ChromaReader:
    def __init__(self, path: Path | str = DEFAULT_CHROMA):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Chroma DB not found: {self.path}")
        self._con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)

    def chunks_for_doc(self, doc_id: str) -> list[Chunk]:
        rows = self._con.execute(_CHUNK_SQL, (doc_id,)).fetchall()
        return [Chunk(doc_id, int(r[1] or 0), r[2], r[4] or "unknown", r[5] or "", r[3]) for r in rows]

    def indexed_doc_ids(self, candidates: list[str]) -> set[str]:
        found: set[str] = set()
        for i in range(0, len(candidates), 500):
            batch = candidates[i:i + 500]
            marks = ",".join("?" * len(batch))
            rows = self._con.execute(
                f"SELECT DISTINCT string_value FROM embedding_metadata WHERE key='doc_id' AND string_value IN ({marks})",
                batch).fetchall()
            found.update(r[0] for r in rows)
        return found

    def doc_meta(self, doc_id: str) -> dict:
        meta = {"title": "", "year": None, "publication": "", "doi": "", "tags": [], "collections": []}
        for key, sval, ival in self._con.execute(_META_SQL, (doc_id,)):
            if key == "doc_title": meta["title"] = sval or ""
            elif key == "year": meta["year"] = ival
            elif key == "publication": meta["publication"] = sval or ""
            elif key == "doi": meta["doi"] = sval or ""
            elif key in ("tags", "collections"):
                meta[key] = [t.strip() for t in (sval or "").split(";") if t.strip()]
        return meta
