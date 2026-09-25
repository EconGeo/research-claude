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

---

## 2026-09-08 (audit) — Post-completion audit of the Quarto-native pipeline: four defects, all silent

Asked to review the just-completed plan and answer whether the pipeline is fully
functional. It is — but the review found four defects that the plan's own gates
could not have caught, because every one of them fails **silently**: no error, no
log line, just nothing happening.

**Operations**

- Independently exercised the coauthor bootstrap path (`bootstrap-pipeline.sh`, no
  flag) from a bare scratch directory — the one design promise the rollout never
  tested. Clones, detaches at the locked SHA into a project-local
  `.pipeline/research-claude`, links 19/26/16/12 with zero dangling, leaves the
  shared checkout on `main`. **D10 holds.**
- Re-linked POGM4 (`bootstrap-pipeline.sh --tip`), 15 → 16 rules.
- Untracked 142 committed symlinks across five repos; ESG was already correct.
- Wrote `scripts/check_install.sh` and red-tested all six of its checks.
- Audited all twelve hooks against the documented contract at
  `code.claude.com/docs/en/hooks` (fetched, not recalled); fixed three; wired
  `session-guard.py` everywhere; added `templates/settings.json` + an `apply.sh` seed.
- Amended the plan's status banner and its Verification section (staleness sweep).

**Findings**

1. **Committed symlinks in 5 of 6 repos.** `.gitignore` was correct everywhere, but
   gitignore does not untrack what is already in the index, and Step 5 of the plan
   omits `hooks` from its `git rm --cached` snippet (the Task 18 runbook includes
   it). Targets are machine-specific — `../../../../Academic/research-claude/...` —
   so a coauthor's clone dangles before bootstrap and stays permanently dirty after,
   since bootstrap repoints them at `.pipeline/`. Exactly the hazard D10 gitignores
   those directories to prevent. Only mode-120000 entries were untracked; the real
   overrides (`statusline.sh`, POGM4's two skills, zoning2026's `ground-truth.md`)
   stayed tracked.
2. **POGM4 was never re-linked**, so it alone lacked `rules/session-handoff.md`.
   Per-item links (D9) propagate *edits* instantly but not *membership*: a link
   points at a file, not at whatever a directory will later contain. Per-directory
   links would fix that at the cost of the override escape hatch — the wrong trade,
   so membership is now checked instead of assumed.
3. **Three hooks did nothing at all.** `post-edit-lint.sh` read
   `$CLAUDE_TOOL_ARG_FILE_PATH`, which Claude Code does not set and never has, so it
   exited on line one — in the one project that wired it. `session-guard.py` emitted
   a top-level `{"decision":"block"}`, the PostToolUse/Stop shape; PreToolUse honours
   only `hookSpecificOutput.permissionDecision`, so the JSON was ignored and the tool
   ran. `pre-compact.py` blocked via exit 0 + JSON against an undocumented PreCompact
   schema (exit 2 is the documented guarantee). Two more had been fixed days earlier
   for the same class of reason.
4. **`session-guard.py` was wired in ZERO of six repos.** `/freeze` and `/careful`
   write `.claude/state/session-guards.json` and document that the hook reads it and
   blocks edits — so both skills reported themselves active while enforcing nothing,
   and would have enforced nothing anyway given #3. Two independent failures stacked,
   which is why neither surfaced. Root cause: a linked hook is inert until
   `settings.json` names it, `settings.json` is project-owned and never linked (C4),
   and nothing seeded one.

**Decisions**

- **C4 revised.** "Linked but not auto-wired" is a safe default only if no shipped
  skill depends on a hook. Two did. `apply.sh` now seeds `templates/settings.json`
  for new projects; existing projects were brought to the same baseline **after
  asking** — turning six hooks on across six repos is a decision, not a side effect.
- **Membership is a gate, not a convention** — `check_install.sh`, wired into README,
  CLAUDE.md, `rules/shared-pipeline.md` (so it is reachable from any paper session)
  and `/promote` step 5.
- **`pipeline.lock` drift is a WARN, not a FAIL.** In `--tip` mode the lock is an
  install-time provenance stamp; it is only wrong at submission time.
