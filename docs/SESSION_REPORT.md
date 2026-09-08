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

## 2026-09-08 — Design: fork to a Quarto-native pipeline (clo-author decoupling)

**Operations:**
- Audited all 47 clo-author agent/rule/skill files for LaTeX/Beamer/multi-file coupling.
- Checked every clo-author capability for artifact-level evidence of use across `~/Research/*`.
- Compared agent versions across clo-author, POGM4, NAR_settlement, zoning2026.
- Created `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md`.
- Created `docs/checkpoints/2026-09-08_quarto-native-pipeline-fork.md`.
- Branch `design/quarto-native-pipeline` cut from `main`. No code touched; docs only.

**Decisions:**
- Remove the `clo-author` submodule; keep `ai-audit` and `journal-digest` (both EconGeo, live).
- Keep worker→critic pairing, separation of powers, 3-strikes escalation; cut the orchestration
  graph (orchestrator, permissions, lifecycle, pipeline_state, traces, weighted aggregation).
- `research-claude` is authoritative; harvest project improvements with a de-projectification pass.
- Fold `librarian`/`librarian-critic` into a new `skills/lit-position/` bridge skill rather than
  editing the vendored `zotpilot-skills/`.
- Keep `theorist` + `theorist-critic` in the default install.
- Delete `rules/pipeline-precedence.md` — with no legacy layer there is nothing to precede.

**Results / verified facts:**
- Coupling is narrow: `working-paper-format.md` 17%, `content-standards.md` 9%, `storyteller.md` 9%,
  writer/writer-critic/verifier 6%; ten agents measure exactly 0%.
- `clo-author` pinned at 2026-05-10; no pulls in four months.
- Stranded value: `editor.md` 366 lines in POGM4 vs 67 upstream; `coder-critic` diverged
  independently in POGM4 (99) and zoning2026 (82), each adding a *different* half of Quarto
  support — POGM4 the manifest checks (INV-23/24), zoning2026 the Correctness Layer.
- `NAR_settlement` is at baseline on every agent — nothing to harvest there.
- Four shipped files give wrong instructions and are NOT covered by `pipeline-precedence.md`:
  `table-standards.md` (threeparttable/tabularray vs flextable), `figure-standards.md`
  (`ggsave("fig.pdf")` vs PNG@200dpi for Word), `content-standards.md`, `meta-governance.md`
  (Emory/biology-forker identity leak).
- Never-exercised capabilities confirmed empty in POGM4: `strategy/`, `theory/`,
  `preregistrations/`, `decisions/`, `specs/`, `literature/`, `traces/`, `paper/talks/`,
  `paper/replication/`.
- De-projectification scope: one leaked token (`manuscript_quarto_word`) across 8 candidates.

**Commits:**
- `7729df1` Design spec: fork to a Quarto-native research pipeline

**Status:**
- Done: audit, design, spec written + self-reviewed + committed, checkpoint saved.
- Pending: user review of the spec; then `superpowers:writing-plans`; then implementation.
- Open: Q1 scratch-vs-in-place re-apply to POGM4; Q2 promotion mechanism; Q3 rollout order for
  zoning2026 / ESG / BRI / affordable_housing_2026.

---

## 2026-09-08 — Quarto-native pipeline fork (Tasks 1–17)

Forked `EconGeo/research-claude` off the dead `hugosantanna/clo-author` submodule
into a standalone Quarto-native pipeline, and changed distribution from copy to
per-item symlink.

**Final tree:** 17 agents · 18 skills · 15 rules · 9 references · 8 hooks · 2 submodules
(`ai-audit`, `journal-digest`). `scripts/check_fork.sh` exits 0.

### Task 17 — scratch-POGM4 validation (D6)

Conversion of `/private/tmp/pogm4-scratch` (a copy of POGM4) via
`apply.sh --link --tip`:

