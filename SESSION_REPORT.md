# Session Report — research-claude

## 2026-06-12 20:05 UTC — README overhaul, rules refactor, dataset/variable tagging + ztp-data-tag plan

**Operations:**
- Pushed the pending `data-manifest.md` commit; brought local `main` in sync with origin.
- **README** (`EconGeo/research-claude`): documented the rules layer; added Windows micromamba install; Zotero 8→9; ZotPilot fork attribution + ChromaDB/Ollama-vs-Gemini rationale; documented the Connector bridge (auto-download papers) with a prebuilt-zip path + build-from-submodule path; noted the bridge auto-starts; added the "let Claude install it" top callout; added the Obsidian knowledge-base section; consistency pass fixed `zotpilot stats`→`status`, `/data-analysis`→`/analyze`, added `/seed-papers`, normalized `~/path/to/your-project` placeholders, added Connector removal to uninstall.
- **Rules** (`rules/`): split the quarto rules by concern — `quarto-empirical.md` owns architecture/caching/single-source-of-ground-truth; `quarto-pdf.md`/`quarto-word.md` reframed as format-reference docs (canonical model: one `manuscript.qmd`, both outputs). Dropped the vestigial top-level Chicago `csl`.
- **apply.sh**: synced `--list`/header to actual `rules/` + skills; installs the Obsidian `obsidian-config.md.example` template into `.claude/state/` (closed the `--setup-obsidian` gap).
- **journal-digest submodule** (`EconGeo/journal-digest`, `23d6815 → e3e554d`): Tier-2 prompt now extracts datasets + key variables; `gather/writer.py` emits a structured, `json.loads`-able `Data` field per article (`{"datasets":[],"variables":[],"unit":"","timespan":"","access":""}`); pointer bumped in research-claude.
- Wrote `docs/plans/2026-06-12-ztp-data-tag-skill.md` — full plan for an opt-in `/ztp-data-tag` skill (to execute in a later session).

**Decisions:**
- Quarto file model = **one `manuscript.qmd`, PDF primary, Word via added `docx:` block** (user choice) — drove the rules reconciliation.
- Connector download stays pointed at **upstream `xunhe730`** (user doesn't maintain the extension); documented as the upstream author's, bundled here only.
- ztp-data-tag storage = **tags + structured note**; scope = **pilot one collection first**; batch/manual, user-opt-in.
- Schema for the data field is shared between journal-digest and the planned skill (5 keys identical; skill adds `source` quality flag).

**Results / verified facts:**
- Connector bridge **auto-starts** on first ingest (`BridgeServer.auto_start`, `tools/ingestion/connector.py`) — no manual `zotpilot bridge`.
- Extraction text channels: `get_paper_details` returns **metadata + abstract** (Zotero SQLite), **not** body; paper body is only ChromaDB chunks via `search_papers`/`get_passage_context`; **no tool returns full text / all chunks** → extraction is retrieval-based; unindexed papers are abstract-only.
- Persistence is **global**: tags/notes write to the Zotero library; ChromaDB + config live in `~/` (machine-global). `apply.sh` only adds project-local skill files + `.mcp.json`. So a whole-library data-tag pass is **one-time** and a new project's run skips already-tagged items. **Invariant locked into the plan:** idempotency key = the global `data-tagged` Zotero tag (read live via `advanced_search`), never a project-local file. ChromaDB needs a re-index only for searchability, not dedup.

**Commits (research-claude `main`):**
- `38a1783` lock in global persistence + cross-project dedup invariant (plan)
- `b18b229` correct extraction channel — ChromaDB chunks, not full-text read (plan)
- `e6abdcf` add ztp-data-tag implementation plan
- `a8f4cbe` bump journal-digest to structured Data field
- `00a9db9` document dataset/variable tagging for the Obsidian knowledge base
- `72bc4aa`,`42f4e6d`,`82ac03b`,`928043f`,`047b558`,`794f6d7`,`3db48f5`,`11740b3` README work
- `9ecfbcd` drop vestigial Chicago csl; `f2610b7` split quarto rules; `eb5dc34` document rules layer
- journal-digest: `23d6815 → 49aa852 → e3e554d`

**Status:**
- Done: all README/rules/apply.sh/journal-digest work committed + pushed; both repos in sync.
- Pending (next session): **execute `docs/plans/2026-06-12-ztp-data-tag-skill.md`** — build the `/ztp-data-tag` skill (Tasks 1–3 are repo edits; Task 4 is a manual pilot that needs a project with ZotPilot configured + write creds + indexed library). Use subagent-driven-development or executing-plans.