- Left alone: ESG's `manuscript.qmd` naming; POGM4's untracked
  `quality_reports/pipeline_test_2026-09-08/` (not this session's).

**Results**

- `check_fork.sh` exit 0 · `check_install.sh --all` exit 0 across all six.
- All six repos: identical 7-hook / 6-event wiring, every path resolving and
  returning 0 on a real stdin payload.
- Every hook fix verified by piping the actual payload and checking the exit code,
  not by reading the code. Two of those tests first "passed" for the wrong reason —
  a misplaced plan file and a stale sentinel in `~/.claude/sessions/<hash>/` — so the
  initial green results were meaningless until isolated.
- **`check_install.sh`'s override check was vacuous on first write** —
  `! -path '*/.*'` excluded the whole tree, since everything lives under `.claude`.
  It passed on all six repos while checking nothing. The red test caught it; the
  green run had not.

**Commits**

- `9c9ec0c` feat(scripts): add check_install.sh — the project-side gate
- `b12d6e2` fix(hooks): three hooks did nothing at all, and the guard hook was never wired
- one `chore:` commit per paper repo (untrack symlinks; wire session-guard; wire the
  full baseline). All seven repos pushed, clean, at origin.

**Status**

- Done: all four defects fixed, verified and pushed. Plan amended.
- Pending: the pre-existing manuscript prose-number findings — zoning2026 41
  (incl. a hardcoded "Section 5.3" that should be `@sec-`), ESG 14,
  NAR_settlement 2. Not conversion-caused; a separate pass.
- Note: NAR_settlement's `origin/main` is 95 commits behind `phase1-event-study` and
  predates the conversion entirely. Pre-existing, untouched.

**The generalisable lesson.** Every defect here was a *presence* check passing while
the thing checked did nothing. Where a check can be red-tested by injecting the
failure it is supposed to catch, red-test it — the one check I did not red-test first
was the one that was broken.

### Addendum (same session) — cross-session exchange, and a severity correction

Recorded before clearing the window. Everything below existed only in cross-session
messages or in conversation; none of it was durable.

**A defect I introduced this morning and deliberately did NOT fix.**
`skills/revise/SKILL.md:80` names `` `templates/response-letter.md` ``. The file is
`skills/revise/templates/response-letter.qmd` — I converted it from `.tex` during the
fork (see the judgment calls above) and never updated the pointer. One-line fix:

```
-| Response letter | `templates/response-letter.md` | Step 6 — response-letter boilerplate |
+| Response letter | `templates/response-letter.qmd` | Step 6 — response-letter boilerplate |
```

Left unfixed on purpose: `research-62` is running a referential-integrity audit over
exactly these paths, and a file changing under it would move its numbers mid-sweep. It
is flagged to that session as mine. **If the audit does not land it, it is still open.**

**Severity correction to that audit — the number driving the current re-scope.**
`research-62` reported "68 of 108 internal file paths named in shipped files do not
exist," including 55 nonexistent `templates/...` paths, and concluded all 55 resolve to
nothing in all six repos because a paper repo's `.claude/` has no top-level `templates/`.

Independently measured on `main` @ `999f3f9`, distinct paths matching
`templates/[A-Za-z0-9_/-]*\.md`, `zotpilot-skills/` excluded:

| Where named | Distinct | Finding |
|---|---|---|
| `skills/` | 45 | **44 resolve** as `skills/<that skill>/templates/<name>` — skill-relative and correct. 1 broken (`response-letter.md`, above) |
| `agents/` + `rules/` | 26 | 3 resolve at root `templates/`; **19 name a file that exists under some skill's `templates/` but is unreachable from an agent or rule** (pointer-precision, not missing capability); 4 resolve nowhere |

The inference that no `.claude/templates/` implies the skill paths dangle does not hold:
`.claude/skills/submit` is a symlink to the canonical skill **directory**, which contains
`templates/`. Verified in BRI — no top-level `.claude/templates/`, and every per-skill
template present through the skill symlinks.

So the surface splits three ways rather than one: **~44 false positives · ~19 real but
cosmetic · ~12 genuinely absent.** The 12 are the 4 dead templates, plus
`scripts/generate_dashboard.py` and `scripts/generate_html_report.py` (confirmed absent,
named in 7 and 5 shipped files), plus the six missing `references/*.md`. Those are real
and were confirmed independently.

*"68 missing files" implies rebuilding capability across nearly every agent; "12 missing,
19 mis-pathed, 44 fine" is a smaller and differently-shaped job.* Sent to `research-62`
as check-me rather than correction — denominators may differ definitionally (occurrences
vs distinct, non-`.md` paths), but the resolution-base disagreement accounts for 44 and
is not definitional. **Unresolved at window close: that session had not replied.**

**Decision D-D — ruled, then overtaken.** The shared checkout was found on
`fix/critic-dispatch`, so all six papers were running an in-progress branch through their
symlinks (BRI's `rules/quality.md` verified byte-identical to the branch tip).
`check_install.sh` does not detect this — it emits only a lock WARN that reads like
ordinary tip drift. Drew ruled *accept knowingly + add a branch check*; the recommended
shape is FAIL unless the checkout is on `main` or detached at the project's lock SHA,
with an explicit opt-out env var downgrading to WARN, so "accept knowingly" is something
someone must say rather than a silent default. **Not implemented** — Drew then stood this
session down, and `research-62` returned the checkout to `main`, making it moot for now.
The check remains unwritten and the gap remains real for the next person who checks out a
branch here.

**Cross-session state at window close.** `research-62` owns the pipeline work: its
critic-dispatch plan is paused in favour of an audit-first re-scope, its `/discover` edit
is in `stash@{0}`, and `check_fork.sh` criteria 9a/9b live only on `fix/critic-dispatch`
at `cd1d47a`, unmerged. Checkout on `main`, clean, six repos verified resolving.
`pogm4-91` is on the POGM4 manuscript rewrite and is not involved.

**Method lessons, all earned the hard way this session.** Four instances of the same
failure, in which *the green result was the bug*: `check_install.sh`'s `! -path '*/.*'`
matching nothing; criterion 9a written against an assumed surface; my `grep $SHIP` scan
returning 0 because **zsh does not word-split unquoted parameters** (bash does — the six
directories collapsed into one nonexistent path and grep's error went to `/dev/null`);
and my orchestrator count of 34, which searched the stem `orchestrat` and swept in
"orchestration"/"orchestrated" while I labelled it `orchestrator` — the real figure is 30.
Red-test every check by injecting the failure it exists to catch. A number is not evidence
until you have read what produced it. And when a path assertion fails, question the
resolution base before the file.

## 2026-09-10 — Handoff §1/§2e, the any_of hint, and the live tier's first real run

**Operations:**
- Moved `~/pipeline-repair-handoff.md` → `docs/2026-09-10_final-cleanup-handoff.md` (`4cf76a8`).
- §1: dropped the stash (verified byte-identical to the committed patch first), deleted
  `fix/critic-dispatch` after diffing `cd1d47a` against the shipped gates.
- Fixed `any_of` swallowing its branches' `producer` hints (`eeb21da` → `616d719`), red-first.
- §2e: `JHousE` in all three real `journal-profiles.md` copies; consumer `zoning2026/CLAUDE.md`
  updated (ESG `ce7c32b`, zoning2026 `342e870`).
- Built and exercised the live tier (`a70885b`, `d6f4a9e`, `12cbcee` → `dc293d7`).
- Fixed `check_install` membership counting `hooks/__pycache__` (`3b64af0` → `1513246`).
- Pushed `7268017..be1e8d4`; `main` in sync with `origin/main`.

**Decisions:**
- Do NOT run `/pipeline run` in a paper repo — POGM4's state file is younger than the work it
  tracks, so every stage reads unstarted and `writer` would be pointed at a manuscript already
  through three referee rounds. The fixture is the vehicle.
- The live tier asserts MECHANISM, never OUTCOME. Strategy scored 61 on round one; an
  assertion that a run *reaches* a stage would depend on an LLM clearing 80 on a synthetic
  fixture, which is not a property of the pipeline.
- Left §2b/§2c alone — deliberate prior decisions with recorded reasons.
- Left the live tier RED rather than tuning it green: `--yes` covers approval gates, not a
  stage asking a substantive question.

**Results:**
- **The enforcement chain ran for real under the driver for the first time:** `strategist` →
  `strategist-critic`, both `source: "hook"` (dispatch-log.py on SubagentStop) with a real
  session id, `strategy=61.0`, `strikes {strategist: 1}`, `overall 68.71`; `critic-pairing.py`
  correctly did not block a matched pair.
- Six live-tier defects found and fixed, three of them introduced by this session's own
  hardening. Full list with mechanisms in the handoff's progress log.
- `claude -p` **exits 0 on an unknown command** (tested) — exit code is not a usable success
  signal for it.
- `check_install --all` had been red since 06:22 and nobody had run it.
- **Open, not fixed:** `quality_reports/session_logs/` is written by `log-reminder.py` and read
  by `pre-compact.py`/`post-compact-restore.py`, but `rules/logging.md` never defines it —
  compaction recovery reads a directory nothing is instructed to write.

**Status:**
- Done: handoff §1, §2e, §2f (built + exercised); `CLAUDE.md` now points at the handoff.
- Pending: §2a (109 prose literals), §2d (upstream ZotPilot), the `session_logs/` question,
  the six `pipeline.lock` files still recording `8bb6218`, and a full green `--live` run.

## 2026-09-16 — Skill token optimization: Tasks 0–8 complete

Executed `docs/plans/2026-09-16-skill-token-optimization.md` end to end. Nine branches, each
merged to `main` with `--no-ff` after its own green verification.

**Operations:**
- `fix/session-guards` (786379e), `fix/submit-coverage-check` (fdf17a3),
  `refactor/review-skill` (745794f), `refactor/strategize-skill` (ea89319),
  `refactor/write-skill` (4e765ce), `refactor/discover-skill` (4333ec2),
  `refactor/checkpoint-skill` (52a3267), `feat/checkpoint-improvement-candidates` (35f82d5)
- New tests: `tests/test_session_guard.py` (12 cases), `tests/test_submit_gate.py` (2),
  `tests/test_skill_contracts.py` (3 — step-binding, allowlist staleness, Level-2 budget)

**Results — Level 2 (SKILL.md bodies, loaded in full on every invocation):**

| | baseline | after | change |
|---|---|---|---|
| The five refactored skills | 63,573 | **37,756** | −41% (target ≤38,000 ✓) |
| All 18 skills | 121,621 | **98,672** | −19% (~30,399 → ~24,668 tok) |
| One `/pipeline run` (8 skills) | 73,176 | **50,819** | −31% (~18,294 → ~12,704 tok) |

Per skill: review 18,058→10,878 · strategize 15,966→7,967 · write 11,290→7,482 ·
discover 9,733→5,934 · checkpoint 8,526→5,495. `submit` grew 4,779→5,192 (the R-133 coverage
check), and `careful`/`freeze` grew (the corrected guard documentation) — both deliberate.

Test suite 142 → **159 passed**, `check_fork.sh` PASS.

**Decisions:**
- **D1 — `/strategize pap` score scope: user chose (b).** The PAP now records with
  `--scope section:pre-analysis-plan`. Verified by reading `scripts/pipeline.py:483` in full:
  only a `section:`-prefixed scope writes `state["sections"]`; a bare `--scope pap` would still
  overwrite the component. R-103's mandatory PAP critic is intact. Accepted consequence —
  `pipeline.py next` reports `strategy` unscored for a PAP-only project — is recorded in
  `skills/strategize/gotchas.md` so it is not later "fixed".
- **`disposition-pool.md` vs `agents/editor.md` on the 0-FATAL case: editor.md wins.** Zero FATAL
  with 4+ ADDRESSABLE is a Major revision. The losing copy's duplicated peeve pools, decision
  rule and report formats were deleted rather than corrected — a second copy only drifts again.
  The file now owns only the six disposition definitions, which nothing else in the tree defined.
- **Data feasibility grade A–D vs A–F: both, reconciled.** The explorer-critic's six categories
  separate practical feasibility from the four fit categories, so the grade measures **access
  effort** (the skill's semantics), extended with the template's **F** = not obtainable.
- **Improvement loop: `/checkpoint` → `/promote`, not the audit's P6.** P6 would put a closing
  instruction block in all 18 SKILL.md files — the exact per-invocation tax this plan removes.

**Defects found and fixed beyond the plan's tables:**
- `references/journal-profiles.md` pointed at `editor.md` for the disposition definitions;
  `editor.md` never had them.
- `/review --code` routed to "categories 4-12"; the agent and template both say 5–16, split
  1–4 strategic / 5–16 quality.
- `/write style-guide`'s inline workflow omitted the protocol's **self-citation check**, so
  self-citation keys missing from `references.bib` went unreported.
- `/discover` said the explorer-critic runs a "5-point assessment"; it runs six categories.
- `/checkpoint` Step 3 told the model to ask "Look right? I'll save all of this" and wait — a
  blocking prompt the user's global `CLAUDE.md` has standing instructions against. Removed.
- `/checkpoint` never performed the plan staleness sweep, the handoff reference dry-run or the
  `ai_use_log.md` confirmation that `session-handoff.md` and `ai-disclosure.md` require. Added as
  report lines, not prompts.
- `/tools learn` claimed "auto-memory handles corrections automatically" — silent
  self-modification, which `meta-governance.md` forbids. Repointed.

**Two findings worth carrying forward:**
1. **No re-link was needed.** Task 8 Step 4 assumed membership changes require `apply.sh --link`.
   Each skill is a *directory* symlink into this tree, so files and subdirectories created or
   deleted inside an existing skill propagate immediately. Verified in `NAR_settlement`:
   `causal-audit-4-phases.md` present, `referee-report-template.md` absent,
   `checkpoint/references/` present, `discover/references/` gone. `check_install`'s `membership`
   check passes in all six projects. A re-link is only needed for a brand-new top-level skill.
   (Also note: the plan's command `./apply.sh --link` is wrong — `--project-dir` is required.)
2. **`check_install --all` is RED — known and deliberate, but one project is worse than
   recorded.** `docs/2026-09-10_final-cleanup-handoff.md` records `clone-links` as failing
   **BRI, NAR_settlement, POGM4 and zoning2026** on purpose: each needs real copies of the three
   `references/*` files before a coauthor clones it. That is still true and is not this work
   (BRI's links date to `cd60ca1`, 2026-06-17).

   **New:** ESG also fails, and the handoff says ESG was *fixed* by `9349a8e` on `main`. ESG is
   checked out on `pipeline-adoption`, and `9349a8e` is **not an ancestor of that branch** — the
   three links are still committed there (mode `120000`). The fix has not reached the adoption
   branch, so ESG regresses into the failure if that branch merges. Worth resolving before the
   adoption lands.

**Deliberately not implemented** (so the next audit does not re-raise them):
P2 `disable-model-invocation` (breaks `/pipeline`, which invokes stage skills by name), P4
"5–10 options per decision point", P6 as specified, P7 eval suite (needs a mock ZotPilot MCP
server).

**Status:**
- Done: Tasks 0–8. Plan's Progress Log is complete and is the detailed record.
- Pending, from the audit and unchanged by this work: §4 Med/Low defects in `review`
  (`--theory` has no mode section, `--variance` undocumented), `revise`, `tools`, `ztp-data-tag`,
  `lit-position`, `pipeline` (possible double-strike — **unverified**, confirm before fixing),
  `promote`, `state/`; P5 subagent routing; `allowed-tools` accuracy; P7 evals; and the two worst
  P1 offenders, `ztp-tutor` (431 lines) and `humanize` (205), which live in vendored trees and
  need upstream PRs to `EconGeo/ZotPilot` and `EconGeo/ai-audit` before a re-sync.
- Also open: the six `pipeline.lock` files record `f7f49af`, now 30+ commits behind.

## 2026-09-24 — Skill defect close-out: Tasks 1–7 complete (the stalled 09-16 plan)

**Plan:** `docs/plans/2026-09-16-skill-defect-closeout.md`, stalled since 09-16, unblocked by the
09-24 connectivity plan's Task 6, executed today one task per branch with red-first tests. Every
task's Progress Log row carries the full account; this entry is the cross-task record.

**Operations (one merge per task, all on `main`):**
- Task 1 `c5df76a` — `/review --theory` mode section; `--stress` records nothing (gauntlet path
  registered under `editor`'s `produces`); `--variance` named only to refuse; Scoring table gained
  Theory and Replication; **D3(a)** applied: Editor rubric in `scoring-rubrics.md` (mean of the two
  referee scores clamped to the decision band — Accept 90–100 / Minor 80–89 / Major 60–79 / Reject
  0–59) and an `**Overall score:**` line in `editorial_decision.md`.
- Task 2 `7c031a9` — `/revise` runs `post writer` before the letter; letter written from
  `response-letter.qmd` as `.qmd` with anchors, never page numbers; REWRITE added to
  `rules/revision.md`; Bash pre-approved; two templates bound, catalogue deleted, `KNOWN_UNBOUND` −2.
- Task 3 `a281b5b` — `state strike` has one owner per creator: the stage skill (rule in
  `rules/agents.md` §3); driver reads the count; strike lines added to `/discover data`,
  `/strategize theory`, `/analyze` (data-engineer), `/talk`; `review` and `submit` are stated
  exceptions.
- Task 4 `69e3e3f` — `/tools render` resolves the manuscript; lint default matches the hook;
  `validate-bib` and `journal` have real steps; `context` deleted; `tools/gotchas.md` deleted.
- `/tools commit` gates `4c68b6c` (user request, outside the plan): Gate A before `git commit`,
  Gate B before PR/merge, both honouring `--yes`; `--yes` never skips Step 0.
- Task 5 `d91b540` — `ztp-data-tag` writes the Data note before the `data-tagged` marker and
  reports the skip; `lit-position` runs the local sweep before `/ztp-research`; Bash added.
- Task 6 `7885356` — `promote` reads `# installed via:`; re-link commands carry `--project-dir`;
  `state/obsidian-config.md.example` no longer names the deleted skill; `check_refs` scans `state/`
  and `.example`; `new-project-ztp` anchor and index estimate fixed. **D2 moot** (`/humanize` →
  `/civilize` upstream, `c737ac6`).

**Decisions:**
- D3 → (a), user, 2026-09-24. Rubric band values are a policy choice; change the four bands if
  wrong, the tests pin only that the rubric section and the score line exist.
- D2 → moot; `/write humanize` keeps its name.
- Task 1 fix 2 (wire `--variance` with N-referee dispatch) **not applied**: the user's 09-24 ruling
  (repair plan Phase 2.5, D-19) says do not build variance dispatch. `/review` refuses the flag.
- Task 3: `review` and `submit` exempt from the strike rule, by their own reference files.
- Task 4: `/tools context` deleted rather than documented (the hook needs a harness-supplied
  `transcript_path`; built-in `/context` exists); `/tools journal` reframed from "regenerate" to
  "append what the state file shows is missing" because `rules/logging.md` defines it append-only.
- Task 6: `## Current Project State` exists in two of three real projects but no template, so the
  anchor became "update `## Tools` in place, else append at EOF".

**Contradictions resolved — which copy won and why:**
- `--stress` recording (skill) vs "no editorial decision letter" (agent): **agent** — it is what
  runs; the skill now says records nothing.
- Editorial-decision score source: none existed; **new rubric** created (D3a).
- `--variance` enforcement delegated by the agent to a skill that never mentioned it: **neither**
  wires it; both now say it is refused (D-19).
- REWRITE in the skill, absent from the rule: **skill** — the registry declares pairings, not
  classes; the rule gained the row.
- Letter format: skill's "page/section references" vs template's "never a page number":
  **template** — it is what ships to an editor.
- Strike ownership: driver vs stage skills: **stage skill**, mirroring the `record-score`
  convention every `references/<stage>.md` already states.
- Lint default: skill's "acquire + explorations" vs hook's single target: **hook** — it runs.
- `tools/gotchas.md` vs SKILL.md (3): validate-bib claim (now false, dropped), journal-selection
  bullet (described `/submit target`, dropped), `.claude/state/` staging rule (folded into commit).
- `promote` checkout test: `commit=` (always present) vs `# installed via:` — **the lock's last
  line**, per `apply.sh`'s `write_lock()`.
- `new-project-ztp` index estimate vs README: **README** (200 papers ≈ 10–20 min, Ollama
  recommended).

**Found in passing and fixed:** `artifact-paths` allowlist named the referee letter as `.md`
(Task 2); `check_paths` caught an unprefixed hook path (Task 4); the plan's Task 7 expected
`check_install --all` RED on `clone-links` — it is PASS in all six repos since the 09-23
reference-linking change (D-26); `CLAUDE.md`'s `templates/` sentence named files that live in
`seeds/` (corrected today).

**Budgets moved (all upward, each with a reason in `tests/test_skill_contracts.py`):** review
11,500 → 12,500 (mode section for a weight-20 component); discover 6,000 → 6,200 (strike line).
Measured today: all 18 SKILL.md bodies 114,966 chars (phase-1 baseline 98,672, +16.5%); the
eight pipeline-run skills 56,656 (baseline 50,819, +11.5%). Correctness text, not prose creep —
every addition is a dispatch, a gate, a record line or a refusal.

**Results:** 274 tests OK (218 at the start of the day, +56 across seven new test files) ·
`check_fork` PASS · `check_paths` PASS · `check_refs` 0 FAIL · `check_install --all` PASS ×6 ·
`run_fixture` mechanical PASS · **`run_fixture.sh --live` GREEN for the first time** (explorer →
explorer-critic → strategist → strategist-critic via hook; data=92, strategy=84; exit 0).

**Commits (research-claude, main):** `1edcffa` docs pointer + June plans closed; `c5df76a`,
`7c031a9`, `a281b5b`, `69e3e3f`, `4c68b6c`, `d91b540`, `7885356` (task merges); plus the close-out
commit that carries this entry. Paper repos: pipeline.lock refresh committed in all six;
POGM4 `e6a99bc` (Phase 1.6); ESG `98de0c5`, `1d072d7` (adoption round, field audit, script).
**Nothing pushed anywhere** — `main` is ~15 ahead of origin; five paper repos ahead of theirs.

**Status:**
- Done: the 09-16 plan in full (Tasks 0–7); every carry-forward item from the 2026-09-10 handoff
  is closed (R-136 is detected by `hooks-wired` deriving from the seed; live tier green;
  `clone-links` PASS ×6; locks refreshed 09-23 — re-warn on every commit by design, refresh at
  submission; POGM4's leftover `.html` is gone).
- Still open from the 2026-09-15 audit, unchanged by this plan and recorded in its "What this
  plan deliberately leaves open": the other **P4 option points** (`/tools commit` is now done);
  **P5 subagent routing**; the full **`allowed-tools` sweep** (`strategize`, `discover`, and
  `mcp__zotpilot__*` pre-approval); **P7 evals**; the **vendored P1 offenders** (`ztp-tutor`,
  `civilize`) and `seed-papers`' domain-profile field — all upstream work;
  `skills/submit/templates/audit-10-checks.md` still in `KNOWN_UNBOUND`.
- Pending (user): push research-claude and the six paper repos.

## 2026-09-24 (later) — Audit residue: allowed-tools sweep, KNOWN_UNBOUND emptied, plan for P4/P5/P7

**Context:** "Start the remaining plan items" — the residue the 09-16 close-out listed under
"What this plan deliberately leaves open". Two items were closable without a decision; the
other three are design work and got a plan with the decisions named.

**Operations (one merge per item, on `main`):**
- `736939f` **allowed-tools sweep.** `discover`, `strategize`, `write` run `pipeline.py` and
  now pre-approve `Bash`; `lit-position`, `new-project-ztp`, `ztp-data-tag` and (from the
  second merge) `pipeline` call `mcp__zotpilot__*` and now pre-approve it. New
  `tests/test_allowed_tools.py` derives both requirements from the SKILL.md body, so it went
  red on `pipeline` the moment the second merge put the ZotPilot check in the driver — the
  check working as intended. `mcp__zotpilot__*` spelling is per the permissions docs (fetched
  this session): an allow glob is valid only after a literal `mcp__<server>__` prefix.
- `7365613` **KNOWN_UNBOUND emptied.** `skills/submit/templates/audit-10-checks.md` deleted:
  `agents/verifier.md` is the one pass/fail definition (both files said so), the skill's own
  list indexes into it, and the 09-23 inventory found the copy drifted a second time.
  `/submit final` now reads `gotchas.md` before reporting. `pipeline/SKILL.md` `run` binds
  `references/setup.md` before the loop (a normal run previously skipped the ZotPilot check)
  and names `talk.md` in the stage list. The ratchet is a real `set()`, not `{}`.
- `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md` written: Part A option gates
  (one shared `rules/option-gates.md`, `--yes` takes rank 1, picks recorded in the artifact the
  step already writes, 12 tasks), Part B subagent routing (registry-declared agents with
  `mcpServers: [zotpilot]`, the `lit-critic` shape), Part C a stdio ZotPilot mock and the first
  two mechanism evals. Open decisions D1–D5 with recommendations; Part A is executable now
  under them.

**Found in passing:** `check_paths` caught a bare `references/setup.md` (Global constraint 9
again); `check_install --all` fails its `[branch]` check on any feature branch by design —
run it from `main` after the merge.

**Results:** 275 tests OK (+1) · `check_fork` PASS · `check_paths` PASS · `check_install --all`
PASS ×6 from `main` · `run_fixture` mechanical PASS (inside `check_fork`).

**Status:** Open from the 09-15 audit: P4, P5, P7 (planned above, awaiting D1–D5); vendored
P1 offenders and `seed-papers` (upstream). Pending (user): push research-claude and the six
paper repos — still nothing pushed.

## 2026-09-24 (evening) — Option gates, subagent routing, functionality evals: plan executed in full

**Plan:** `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md`, D1–D5 answered "go
with recommendations" by the user, then A1–A13, B1–B6, C1–C3 one branch per task, red test
first, `check_fork` + full suite before every commit.

**Part A — option gates (`rules/option-gates.md`, 12 gated modes).** One rule defines the
mechanism (5–8 ranked options, `--yes` takes rank 1, pick recorded in the artifact the step
already writes; never between a critic score and the below-80 loop). Gates in strategize,
discover ×4, lit-position ×3, submit target, review --peer ×2, revise ×2, talk, write ×2,
pipeline (strike-3 menus from ranked Escalation blocks; theory opt-in), analyze, ztp-data-tag
(+ Step 5b tag merge). Every stage reference passes `--yes` through.
`tests/test_option_gates.py` checks each declared gate. Caps raised with reasons: strategize
8,000→8,500; discover 6,200→7,500; write 7,600→8,200; review 12,500→12,700.

**Part B — routing.** Three registry-declared read-only agents with `mcpServers: [zotpilot]`
where needed: `data-tag-extractor` (per-batch records), `lit-scout` (local sweep + in-library
citation chains; `/ztp-research` stays in the main context), `journal-scout` (the 547-line
profiles read). D4b: Obsidian sync stays home, reason in `checkpoint/gotchas.md`. revise/write
list the manuscript's labels and headings; the writer reads. explorer keeps its web tools —
read in full, its search uses them, so the audit's "unused" did not hold for the agent.

**Part C — evals.** `tests/mock_zotpilot.py`: a stdio MCP stand-in for ten ZotPilot tools
from a checked-in fixture, logging every CALL/WRITE to a file named in the MCP config's env.
`tests/evals/ztp-data-tag.sh` PASS (extractor dispatched before any write; 0 writes because
`--yes` never answers the batch confirmation — noted as vacuous by the checker).
`tests/evals/lit-position.sh` PASS (lit-scout before external search; no writes in the sweep).
Both checkers are unit-tested red and green.

**Found and fixed (not caused by the gates):**
- `hooks/protect-files.sh` blocked every stage from closing since `5305d11`: its
  `*-critic_*.md` pattern denied the Write that saves a returned critic report, so `post`
  never saw one. The 12:47 green run had saved through Bash. Creation now allowed; Edit and
  overwrite blocked; `rules/agents.md` §3 names round files `_r2`/`_r3`.
- Live tier under `--yes`: two data rounds ran, score and strike recorded; the run halted only
  when `claude -p` refused the round-2 `record-score` Bash call. The fixture now pre-approves
  `pipeline.py` for the live tier.
- Mock: MCP results need the `content` envelope; the client does not forward server stderr.

**User instruction (standing):** keep-on-failure is the default for these tests and builds —
`run_fixture.sh` and both eval runners now keep their temp copies on any failure.

**Results:** 302+ tests OK · `check_fork` PASS · `check_install --all` PASS ×6 (re-linked for
three new agents and one new rule; lock refresh committed in each paper repo) ·
`run_fixture --live` GREEN · two evals PASS. **Nothing pushed** — main is ~50 ahead of origin.

**Open:** the plan's "What this plan deliberately leaves open" — vendored P1 offenders
upstream; P6 self-improvement rule needs its own decision; evals for the remaining skills one
at a time; a same-day round-2 collision is now a naming rule, not a mechanism.

## 2026-09-25 — Residue close-out: P5 tools row, overall round cap, a third eval

**Scope.** "Run the remaining plans and clean up." Every plan under `docs/plans/` was already
marked complete; the live residue was the option-gates plan's "deliberately leaves open" list.
Of it, the pipeline-side items closed here; the rest is upstream or a decision.

**`/tools validate-bib` → `scripts/validate_bib.py`** (`2dfbd8f`, shipped via `SHIPPED`,
`tests/test_validate_bib.py`, 10 tests). The inline shell pipeline wrote to shared `/tmp`
paths and could not be tested. The script reads the `.bib` name from the manuscript YAML,
excludes Quarto cross-ref prefixes and e-mail addresses, exits 1 on MISSING/DUPLICATE, 2 when
it cannot run. My first test asserted the fixture cited a missing key `@example`; reading the
line showed it was `fixture@example.edu` — the test premise, not the script, was wrong.
**`/tools journal` stays home** after re-audit: since `69e3e3f` it appends from `state show`
and the dispatch-log tail — three short commands, no loop to route. Reason recorded in the
plan's residue list.

**`limits.rounds_overall` enforced; `verification_retries` deleted.** The overall cap was a
sentence in `rules/agents.md` §3 and `permissions.md`, read by nothing. `state strike` now
refuses (exit 1, nothing recorded) once strikes summed across creators reach it, and prints
the running total. `verification_retries` had no consumer in scripts, hooks, skills or agents;
deleted from the registry, the renderer and the two prose mentions rather than kept as a
claim. `TestNoPhantomLimits` fails on any declared limit `pipeline.py` does not read.

**Third eval — `tests/evals/tools-validate-bib.sh`** (`c286f44`). First with no MCP server.
The first live run FAILed: the session wrote `SESSION_REPORT.md` after the check because
`rules/logging.md` asks for one, and the checker's "nothing writes" was too broad. Narrowed
to `.qmd`/`.bib` targets, unit-tested both ways, fresh run PASS (4 Bash calls, script ran,
no inline re-implementation).

**Docs.** 06-17 design doc marked superseded with its plan; 09-23 repair plan marked complete
(Phase 5 is POGM4's own — 1.6 is committed there as `e6a99bc`). `CLAUDE.md` § Start here
repointed.

**Fleet.** `validate_bib.py` is a new shipped file → re-linked all six repos; each lock refreshed
and committed (`pinned` mode kept, as the prior refresh recorded). `check_install --all`
PASS ×6.

**Results:** 326 tests OK · `check_fork` PASS · `check_install --all` PASS ×6 ·
`run_fixture` (mechanical) PASS · `tools-validate-bib` eval PASS. `run_fixture --live` not
re-run this session (the strike change adds a refusal at 5 total strikes; the live tier's two
rounds stay well under it — `TestOverallRoundLimit` covers the boundary).

**Still open, none of it in this repo's hands:** vendored P1 offenders (PRs to the
`EconGeo/ZotPilot` / `EconGeo/ai-audit` forks); the P6 self-improvement rule (a decision
against `meta-governance.md`'s 3+ project bar, then a plan); evals for the remaining 20
skills, one per task.

## 2026-09-25 — Improvement loop (P6) and Quarto render gate; merge to main

**Scope.** Close the P6 self-improvement residue and use its first repeated ledger entry to
land the Quarto silent-failure fix those corrections never reached the shared tree with.
Built on `improvement-loop` branch, then merged to `main` and closed out.

**Branch commits (oldest first):** `faff6c6` plan · `1be0cab` `scripts/ledger.py` ·
`5a363a5` ledger seed · `1ff3895` `rules/meta-governance.md` — User corrections + pointers ·
`2b42e69` `rules/logging.md` wording · `423e5c3` checkpoint 4a + budget 5,500→5,900 (measured
5,611) · `02c137d` promote Step 2b · `d1a6322` `references/quarto-authoring.md` + five
bindings (write trimmed to 8,199) · `98c776d` `check_render.py` + gate item 4 · `5c20cda`
ledger rows landed · `afb7cda` `check_render` regex fixes (COLUMN non-digit boundary, DOUBLED
same exhibit word).

**Decision.** The 3+ project bar in `rules/meta-governance.md` governs only log-inferred
learnings; a user correction is instead asked once at the moment of correction and lands via
`/promote`, otherwise `/checkpoint` writes it to `docs/improvement-ledger.md` and `/promote`
flags a target two projects named. The ledger's first REPEATED target — Quarto silent-failure
corrections, made in two projects — was closed by shipping the authoring reference bound into
`writer`/`coder`/`write`/`talk`/`quarto-empirical` and by `scripts/check_render.py` as
write-gate item 4.

**Merge.** `improvement-loop` merged into `main` with `--no-ff` in a temporary worktree
(`research-claude-main-tmp`), merge commit `e1923167eaa7f9646e3f2c63cb81caf12a4ca656`. No
conflicts. Not pushed.

**Results:** 355 tests passed (3 subtests) · `check_fork` PASS (pre-existing WARNs only —
unprefixed vendored paths, orphan files, `ztp-ollama` never invoked). Smoke test:
`check_render.py /Users/andrew.mueller/Research/NAR_settlement/manuscript_NAR_settlement.pdf
--expect "IS NOT MET"` → 0 findings.

**2026-09-25 (later) — fleet re-link and final-review fixes.** All six paper repos
(`BRI`, `ESG`, `NAR_settlement`, `POGM4`, `zoning2026`, `affordable_housing_2026`) re-linked
with `apply.sh --project-dir <p> --link` (pinned mode kept — `# installed via: pinned` in each
`.claude/pipeline.lock`), locks refreshed to `1b11285` and committed: `BRI` `e50231a`, `ESG`
`3cd1cab`, `NAR_settlement` `2039c39`, `POGM4` `c7a717d`, `zoning2026` `8072475`,
`affordable_housing_2026` `3864103` (each is `git log -1 --format=%h .claude/pipeline.lock` in
that repo). `./scripts/check_install.sh --all` PASS. `~/.claude/references/quarto-authoring.md`
is now a symlink to the canonical checkout's `references/quarto-authoring.md`. Separately, a
final-review fix wave landed as `b3bb593`, closing four Important findings: `/promote` now
commits the ledger after acting on it (Step 2.6); `ledger.py add` normalises a `.claude/`- or
`./`-prefixed `--target` and rejects `|` in `--project`/`--target`; `check_render.py`'s DOUBLED
check is anchored to a caption line and catches a doubled exhibit with a *different* number
(a renumbering artifact, not just a copy-paste one); its COLUMN check binds captions with
appendix letters (`Table A1:`) and matches a header on a word boundary instead of by substring.
Also landed: `norm()` joins hyphenated line breaks and maps curly quotes, and the Quarto
authoring reference's binding moved earlier in `/talk create` and out from under a
Results-only heading in `agents/writer.md` so it applies to every section.

**Still open.** Vendored P1 offenders (already tracked), evals for the remaining skills, and
the 3+ bar for log-inferred learnings remains unenforced (no cross-project source; recorded,
not built).

## 2026-09-25 — Evals for the remaining twenty skills: plan executed in full

**Scope.** Close the last residue of the 09-24 evals plan: one functionality eval per remaining
skill, twenty tasks, under `docs/plans/2026-09-25-remaining-skill-evals.md`. Built on
`evals/remaining-skills-7tvb54` (in place, not a worktree — see Rulings), subagent-driven, one
implementer per task (Tasks 4–10, the six same-shape mock evals plus `/promote`, as one
batch), a review after each, live runs sequential. Nothing under `agents/`, `skills/`,
`rules/`, `hooks/` or `templates/` changed; everything landed under `tests/`.

**Branch commits (oldest first):** `6eb8755` Task 0 — `tests/evals/_lib.sh`,
`tests/evals/evallib.py`, mock grows the ten tools the vendored skills call · `3276e7e`
careful · `5b71fa8` freeze · `c9c76d1` + `b5bf148` checkpoint · `1cc523c` new-project-ztp ·
`a13e234` seed-papers · `9155b4a` ztp-review · `2e16624` ztp-research · `d84b78a` ztp-profile ·
`47f1a39` ztp-tutor · `32cb6d6` promote · `0c53b10` civilize · `fae8ae7` + `922f047` +
`204211f` verify-claims · `76474d6` revise · `a799004` submit · `8649a94` + `2514c87` talk ·
`77011fb` write · `361654a` strategize · `0c3029e` + `8858419` discover · `cf46507` review ·
`7268dc5` analyze · close-out commits (this entry).

**Results by live run.** 15 PASS (1–11, 16, 18–20; four of those — 3, 11, 16, 18 — after a
harness fix and a clean re-run) · 5 `FAIL (skill)`: `/verify-claims` (vendored), `/revise`, `/submit final`,
`/talk create`, `/strategize`. Each red is a finding recorded in the plan's Findings with the
failing assertion and the `SKILL.md` step it contradicts; the checkers were not loosened. The
skill fixes are the open work (the `/verify-claims` one is a PR to `EconGeo/ai-audit`).

**Rulings** (the SDD ledger under `.superpowers/` is gitignored, so they are recorded here):

- **In-place branch, not a worktree.** `agents/`, `skills/`, `rules/`, `hooks/` are linked
  into every project from *this* checkout; an eval that links the checkout into its temp
  project must link the one under test. A worktree would have evaluated main's skills against
  the branch's checkers.
- **`/verify-claims` checker keeps the report-file assertion.** The vendored `SKILL.md` Phase 4
  says "return the report and let the user decide" and names no file, but `registry.yaml`
  `claim-verifier.produces` expects `quality_reports/verify_claims_*.md`, which `/submit` and
  `/review` read. The registry is the contract; the red is the vendored skill's.
- **`/talk create` fixture.** `tests/fixture-project` ships a pre-committed
  `talks/manuscript_fixture.qmd` symlink; `talk.sh` removes it before the run so the skill's own
  symlink step is exercised. `check_talk.py` allows `tbl-` embeds after the first
  `backup|appendix|q&a` heading, because `SKILL.md` puts tables in backup slides; the main deck
  stays bare-filename only.
- **`_lib.sh` drift check narrowed.** `eval_finish` compared unfiltered `git status
  --porcelain` and tripped on untracked scratch files outside the linked tree. Both snapshots
  are now filtered to paths under the linked dirs (`LINKED_DIRS_RE`); the inline checks in
  `checkpoint.sh` and `promote.sh` match.
- **`evallib.main_session_tool_uses()`.** `claude -p --output-format stream-json` flattens a
  dispatched subagent's tool calls into the transcript, tagged only by `parent_tool_use_id`.
  Every "the main session never X" assertion (web tools in `/discover`, and any future one)
  filters to lines without that field; `evallib.tool_uses()` stays the whole-transcript view.
- **Batch dispatch for Tasks 4–10.** Six mock evals of one shape plus `/promote` went to one
  implementer to keep the runner idiom identical; live runs still ran one at a time.

**Final review (fix wave).** `check_strategize.py` now asserts Step 5's rule instead of the audit's
"exactly one record" (a correct sub-80 run would have gone red); `evallib.bash()` joins shell
line continuations so `check_promote.py`'s "never pushes" cannot be slipped by `git \`+newline;
`promote.sh`'s plant now carries a noun `check_fork.sh` actually scans (`zoning`) — the journal
name alone was never in its scan, so only the skill's own Step 4 refusal stood between it and a
commit; `check_civilize.py` no longer flags a relative `quality_reports/` Write; the plan's
convention bullets record the flattened-subagent transcript and the on-disk-facts practice.

**Close-out.** Plan Progress Log filled (commit per task; rows 12–18 trimmed to the checker's
summary line, diagnoses moved to a Findings list). 09-24 plan's "20 remain" bullet and
`CLAUDE.md` § Start here repointed at the 09-25 plan.

**Results:** 469 tests OK (1 skipped) · `check_fork` PASS (pre-existing WARNs only) · 20 live evals
recorded in the Progress Log: 15 PASS · 5 `FAIL (skill)` · 0 `FAIL (design)`. Run in a cloud
container: Quarto, R, xelatex and the fixture's R packages were installed for the run (CRAN is
blocked there, so `fixest`, `modelsummary`, `tinytable`, `tables`, `data.table`, `xfun`, `knitr`,
`rmarkdown`, `evaluate` came from their GitHub sources); no live `claude -p` re-runs this step.

**Deferred minors** (from the task reviews, none blocking): `evallib._MOCK` splits on the
literal `" -> "`; `check_freeze.py`'s two predicates both match `talks/manuscript_fixture.qmd`;
`check_promote.py`'s regexes miss line-continued git commands; the checker scripts are
inconsistently `+x` (the runners invoke them through `python3`, so nothing depends on it).

**Still open.** The five skill reds above. Fleet re-link is not needed: no shipped file was
added or removed.

## 2026-09-25 — data-dict (tidyverse) trial: ruled DEFER

**Scope.** Assessed Hadley Wickham's `data-dict` (spec 0.1.0, CLI 0.0.3) as a checkable replacement for `data-engineer`'s prose codebook, under `docs/plans/2026-09-25-data-dict-trial.md`. The trial ran on scratch copies of five `zoning2026` raw inputs. **No shipped file changed; the paper repo was read only.**

**Findings** (`docs/audits/2026-09-25_data-dict-trial-findings.md`):
- The validator caught 6/6 planted faults and the 10 real known AK/MD BPS duplicates, with line-level messages and a good self-contained HTML report.
- It reads **Parquet only**, and `parquet:` globs are broken.
- The `datadict` R wrapper calls a subcommand the released binary lacks.
- `translate` to R covers `assert:` expressions only (no key, type or enum checks), and it silently passes an assertion on a type-changed column.
- Relationship cardinality isn't validated.

**Ruling: DEFER.** C1 (formats) fails and C3 (R translation) is partial. The re-test trigger is in the findings file: any two of CSV/data-frame source, working globs, wrapper and binary in sync, structural `translate`.

**Left installed:** the `datadict` R package plus the CLI binary (in the R user cache), and `nanoparquet`. Three upstream issue drafts are in the findings file, unfiled.