| Check | Spec criterion | Result |
|---|---|---|
| `quarto render manuscript_quarto_word.qmd` | 4 | **exit 0** — .docx produced, newer than source, 0 ERROR/WARNING in the log |
| `prose_number_check.py manuscript_quarto_word.qmd` | 5 | **exit 0** — 95 distinct literals, all allowlisted with a reason (479 occurrences) |
| Links resolve | link mechanism 1 | **pass** — only the 3 shared-reference symlinks dangle, an artifact of `/tmp` being outside `~/Research`; they resolve in the real project |
| Override preserved, dead link pruned, edited seed untouched | link mechanism 2 | **pass** — `flextable-quarto-word-captions` and `commit` stayed real directories across a re-link |
| Every linked skill/agent well-formed and discoverable | link mechanism 3 (proxy) | **pass** — 28/28 skills have valid frontmatter with `name:` matching the directory; 19/19 agents valid; 15 rules and 8 hooks resolve |
| Project `CLAUDE.md` still loads | — | present, untouched |

**Still outstanding:** the interactive confirmation that Claude Code *discovers* a
per-item symlinked skill in a live session (Task 17 Step 5). No script can make that
check. The structural proxy above is as far as automation goes. **Task 18 (converting
the six live paper repos) is gated on it and has NOT been run.**

### Defects found and fixed during execution

1. **`apply.sh` relative-path bug.** Links were computed with a logical `pwd` but
   resolved by the kernel physically. On macOS `/tmp` → `/private/tmp`, so all 66
   links came out one directory short and silently dangled. Both `SCRIPT_DIR` and
   `PROJECT_DIR` now use `pwd -P`.
2. **`copy_seed` clobbered symlinked seeds.** It tested only `-e`, so a
   `--link-references` symlink read as absent; `cp` then followed the dangling link
   and aborted the run under `set -e` before the lock file was written.
3. **INV-11's enforcer did not travel with the pipeline.** `prose_number_check.py`
   lived only in `~/Research/scripts/` and was referenced by that absolute path in a
   shipped rule. A coauthor bootstrapping from a clone could not run the one check a
   clean render cannot make. Vendored into `scripts/` and linked into
   `.claude/scripts/`.
4. **Wrong invocation in four places** (mine, and the plan's):
   `prose_number_check.py .` — the script takes a manuscript path and errors on a
   directory.
5. **`rules/ai-disclosure.md` existed only in POGM4** — a stranded improvement the
   harvested `writer`/`coder` agents already referenced. Vendored with its template.
6. **Scope larger than the spec estimated.** The spec measured clo-author's LaTeX
   coupling at 0–6%; the vendored *skills* carried much more (`/talk`'s Beamer engine,
   `/tools compile` via latexmk, `/write` and `/revise` targeting `paper/sections/*.tex`,
   a LaTeX deduction table in the manuscript-review template, and a second stale copy
   of the table/figure rules inside `content-standards.md`). All rewritten.
7. **Four pre-existing D5 violations in research-claude's own rules** (project nouns as
   worked examples), found by the gate on its first run.

### Judgment calls made without the user

- **Criterion 7 was split** into `project-identity` (banned everywhere) and
  `project-nouns` (journal/vendor names, banned everywhere *except* `references/`).
  `discipline-cards.md` names REE/JREFE/JRER/JREPM and CoStar because that is what a
  discipline card is; the original rule made shipping one impossible.
- **`prose_number_check.py`'s provenance comments naming POGM4 and NAR_settlement were
  kept.** They record why the rule exists, and `scripts/` is infrastructure rather than
  shipped instruction content.
- **`templates/response-letter.tex` converted to `.qmd`.** A LaTeX-only response letter
  does not belong in a pipeline whose output contract is `quarto render`.

### Task 18 — POGM4 converted on a branch, deliberately NOT merged

`~/Research/POGM4` branch `pipeline-symlink` (b7dd786) holds the conversion. The
working tree was returned to `main` and is byte-identical to how it was found, apart
from the untracked rollback dir `.claude.bak.20260908/`. The other five repos were not
touched.

**Verified on the live repo:** `quarto render` exit 0 · `prose_number_check.py` exit 0
(95 literals, all allowlisted) · no dangling symlinks · all six project overrides
remain real files.

