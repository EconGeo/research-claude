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

## 2026-06-12 20:45 UTC — Plan written: ZotPilot delete_note MCP tool (checkpoint before /clear)

**Operations:**
- Explored the ZotPilot codebase (`submodules/zotpilot` = `EconGeo/ZotPilot`) to ground a plan for a `delete_note` MCP tool (the gap the ztp-data-tag pilot exposed — no MCP path to delete a note).
- Wrote `docs/plans/2026-06-12-zotpilot-delete-note-tool.md` (TDD, full code + tests inline). Decided NOT to keep `spatial` test tags? No — **kept** the spatial backfill per user.

**Key facts verified in ZotPilot source (baked into the plan):**
- MCP tools register via `@mcp.tool(tags=tool_tags("extended","write"))` in `write_ops.py` (auto-imported by `tools/__init__.py`) — no registry edit needed.
- `ZoteroWriter.delete_item(key)` already trashes ANY item (no type guard) → `delete_note` adds an `itemType=="note"` guard + a default `[ZotPilot]`-marker guard so it never deletes a paper or the user's own notes.
- Tests mock pyzotero `_zot` (writer) / patch `_get_writer` (tool); run with `uv run pytest`. Anchors confirmed: `create_note` write_ops.py:154, `delete_item` zotero_writer.py:433, `logger` zotero_writer.py:14, imports present.

**Plan shape:** Task 1 writer method + guard tests · Task 2 MCP tool wrapper + delegation test · Task 3 regression run + push `feat/delete-note-tool` branch + `gh pr create` to EconGeo/ZotPilot · Task 4 (gated on merge) bump submodule + switch ztp-data-tag undo to use `delete_note`.

**Commits (research-claude):**
- `8921257` docs: add plan for ZotPilot delete_note MCP tool

**Status:**
- Done: delete_note plan written, grounded, committed/pushed. Checkpoint complete.
- Pending (next session, after /clear): **execute `docs/plans/2026-06-12-zotpilot-delete-note-tool.md`** via subagent-driven-development. Work is in `submodules/zotpilot` (Tasks 1–3); Task 4 (research-claude) is gated on the PR merging. Needs a ZotPilot dev env (`uv`/deps) for pytest; no live Zotero required (mocked).


## 2026-06-22 19:43 UTC — ZotPilot: executed multi-library indexing (PR #2) + indexing-reliability & token-aware chunking (PR #4)

All work in `~/Projects/ZotPilot` (= `EconGeo/ZotPilot`, fork of `xunhe730/ZotPilot`). Two plans executed via superpowers subagent-driven-development (fresh implementer + spec/quality review per task + opus whole-branch review). Durable ledgers at `ZotPilot/.superpowers/sdd/progress.md`.

**Operations — multi-library indexing (plan `docs/superpowers/plans/2026-06-21-multi-library-indexing.md`):**
- Executed 6 code tasks + a final-review fix on branch `feat/multi-library-indexing`. Added `enumerate_indexable_libraries`, `global_pdf_doc_ids`, and the `index_all_libraries` orchestrator: one cross-library PDF-doc-id union passed as `protected_doc_ids` to every per-library `Indexer.index_all`, so reconciliation only deletes docs absent from EVERY library. Wired CLI `cmd_index` + MCP `index_library`; stats span all libraries.
- Final review caught a real convergence bug (a fully-indexed early library starved later libraries under batched runs because `index_all` derives `has_more` from the pre-skip candidate count) → fixed: orchestrator only stops on a library that made real progress. Regression test added.
- **PR #2** opened (EconGeo fork, base `main`). 8 commits, all reviews clean.

