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

## 2026-06-12 20:20 UTC — Executed the ztp-data-tag plan (Tasks 1–3) via subagent-driven development

**Operations:**
- Ran `docs/plans/2026-06-12-ztp-data-tag-skill.md` with subagent-driven-development: one fresh implementer subagent (sonnet) per task, sequential (shared git state), with controller-run independent verification after each.
- **Task 1** — created `skills/ztp-data-tag/SKILL.md` (165 lines): opt-in library data-field backfill skill; preconditions check, pilot-collection-first, `data-tagged` resumability marker, retrieval-based extraction (ChromaDB chunks), tags-via-`add` + structured Data note, confirm-before-write gates. Schema reuses journal-digest's five keys + `source`.
- **Task 2** — updated `apply.sh` header comment + `--list` to mention the skill (install is automatic via the `skills/*` glob).
- **Task 3** — documented `/ztp-data-tag` in README (pipeline-skills table row + data-discovery cross-reference); pushed.

**Decisions:**
- Collapsed the skill's per-task spec/code-quality review subagents into controller-run independent verification — for markdown/bash-comment edits with exact specified content + built-in verify commands, a separate code-quality subagent is ceremony. Verified each task by reading files + running the plan's exact checks myself (not trusting subagent reports).
- Executed on `main`, consistent with the session's direct-to-main workflow and the plan's own commit/push steps.

**Results / verification:**
- Schema parity confirmed: SKILL.md and `submodules/journal-digest/gather/writer.py` emit the identical 5-key prefix. Tool names: exactly the 9 real `mcp__zotpilot__*` tools, no typos.
- Fresh `apply.sh --project-dir <tmp>` install confirmed `ztp-data-tag/SKILL.md` lands in the target `.claude/skills/` and shows in `--list`.
- Each task's diff inspected = only the intended hunks. Branch in sync with origin.

**Commits (research-claude `main`):**
- `00654c5` feat: add ztp-data-tag skill
- `68ab9cf` chore: list ztp-data-tag in apply.sh --list/header
- `cc1632f` docs(readme): document /ztp-data-tag

**Status:**
- Done: Plan Tasks 1–3 (build + wire + document the skill) — committed, pushed, verified.
- Pending: **Task 4 — manual pilot.** Cannot run in this tooling repo. In a project with ZotPilot configured + write creds + an indexed library: invoke `/ztp-data-tag`, pilot a small (≤5-paper) collection, confirm tags + Data note land, verify re-run skips `data-tagged` items (resumability), test undo. Then record findings (datasets-found vs empty vs abstract-only) to judge a whole-library run.

## 2026-06-12 20:30 UTC — Task 4 pilot run + skill fixes

**Operations:**
- Created test project `~/data_tag_test`, installed via `apply.sh` (ztp-data-tag skill landed).
- Ran the full pilot against the live Zotero library (293 docs indexed) via ZotPilot MCP. Picked collection `spatial` (5 papers): CI84N8RM, DV4AI84P, NIYFJAEF (dup), MQ5DDUU9, 4LDTWWPX. Wrote `dataset:*`/`var:*`/`data-tagged` tags + a "Data (auto-extracted)" note to each. Verified, tested resumability and undo.
- Applied 4 fixes to `skills/ztp-data-tag/SKILL.md`.

**Pilot result — all 5 test steps passed:**
- Preconditions check → collection pick → batch preview before write: ✓
- Tags + Data note landed on all 5 (verified via `advanced_search` tag=data-tagged + `get_notes`): ✓
- Resumability: marker query returns all tagged → re-run sees 0 new → "already processed": ✓
- Undo: removed tags from MQ5DDUU9 → marker returns 4 → reprocessed exactly that one: ✓
- Extraction quality good even for methods papers (Xu→US voter-turnout/EDR; Ashenfelter-Card→CETA); the ChromaDB retrieval channel surfaced datasets absent from abstracts (Montréal Altus sales 1993–2000; Aberdeen 2004–2007). Justifies a whole-library run.

**Findings → fixes (committed to the skill):**
- **CRITICAL:** `manage_tags(action="add")` creates NO new tags without `allow_new=true` — as originally written the skill would tag nothing. Fixed: `allow_new=true` + Rules bullet.
- **IMPORTANT:** `create_note` not idempotent → duplicate Data notes on reprocess. Fixed: `idempotent=true`.
- **IMPORTANT:** ZotPilot has no delete-note MCP tool — Undo "delete notes" is manual in Zotero. Fixed: Undo wording + rely on `idempotent=true`.
- **MINOR:** `search_papers` has no `doc_id` filter (only collection/author/tag); one collection-scoped search covers several papers efficiently — and `section_weights` has no `data` key (use `methods`). Fixed: Step 3 reworded.

**Decisions:**
- Left the `spatial` collection genuinely backfilled (real, useful artifact; all 5 consistently tagged + noted after restoring MQ5DDUU9). `~/data_tag_test/` is disposable scaffold.

**Status:**
- Done: **Plan fully executed (Tasks 1–4).** Skill built, wired, documented, piloted against the real library, and corrected for the 4 issues the pilot exposed.
- Optional next: a whole-library `/ztp-data-tag` run (now safe with the fixes), then re-index so Data notes are searchable. Consider proposing a `delete_note` tool upstream in ZotPilot.