**Why unmerged.** The plan gates Task 18 on Task 17 Step 5 — confirming in a live
interactive session that Claude Code discovers a *per-item* symlinked skill. No script
can make that check, and it was not made. Merging six paper repos onto an unverified
discovery mechanism is not a call to make unattended.

### What Task 18 found that the plan did not anticipate

1. **Step 2 does not diff `hooks/` or `agents/`, but Step 3 deletes them.** POGM4 had
   four project-specific hooks (`context-monitor.py`, `log-reminder.py`, `notify.sh`,
   `verify-reminder.py`) and two locally-corrected canonical ones. Following the plan
   literally would have destroyed all six. **Add `hooks` and `agents` to the Step 2
   diff before converting any other repo.**

2. **Both corrected hooks fix real API errors that shipped to every project.**
   `post-compact-restore.py` matched `SessionStart` on `type="compact"` — the field is
   `source=` — so it never fired. `pre-compact.py` signalled with exit code 2 instead of
   the exit-0-plus-JSON block contract. Upstreamed (966bb9b).

3. **The plan's `.gitignore` block silently drops a project's own overrides.** It uses
   `.claude/skills/`, and git cannot re-include a path inside an excluded *directory*,
   so any negation is dead. POGM4's two local skills and four local hooks would have
   vanished from the repo, and a coauthor's clone would be missing them. Fixed in the
   project and in `templates/gitignore` (b7742c8): `/*` form plus explicit negations.

### Before converting the remaining five

Order per D11: NAR_settlement → zoning2026 → ESG → affordable_housing_2026 → BRI.

| Repo | Watch out for |
|---|---|
| `NAR_settlement` | On branch `phase1-event-study`, **not** `main` — branch from there, not from main. Carries `rules/session-handoff.md`, which exists in no canonical tree and looks generalizable: it extends what `/checkpoint` must verify. It references `pipeline-precedence.md` and `workflow.md`, both now deleted, so it needs rewriting before upstreaming. Decide before converting. |
| `zoning2026` | Carries `rules/ground-truth.md` — a RETIRED stub kept so inbound references do not dangle. Project-local; keep as a real file. **No `manuscript_*.qmd` at the repo root**, so the Step 6 render check needs a different target. |
| `ESG` | Has the same four local hooks as POGM4 — shared across two projects, so consider upstreaming rather than keeping local in both. Manuscript is `manuscript.qmd`, which does not follow the `manuscript_<project>.qmd` convention. |
| `affordable_housing_2026` | Clean; `manuscript_affordable_housing_2026.qmd` matches the convention. |
| `BRI` | No `manuscript_*.qmd` at the repo root. |

`humanize`, `verify-claims`, `seed-papers` and the `ztp-*` skills show as "only local"
against `research-claude/skills/` but are **not** overrides — they come from the
`ai-audit` submodule and `zotpilot-skills/`, both linked separately. Do not restore them
as real files.

### Runbook per repo

```bash
cd ~/Research/<project>
git checkout -b pipeline-symlink            # from the repo's CURRENT branch
cp -R .claude ".claude.bak.$(date +%Y%m%d)"

# Step 2 — diff ALL FOUR, not just skills and rules
for s in skills rules agents hooks; do
  diff -rq ".claude/$s" ~/Academic/research-claude/$s 2>/dev/null | grep 'Only in .claude'
done

rm -rf .claude/skills .claude/agents .claude/rules .claude/hooks
~/Academic/research-claude/apply.sh --project-dir "$PWD" --link --tip
# restore genuinely local items from the backup as REAL files, then add a
# !negation line for each in .gitignore
git rm -r -q --cached .claude/skills .claude/agents .claude/rules .claude/hooks

quarto render manuscript_*.qmd                                   # expect 0
python3 .claude/scripts/prose_number_check.py manuscript_*.qmd   # expect 0
find .claude -maxdepth 2 -type l ! -exec test -e {} \; -print    # expect empty
```