**Operations — indexing reliability + token-aware chunking (plan `docs/superpowers/plans/2026-06-22-indexing-reliability-and-rag-chunking.md`):**
- Brainstormed whether to switch off ZotPilot vs harden it; chose harden + delegate chunking to a RAG library (LlamaIndex). Wrote the plan, executed 8 tasks + final-review fixes on branch `feat/indexing-reliability-and-token-aware-chunking` (stacked on the multi-library branch — depends on `index_all_libraries`).
- Phase A (no new deps): Ollama embedder truncates oversized inputs + sub-batches (one over-long chunk no longer fails a whole doc); Gemini retry loop surfaces the real cause (fixed `UnboundLocalError: 'e'` mask); preflight 1-token embedder probe (guarded by `if to_index:`); `--limit 0` = index-nothing; multi-library aggregate fixes (distinct `already_indexed`, restored quality/extraction summary).
- Phase B: `ChunkerProtocol` seam; `LlamaIndexChunker` using bge-large's own tokenizer via `SentenceSplitter` → chunks guaranteed ≤512 tokens (root-cause fix), behind optional `[llamaindex]` extra; `chunker_backend` config wired into the index config-hash. Final review caught a spurious-reindex-warning risk → folded `chunker_backend` into the hash only for non-default backends so existing `char` users are unaffected on upgrade (locked by `test_config_hash_char_equals_no_attr`).
- Also fixed 2 stale embedder tests (nomic-embed-text/768 → bge-large/1024). **PR #4** opened, stacked on PR #2. 12 commits, all reviews clean.

**Live runs (real library, ~/Library/CloudStorage/.../Zotero):**
- 5 libraries (My Library + 4 groups: ESG, NAR_settlement, affordable_housing, regenerative_paradigm); global union 3340 PDFs.
- First sweep FAILED to embed (254 fails): root cause was env misconfig — `embedding_provider=gemini` with invalid key `'exit'` while Ollama+bge-large was the real backend; failures masked as the EMN7YZV7 `UnboundLocalError`. SAFETY HELD: store unchanged at 2744, 0 deletions.
- Fixed via `zotpilot config set embedding_provider ollama` (verified bge-large 1024-dim matches the existing `chunks_bge` collection — space is set by MODEL, so safe). Re-ran: +254 docs indexed (store 2744 → 2998), 0 deletions across 4 passes. Remaining ~343 unindexed = long books >40pp (by design), image-only/no-text PDFs, 11 group PDFs not on local disk.

**Decisions:**
- Library for chunking delegation = **LlamaIndex** (token-aware SentenceSplitter + bge tokenizer), behind a swappable `ChunkerProtocol`.
- Keep fork PRs only; **do NOT open upstream now** — `EconGeo` fork is 12 commits diverged from `xunhe730/ZotPilot` (which is 57 commits ahead independently), so an upstream PR would be a messy 20-commit conflict mix. Upstream contribution deferred to a deliberate rebase/cherry-pick of feature work onto current `upstream/main`.
- Embedding errors are now observable (truncation logs a warning; real causes surfaced).

**Results / verified facts:**
- Full suite: 853 passed; 10 pre-existing failures (down from 12 — fixed the 2 stale embedder tests), all unrelated (present at the pre-PR-#2 baseline `de99ae5`): bootstrap_install, cli_setup batch_size, state tool-surface, 5 token_budget MagicMock-config contracts, 2 tool_profiles.
- Multi-library safety invariant (`index_authority.py` reconciliation) untouched throughout both PRs.
- zotpilot is installed editable → CLI/MCP run the committed code. Added an `upstream` git remote (xunhe730) for future rebase.

**GitHub (EconGeo/ZotPilot):**
- PR #2 — multi-library indexing (base `main`). PR #4 — reliability + token-aware chunking (stacked on #2). Issue #3 — Ollama-400 chunk bug, FILED then cross-linked to PR #4 (resolves on merge). Enabled repo Issues (were disabled).

**Status:**
- Done: both plans fully executed + reviewed; both PRs open on the fork; library re-indexed; Issue #3 addressed by PR #4.
- Open follow-ups (non-blocking, in PR #4 notes): LlamaIndexChunker page-offset approximate under overlap (metadata only); gemini deferred-import style; PDFs missing on local disk counted as unindexed (path-resolution, parked); upstream contribution needs a clean rebase onto `xunhe730/main`.
