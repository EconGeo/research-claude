#!/usr/bin/env python3
"""mock_zotpilot.py — a stdio MCP (JSON-RPC 2.0, newline-delimited) stand-in for the ZotPilot
server, answering the ten tools the bridge skills and extraction agents call from
tests/fixture-project/zotpilot_fixture.json.

Purpose: functionality evals that assert MECHANISM — which tool, in what order, with which
flags — with no Zotero, no ChromaDB and no embedding provider (audit 2026-09-15 §3 P7;
docs/plans/2026-09-24-option-gates-subagent-routing-evals.md Part C). Ranking is token
overlap, so it is deterministic. Writes mutate an in-memory copy of the fixture and are
logged as `WRITE <tool> <args-json> -> <result-json>`, and every call (known or not) as
`CALL <tool> <args-json>` — those lines are the evals' assertion source. They go to the file
named by MOCK_ZOTPILOT_LOG (set it in the MCP config's `env`), else to stderr; the client does
not forward a server's stderr, so an eval must set the variable.

Results are wrapped the way the MCP spec requires — `{"content": [{"type": "text", "text":
<json>}]}` — an unwrapped result reads as "completed with no output" to the client (found by
the first eval run, 2026-09-24).

Two ZotPilot behaviours are reproduced on purpose because the skills guard against them:
- `manage_tags(action="set")` is refused (destructive; the skill forbids it), and
  `action="add"` without `allow_new=true` creates NO new tag.
- `create_note(idempotent=true)` returns `created: false` when the item has ANY note.

Usage: register as `{"mcpServers": {"zotpilot": {"type": "stdio", "command": "python3",
"args": ["<repo>/tests/mock_zotpilot.py"]}}}` in an eval project's `.mcp.json`.
Stdlib only.
"""
from __future__ import annotations
import copy, json, os, pathlib, re, sys

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixture-project" / "zotpilot_fixture.json"

TOOLS = [
    ("get_index_stats", "Indexed / unindexed paper counts."),
    ("browse_library", "Browse collections or items (view=collections|items, collection=...)."),
    ("advanced_search", "Metadata filter: author, year, tag, collection."),
    ("search_topic", "Topic search over the local index (query)."),
    ("search_papers", "Passage search over chunks (query, collection?, section_weights?)."),
    ("get_passage_context", "Surrounding chunks for a hit (doc_id, chunk_index)."),
    ("get_paper_details", "Metadata + abstract (doc_id)."),
    ("get_notes", "Notes on an item (item_key)."),
    ("create_note", "Create a note (item_key, title, content, idempotent?)."),
    ("manage_tags", "Add/remove tags (action, item_key, tags, allow_new?)."),
]


def tokens(s: str):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