Then open a session in the project and confirm a linked skill is invocable before
merging. That is the outstanding gate.

### Step 7 needs a re-link that the plan omits

Merging the conversion branch leaves the working tree broken until you re-run the
linker. `git checkout main` restores the real `.claude/` files from main's index; the
merge then applies the branch's deletion of those same files — and because the linked
directories are gitignored, git neither creates nor restores the symlinks. POGM4 landed
at `agents: 0 entries, rules: 1` immediately after a correct merge.

The fix is one command, and it is exactly what the bootstrap script is for:

```bash
git checkout main && git merge --no-ff pipeline-symlink && git push
./bootstrap-pipeline.sh --tip        # <- REQUIRED; git cannot restore gitignored links
```

Verify after: `ls .claude/agents | wc -l` is non-zero, a linked skill resolves, and
`find .claude -maxdepth 2 -type l ! -exec test -e {} \; -print` is empty.

---

## 2026-09-08 (later) — Rollout complete: all six repos converted

The gating check passed — the user confirmed in a live POGM4 session that a per-item
symlinked skill is discovered (`/write` resolves). Task 18 ran to completion.

| # | Repo | Branch merged into | Overrides kept | render | prose |
|---|---|---|---|---|---|
| 1 | POGM4 | `main` | `skills/commit`, `skills/flextable-quarto-word-captions` | 0 | 0 |
| 2 | NAR_settlement | `phase1-event-study` | none | 0 | 2 pre-existing |
| 3 | zoning2026 | `main` | `rules/ground-truth.md` (retired stub) | 0 | 41 pre-existing |
| 4 | ESG | `main` | none | 0 | 14 pre-existing |
| 5 | affordable_housing_2026 | `main` | none | 0 | 0 |
| 6 | BRI | `main` | none | n/a — no `.qmd` yet | n/a |

All six: 19 agents · 26 skills · 16–17 rules · 12 hooks resolving, zero dangling links,
clean working trees, pushed, rollback backups removed.

### Three more improvements came home rather than being deleted

- **Four hooks** (`context-monitor`, `log-reminder`, `verify-reminder`, `notify.sh`) were
  byte-identical in POGM4 and ESG and absent from the other four. Two projects
  independently carrying the same file is shared infrastructure, not a project override.
  Upstreamed; all six now have them, and POGM4's local copies were dropped so it links
  like everything else.
- **`rules/session-handoff.md`** existed only in NAR_settlement. It makes `/checkpoint`
  verify the active plan's status section rather than trust it — a plan three days behind
  is worse than no plan, because a resuming session believes it. De-projected and
  upstreamed with `templates/handoff.md`.
- **`rules/ai-disclosure.md`** (earlier) existed only in POGM4.

That is the whole point of the fork, demonstrated three times in one session: value that
had been stranded in one paper now reaches all six.

### End-to-end verification

Edited `rules/quality.md` through BRI's symlink, then confirmed: visible immediately from
POGM4 and ESG with no re-apply · shows as an uncommitted change in `research-claude`'s
`git status` · invisible to BRI's own `git status` · revert propagated instantly. That
single test exercises both the payoff and the hazard the design is built around.

### Pre-existing manuscript findings (NOT caused by the conversion)

`prose_number_check.py` now runs in every project. Three manuscripts have unexplained
literals — untouched by these branches, and worth a separate pass:

- **zoning2026** `paper/manuscript.qmd` — 41, including a hardcoded "Section 5.3" that
  should be `@sec-`
- **ESG** `manuscript.qmd` — 14
- **NAR_settlement** `manuscript_NAR_settlement.qmd` — 2, in appendix prose
  ("Figures 1, C1, G1 and I1"; "three figures"). No allowlist file exists in that project,
  so 2 hits across 11,800 lines is a genuinely strong result.

Also cosmetic: ESG's manuscript is `manuscript.qmd`, not `manuscript_ESG.qmd`. The naming
convention governs what the template ships, not what an existing paper is called, so it
was left alone.