class Library:
    def __init__(self, fixture: dict):
        self.d = copy.deepcopy(fixture)
        self.by_id = {p["doc_id"]: p for p in self.d["papers"]}
        self.by_key = {p["key"]: p for p in self.d["papers"]}
        self.tag_vocab = {t for p in self.d["papers"] for t in p["tags"]}

    # ── reads ──
    def get_index_stats(self, **_):
        n = sum(p["indexed"] for p in self.d["papers"])
        return {"indexed": n, "unindexed": len(self.d["papers"]) - n, "libraries": ["My Library"]}

    def browse_library(self, view="collections", collection=None, **_):
        if view == "collections":
            return {"collections": [{"name": c, "items": len(ids)} for c, ids in self.d["collections"].items()]}
        ids = self.d["collections"].get(collection) if collection else list(self.by_id)
        return {"items": [self._meta(i) for i in ids]}

    def advanced_search(self, author=None, year=None, tag=None, collection=None, **_):
        ids = self.d["collections"].get(collection, []) if collection else list(self.by_id)
        out = []
        for i in ids:
            p = self.by_id[i]
            if author and not any(author.lower() in a.lower() for a in p["authors"]): continue
            if year and int(year) != p["year"]: continue
            if tag and tag not in p["tags"]: continue
            out.append(self._meta(i))
        return {"items": out}

    def search_topic(self, query="", limit=10, **_):
        scored = []
        for p in self.d["papers"]:
            s = len(tokens(query) & tokens(p["title"] + " " + p["abstract"]))
            if s: scored.append((s, p["doc_id"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return {"papers": [dict(self._meta(i), score=s) for s, i in scored[:limit]]}

    def search_papers(self, query="", collection=None, section_weights=None, limit=10, **_):
        w = section_weights or {}
        ids = self.d["collections"].get(collection, []) if collection else list(self.by_id)
        hits = []
        for i in ids:
            p = self.by_id[i]
            if not p["indexed"]: continue
            for k, c in enumerate(p["chunks"]):
                s = len(tokens(query) & tokens(c["text"])) * float(w.get(c["section"], 1.0))
                if s: hits.append({"doc_id": i, "title": p["title"], "chunk_index": k,
                                   "section": c["section"], "text": c["text"], "score": s})
        hits.sort(key=lambda h: (-h["score"], h["doc_id"], h["chunk_index"]))
        return {"hits": hits[:limit]}

    def get_passage_context(self, doc_id, chunk_index=0, **_):
        p = self.by_id[doc_id]
        lo, hi = max(0, chunk_index - 1), min(len(p["chunks"]), chunk_index + 2)
        return {"doc_id": doc_id, "chunks": p["chunks"][lo:hi]}

    def get_paper_details(self, doc_id, **_):
        p = self.by_id[doc_id]
        return dict(self._meta(doc_id), abstract=p["abstract"], tags=list(p["tags"]))

    def get_notes(self, item_key, **_):
        return {"notes": list(self.by_key[item_key]["notes"])}

    # ── writes ──
    def create_note(self, item_key, title="", content="", idempotent=False, **_):
        p = self.by_key[item_key]
        if idempotent and p["notes"]:
            return {"created": False, "reason": "item already has a ZotPilot note (idempotent)"}
        key = f"N{item_key}{len(p['notes']) + 1}"
        p["notes"].append({"key": key, "title": title, "content": content, "source": "mock"})
        return {"created": True, "note_key": key}

    def manage_tags(self, action, item_key, tags, allow_new=False, **_):
        if action == "set":
            raise ValueError("manage_tags action='set' replaces every tag on the item; refused")
        p = self.by_key[item_key]
        if action == "add":
            added = []
            for t in tags:
                if t in self.tag_vocab or allow_new:
                    if t not in p["tags"]: p["tags"].append(t)
                    self.tag_vocab.add(t); added.append(t)
            return {"added": added, "skipped_new": [t for t in tags if t not in added]}
        if action == "remove":
            removed = [t for t in tags if t in p["tags"]]
            p["tags"] = [t for t in p["tags"] if t not in tags]
            return {"removed": removed}
        raise ValueError(f"unknown action {action!r}")

    def _meta(self, i):
        p = self.by_id[i]
        return {"doc_id": i, "key": p["key"], "title": p["title"], "year": p["year"],
                "authors": p["authors"], "indexed": p["indexed"]}


WRITES = {"create_note", "manage_tags"}


def log(line: str):
    path = os.environ.get("MOCK_ZOTPILOT_LOG")
    if path:
        with open(path, "a") as f:
            f.write(line + "\n")
    else:
        print(line, file=sys.stderr, flush=True)


def wrap(result) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}]}


def main():
    lib = Library(json.loads(FIXTURE.read_text()))
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        req = json.loads(line)
        rid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
        try:
            if method == "initialize":
                result = {"protocolVersion": params.get("protocolVersion", "2024-11-05"),
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "mock-zotpilot", "version": "0.0.1"}}
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                result = {"tools": [{"name": n, "description": d,
                                     "inputSchema": {"type": "object", "additionalProperties": True}}
                                    for n, d in TOOLS]}
            elif method == "tools/call":
                name, args = params["name"], params.get("arguments") or {}
                log(f"CALL {name} {json.dumps(args, sort_keys=True)}")
                if name not in dict(TOOLS): raise ValueError(f"unknown tool {name}")
                result = getattr(lib, name)(**args)
                if name in WRITES:
                    log(f"WRITE {name} {json.dumps(args, sort_keys=True)} -> {json.dumps(result, sort_keys=True)}")
                result = wrap(result)
            else:
                raise ValueError(f"unknown method {method}")
            out = {"jsonrpc": "2.0", "id": rid, "result": result}
        except Exception as e:  # noqa: BLE001 — a tool failure is an isError result (MCP), not an RPC error
            if method == "tools/call":
                out = {"jsonrpc": "2.0", "id": rid,
                       "result": {"content": [{"type": "text", "text": str(e)}], "isError": True}}
            else:
                out = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)}}
        print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
