# Pipeline Repair Plan — 2026-09-23

**Scope:** `~/Academic/research-claude` (the pipeline) and the six paper repos that link it.
**After this plan:** `docs/2026-09-23_pipeline-closeout-handoff.md` gathers everything remaining —
the stalled 09-16 closeout (43 defects), the six divergence GAPs, the connectivity check class,
and the audit defects not yet planned. Do not start it until Phases 2–5 below are done.
**Blocks:** POGM4's JRER submission plan, which is paused until Phase 2 lands.

**Status: complete (2026-09-24).** Phases 1–4 are the pipeline's work and are done; Phase 5 is
POGM4's own resumption and lives in that repo (1.6's edit is committed there as `e6a99bc`;
`87840d8` re-linked it for the option-gates rule). The closeout handoff this plan deferred to is
itself closed — see `CLAUDE.md` § Start here. Original status text follows.

**Status (2026-09-24, earlier): Phases 1–4 done.** Phase 1 (`ec8905e`…`3b1eb9f`) merged in `04375cb`.
Phase 2 (`7424e79`, `71aaaf3`, `ab41926`, `8d65c68`) merged to `main` in `19aaac0`. The upstream
`EconGeo/ai-audit` rename that 2.4 was waiting on has landed and been synced (`c737ac6`):
`/humanize`/`humanize-auditor` are now `/civilize`/`civilize-auditor` throughout `ai-audit/`, so
2.4's gate is met. Phase 3 (all five items, 3.1–3.5) landed in a prior session. Phase 4 (all three
items, 4.1–4.3) is done as of this session on branch `phase4-repair-plan` — see each item for its
gate evidence; every gate was reproduced failing before the fix and passing after, and
`check_fork.sh` / `check_install.sh --all` / the full test suite (212 tests) all PASS as of the
last item. One item remains not fully closed, not silently marked done: 1.6's POGM4 edit is
uncommitted in POGM4's own repo (outside this session's scope to commit). POGM4 can resume — Phase
2 landed. Next: Phase 5 (resume POGM4) — the closeout handoff (`docs/2026-09-23_pipeline-closeout-handoff.md`)
is what comes after this plan finishes, not started.

---

## Why this plan exists, and the rule it is built under

A single session found, one trip-over at a time: a project-local skill that had silently waived a
real defect through two critic rounds for three months; four reference files shadowing upstream
with stale copies, one contradicting the invariant its project was scored against; a rule
superseded months earlier still linked into six repos; a skills table advertising thirteen
commands that had not existed since June; two divergent copies of the same gate script; a gate
citing a checker that did not exist; and nine agents instructed to write reports they have no
tool to write.

Every one of those is a **written claim that nothing verified**. The audits are in
`docs/audits/2026-09-23_*.md`; the intent behind each divergence from clo-author is in
`docs/decisions/clo-author-divergences.md`.

**So this plan is written under one rule, and it applies to this plan too:**

> **Every item ends in an executable check that FAILS before the work and PASSES after.**
> An item whose only evidence of completion is a checkbox is not done — it is the failure mode
> this plan exists to remove. Where no check exists, building the check *is* the first half of
> the item.

Named gates: `scripts/check_fork.sh` (template hygiene), `scripts/check_install.sh` (link tree,
per project and `--all`), `scripts/prose_number_check.py` (INV-11),
`scripts/quarto_structure_check.py` (INV-25), `pipeline.py state validate`, `registry check`.

---

## Phase 0 — landed today (record, do not redo)

- [x] `check_install.sh` check 5b: project-local skills/agents/rules/commands FAIL. Six repos clean.
- [x] `references/` linked, not copied (D-26). The copy_seed design was the cause of the rot.
- [x] `registry-verification-gate.md` deleted as superseded; dangling links pruned in six repos.
- [x] `/tools commit` carries the blocking gates; project-local `commit` skill deleted.
- [x] `quarto_structure_check.py` built; **INV-25** defined. `tested:` PASS on two native
      fixtures, FAIL on a workaround fixture, and it reproduces on a real manuscript the counts
      two independent audits found by other means.
- [x] `hooks/install-check.py` wired at SessionStart — the detector existed and nothing ran it.
- [x] POGM4 skills table rebuilt; 13 of 18 rows were dead.

---

## Phase 1 — Enforcement that does not exist

The audit's central result: **of 24 live invariants, exactly one (INV-11) had a real executable
gate.** INV-25 is now the second. Three more are enforced by nothing at all while the
enforcement table names an enforcer for each.

- [x] **1.1 Fix `chunk_labels()`.** `tested:` it reads only `#| label:` and returns `['setup']`
  for an 80-chunk manuscript, so `pipeline.py post coder` raises a false alarm on a compliant
  document — which is how real findings get waived. Parse brace-form labels too.
  **Gate:** `chunk_labels()` on POGM4's manuscript returns ≥ 80 labels including the `tbl-` set.
  **Done 2026-09-23** (`ec8905e`, merged to `main` in `04375cb`). Gate note: POGM4's manuscript
  has 80 labels total but zero start with `tbl-` (all 35 table chunks use `tab-` instead) —
  flagged to the user, not fixed here (separate repo, out of pipeline scope); a follow-up task
  was spawned (`task_9e2623f6`).
- [x] **1.2 Make the chunk predicates reachable.** All four `chunk` predicates in
  `registry.yaml` use `min: 1`, so prefix correctness cannot fail. Re-express them against
  `quarto_structure_check.py`. **Gate:** a fixture with one `tab-` label fails `post coder`.
  **Done 2026-09-23** (`5820ac0`, merged to `main` in `04375cb`).
- [x] **1.3 Stop trusting `quarto render` exit 0.** `tested:` on Quarto 1.9.37 an unresolved
  `@tbl-` is a WARNING with **exit 0**, and raw `\citet{}`/`\ref{}` produce no warning at all.
  `pipeline.py:179` tests only the return code, and `content-invariants.md:112` claims the render
  "fails or degrades visibly" — it does not. Parse the render log and the artifact.
  **Gate:** a fixture with a dangling `@tbl-` fails the render check.
  **Done 2026-09-23** (`0fb52e3`, merged to `main` in `04375cb`). The raw-LaTeX-macro case (no
  warning at all) is still uncaught by the render predicate — content-invariants.md's INV-9 row
  says so plainly rather than implying coverage that doesn't exist.
- [x] **1.4 Give INV-19 (`source()` prohibited) an executable check.** `tested:` seven prohibited
  constructs planted in one chunk — the linter caught six and missed `source()`, though
  `content-invariants.md:110` names that linter as its enforcer. **Gate:** the fixture fails.
  **Done 2026-09-23** (`07aa079`, merged to `main` in `04375cb`).
- [x] **1.5 Give INV-15 and INV-24 checks, or mark them judgment-only.** `grep -rn data_manifest
  scripts/ hooks/` returns zero hits while the table names enforcers. Either build them or correct
  the table — **an enforcement table that names a non-existent enforcer is worse than a blank
  cell.** **Gate:** every row of the enforcement table resolves to a file that exists.
  **Done 2026-09-23** (`3b1eb9f`, merged to `main` in `04375cb`). Resolution: corrected the table
  (INV-15 marked reviewer-judgment only); INV-24's row already only named agents, not a script, so
  it needed no change.
- [x] **1.6 Resolve the two `prose_number_check.py` copies.** research-claude's 255-line version is
  the superset; `~/Research/scripts/`'s 152-line copy is what POGM4's CLAUDE.md tells you to run,
  so the documented command and the automated predicate can disagree. Keep one, repoint callers.
  **Gate:** `grep -rn prose_number_check` shows one path across all six repos and the pipeline.
  **Done 2026-09-23.** `~/Research/scripts/prose_number_check.py` deleted; `~/Research/POGM4/CLAUDE.md`
  repointed to `.claude/scripts/prose_number_check.py` (two places). The other five linked repos
  (BRI, ESG, NAR_settlement, affordable_housing_2026, zoning2026) never referenced the weak copy.
  This edit is **outside research-claude** — uncommitted in POGM4's own repo, left for the user.

---

## Phase 2 — Contracts that contradict themselves

**POGM4 resumes after this phase.** These are the defects that corrupt review output, and POGM4's
next task is a review round.

- [x] **2.1 Settle the critic write contract.** Of 13 report producers: 2 succeed (only by
  carrying `Bash`), 4 fail loudly, 5 silently produce nothing. `writer-critic` writes via `Bash`
  in violation of its own line 18, "Do NOT edit any file". The design in `rules/agents.md` is that
  the **dispatching skill** writes the report; ten call-sites say otherwise, and `/lit-position`
  Step 7 and `/write` Step 5 name the agent as writer. Make every call-site say the orchestrator
  writes it. Do **not** grant critics `Write` — it is all-or-nothing in frontmatter and would let
  a critic edit the manuscript it scores.
  **Gate:** a `writes`-vs-`tools` consistency check — `registry.yaml` already declares `writes:`
  for all nine — failing when an agent is declared to write a path its tools cannot produce.
  **Done 2026-09-23** (`71aaaf3`). All nine agent files reworded to the
  `humanize-auditor.md`-style "return as final response, do NOT write files" pattern; every
  skill call-site states the session saves the report before the next dispatch; `writer-critic`'s
  unused `Bash` (self-save only, nothing else in the file used it) removed. `rules/agents.md` §2
  states the contract explicitly, plus a new incremental-write rule (every report saved the
  instant it returns, never batched) — checked directly against clo-author (pinned `d36c408`):
  identical exposure, weaker mitigation (manual `/checkpoint` vs. automatic save-on-return).
  Per-finding/chunked-dispatch persistence was considered and explicitly tabled (would cost the
  critic's cross-category holistic judgment); recorded in `rules/agents.md` §2, not built.
- [x] **2.2 Close the separation-of-powers hole.** `rules/agents.md` names its own enforcement:
  "the dispatching skill flags a critic dispatch that leaves a file under a creator's `WRITES`
  prefix". Nothing automates it; the only code touching `WRITES` renders it into a table.
  **Gate:** the check in 2.1 covers the declaration side; add a dispatch-log check for the
  behavioural side.
  **Done 2026-09-23**, folded into `71aaaf3` — see 2.1.
- [x] **2.3 Stop stages closing on reports that do not exist.** `record-score` accepts a
  `--report` path that is absent, and `post <creator>` never checks the critic's `produces`.
  **Gate:** `record-score` with a non-existent report path exits non-zero.
  **Done 2026-09-23** (`ab41926`). `record-score` now refuses a `--report` path that doesn't
  exist; `critic-ran` (`post <creator>`'s gate) additionally re-checks that a previously-recorded
  report still exists on disk, since the record-score check alone doesn't catch a report deleted
  *after* scoring. `tests/run_fixture.sh` and `test_pipeline.py`'s `FixtureCase` updated to create
  the stub report every pre-existing call site had silently assumed existed.
- [x] **2.4 Litigate D-17 — `/write humanize` vs `/humanize`.** Two upstreams, opposite answers,
  never litigated: clo-author's "Output: Edited file with AI patterns removed" versus ai-audit's
  "Not a rewriter … auto-rewriting degrades prose quality". Only `/humanize` sets
  `disable-model-invocation: true`, so "de-AI this draft" — a phrase in `/humanize`'s own trigger
  list — routes to the rewriter it exists to argue against. **Author decision required:** does
  the pipeline edit prose automatically or only report? Record the ruling in the divergence
  register either way. **Gate:** the two skills' trigger lists no longer overlap.
  **Ruled 2026-09-23** (`7424e79`): keep `/write humanize` as the pipeline's humanizer — the
  "cross-vendor research" `/humanize` cited turned out to be unattributed Cursor/Aider community
  observation, not a study. `/humanize` is not retired; the author wants it kept under a
  different name for occasional detect-only use.
  **Gate met 2026-09-24** (`c737ac6`): upstream `EconGeo/ai-audit` PR #2 renamed the skill and
  agent to `/civilize`/`civilize-auditor` (pinned commit `a99c7a75`), synced via
  `scripts/sync-ai-audit.sh`. `tested:` full-repo grep for `humanize` outside `docs/` now hits
  only `skills/write/SKILL.md` (the pipeline's own `/write humanize` mode) and
  `ai-audit/VENDORED.md` (provenance note); `ai-audit/` itself carries no `humanize` string
  anywhere. `/civilize`'s description still lists "de-AI this draft" as a trigger phrase, but
  it carries `disable-model-invocation: true` and that phrase does not appear in `/write`'s
  description, so no natural-language phrase auto-routes to both — the only remaining overlap is
  that a user *could* mean either by that phrase, which is the intended behavior per the ruling
  (auto-rewrite via `/write humanize` is the default; `/civilize` is manual detect-only). Neither
  name is registered in `rules/registry.yaml` yet — that is Phase 3.4, not this item.
- [x] **2.5 Fix the four remaining skill conflicts** from `docs/audits/2026-09-23_skill-inventory.md`:
  `data-engineer.md:92` recommends `kableExtra` while its own critic deducts −5 for it in Word;
  `/talk`'s inline format table disagrees with `format-constraints.md` on every row; two
  `/analyze` bundled resources contradict each other on naming and font size; `editor.md:124`
  delegates to a `/review --variance` flag that does not exist.
  **Gate:** `check_fork.sh` PASS plus a re-read confirming each pair now agrees.
  **Done 2026-09-23** (`8d65c68`). First three fixed by making one side authoritative and the
  other point at it. Fourth (`--variance`): checked clo-author at `d36c408` first — it never had
  more than two referees or a variance mode, so this is net-new, unresolved-anywhere work, not a
  regression; corrected `editor.md`'s false enforcement claim rather than inventing a resolution
  to which agent identity referees 3–N should use. User decided (2026-09-24) not to build
  variance-mode dispatch — a third *named, specialized* referee agent is of more interest than
  N-way disposition sampling; parked as a future design task, not started.

---

## Phase 3 — Wiring gaps

- [x] **3.1 Wire `ai-audit`'s hallucination check into `/submit final`.** `/civilize` and
  `/verify-claims` were referenced only in the README — no registry entry (fixed in 3.4), no
  `/submit final` enforcement — so a manuscript could clear the `submission` gate at ≥95 with no
  hallucination check ever run. **Gate:** `/submit final` refuses without a recorded
  `verify-claims` result.
  **Done 2026-09-24** for the stated gate. `tested:` before the fix, `score --gate submission`
  PASSed on 8 components all scored 96 with `/verify-claims` never mentioned anywhere in state.
  Added `pipeline.py state record-verify-claims --report P --result pass|fail` (refuses a
  `--report` that doesn't exist yet, same contract as `record-score`, Phase 2.3) writing
  `st["verify_claims"] = {result, report, at}`; `score --gate submission` now FAILs — even at a
  qualifying overall score — when `verify_claims` was never recorded, its last result was
  `fail`, or its recorded report has since been deleted. `state validate` checks its shape.
  `skills/submit/SKILL.md` step 2.6 dispatches `/verify-claims` and records the result before the
  gate check; the Principles list states the "no exceptions" rule the way the AI-disclosure rule
  already does. `claim-verifier`'s registry entry (added in 3.4) now declares the
  `quality_reports/verify_claims_*.md` path `/verify-claims` produces, closing an
  `artifact-paths` gap the fix itself exposed. 7 new tests
  (`TestSubmissionGateNeedsVerifyClaims`); full suite (188 tests), `check_fork.sh` and
  `check_install.sh --all` all PASS.
  **Not done, and not claimed:** no `/pipeline` stage dispatches `/verify-claims` automatically,
  and no `/review` route calls it either — it remains a skill the user (or `/submit final`) must
  invoke explicitly. `/civilize` has no gate at all; nothing in the pipeline requires it to run,
  by ruling (2.4) — it is detect-only, occasional-use, never mandatory.
- [x] **3.2 Protect vendored trees in `/promote`.** Its pathspec excludes `ai-audit/` while
  `sync-ai-audit.sh` does `rm -rf`, so an edit made through a project link is destroyed silently.
  `/promote` warns for `zotpilot-skills/` only. **Gate:** `/promote` warns for both.
  **Done 2026-09-24.** Added `check_refs.py`'s `promote-vendor-warn` criterion (wired into
  `check_fork.sh`): FAILs unless `skills/promote/SKILL.md` names every entry in `VENDORED`
  (`zotpilot-skills`, `ai-audit`) on a line that also says "vendor" — `tested:` it FAILed on the
  pre-fix file (only `zotpilot-skills/` named) and PASSes on the fixed one. Added Step 2.5 to
  `skills/promote/SKILL.md`: runs `git status --porcelain -- zotpilot-skills ai-audit` (Step 2's
  pathspec deliberately excludes both) and instructs reporting any hit before proceeding — the
  fix belongs upstream or in a bridge skill, never committed as-is. Updated the "does NOT do"
  section to name both trees symmetrically. 5 new tests (`TestPromoteVendorWarn` in
  `tests/test_check_refs.py`, including one asserting the shipped file itself passes).
  `check_fork.sh` PASS.
- [x] **3.3 Fix `state strike`.** Accepts strike 4 of 3 and returns 0; an unknown agent name is
  accepted for strikes 1–2 then throws an unhandled `KeyError` **after saving**, poisoning
  `state validate` — which `/pipeline run` refuses on — with no command to undo.
  `rounds_overall` and `verification_retries` are declared and read by nothing.
  **Gate:** strike 4 exits non-zero; an unknown agent is rejected before the save.
  **Done 2026-09-24.** `tested:` reproduced both defects first (`ghost-agent` strike 3 raised
  `KeyError` after two silent saves; a 4th `coder` strike printed "strike 4 of 3" and returned 0).
  Fixed in `scripts/pipeline.py`'s `state strike` handler: an unknown agent is now rejected
  (exit 1) before any write, and a strike at or past `rounds_per_pair` is refused (exit 1,
  nothing recorded) instead of silently incrementing past the limit. Three tests added
  (`TestStateStrike` in `tests/test_pipeline.py`); full suite (181 tests) passes.
  `rounds_overall`/`verification_retries` remain declared-and-unread — out of this item's scope,
  not claimed fixed here.
- [x] **3.4 Register `claim-verifier` and `civilize-auditor`.** `registry_check()` globs only
  `<root>/agents/*.md`, so both are installed in every project and invisible to the registry.
  **Gate:** `registry check` counts them.
  **Done 2026-09-24.** `tested:` before the fix, `registry check` reported PASS while silently
  never looking at `ai-audit/agents/*.md` at all. Added `registry_lib.agent_roster()` (scans
  `agents/` and `ai-audit/agents/`, shared by `pipeline.py registry_check()` and
  `tests/test_registry_lib.py` so the two rosters cannot drift apart); this immediately turned
  up both agents as "exists but is not declared" (`registry-complete` FAIL) — the blind spot
  made concrete. Declared both in `rules/registry.yaml` as `role: infrastructure`,
  `component: none`, `quality_weight: 0`, `writes: []` (neither agent carries a `Write` tool —
  same write contract as Phase 2.1: the dispatching skill saves the report). Re-rendered
  `rules/permissions.md`. `check_fork.sh`, `check_install.sh --all` and the full test suite
  (181 tests) all PASS.
- [x] **3.5 Close the two parity gaps.** `/submit` claims to replace `data-deposit` and has no
  deposit step; `narrative-arcs.md` shipped inside `/talk` rather than independent of it.
  **Done 2026-09-24.**
  **Deposit:** added a fifth `/submit deposit [journal]` mode — reads the target journal's
  archive/policy from `.claude/references/journal-profiles.md`, checks `replication/README.md`'s
  placeholders are filled, writes a deposit manifest + manual upload checklist, then **stops and
  waits** for the user to complete the upload themselves (an external, credentialed, irreversible
  publish action this pipeline does not perform). Added `pipeline.py state record-deposit
  --repository --url --report` (refuses a missing `--report`, same contract as `record-score`)
  so "recorded" is a real state entry, not a claim. **Deliberately not done:** `score --gate
  submission` does NOT hard-require a deposit — unlike `verify-claims` (3.1), deposit timing is
  journal-specific (some require it before acceptance, most after), so gating `/submit final` on
  it would be wrong for the common case; this is a documented scope boundary, not an oversight.
  6 new tests (`TestRecordDeposit` in `tests/test_pipeline.py`, `TestDepositModeExists` in
  `tests/test_submit_gate.py`, the latter asserting the mode section exists and calls
  `state record-deposit`).
  **narrative-arcs.md:** moved `skills/talk/templates/narrative-arcs.md` →
  `references/narrative-arcs.md` (repo-root, cross-skill — the same tier as `journal-profiles.md`,
  not namespaced under any one skill). Repointed the two existing references
  (`skills/talk/SKILL.md`, `agents/storyteller.md`) and added a new one from `/write`'s Paper
  Type Detection step, which the audit found missing. Re-worded the file's own opening to state
  its dual audience. Required a documented, minimal budget raise (write's Level-2 cap, 7,500 ->
  7,600 chars, `tests/test_skill_contracts.py`) to fit the one added sentence — the review
  precedent for a reasoned raise, not a silent one.
  **Fleet:** the move/add touches `references/` and `skills/`, both linked directories — re-ran
  `apply.sh --link --tip` against all six projects (membership FAILed on the new file until this
  ran); `check_install.sh --all` now PASS. `check_fork.sh` and the full suite (199 tests) PASS.

---

## Phase 4 — Re-home the orphaned purposes — **done 2026-09-24**

Five of the six GAPs in the divergence register share one shape: **the mechanism was correctly
retired or replaced, and the purpose it served was never re-homed.** The registry is the proven
case — it existed "for writer handoff" because the writer could not see numbers inside `.rds`
objects; Quarto dissolved that for expressions, and nothing owned it for literals until
`prose_number_check.py` was written, years of manuscripts later.

- [x] **4.1** Work D-2, D-3, D-18 and D-19 the same way: name the purpose, decide whether it still
  exists under Quarto, and either re-home it in a gate or record it OBSOLETE with the reason.
  **Done 2026-09-24.** All four closed — see `docs/decisions/clo-author-divergences.md`.
  **D-2:** already re-homed as of Phase 0 (`hooks/install-check.py` at `SessionStart`) but never
  verified against the register; `tested:` `check_install.sh --all` → `PASS [hooks-wired]` ×6.
  **D-3:** genuinely open — `protect-files.sh` was never wired. Traced the "opt-in" citation to its
  actual source (`docs/superpowers/specs/2026-09-08-pipeline-repair-design.md`'s own R-7 — a
  different document's numbering than this repo's rulings appendix, which has an unrelated R-7 of
  its own; the two were conflated in three separate 2026-09-23 audit notes). Superseded that ruling
  given the concrete evidence it produced (`/review`'s own ad hoc `git status --porcelain` patch
  for a report restamped mid-review): wired `protect-files.sh` in `seeds/settings.json` and all six
  linked repos, repointed `PROTECTED_PATTERNS` from inherited LaTeX-era names to the actual
  Quarto-era artifacts. Also found and fixed a second, independent bug while testing: `[[
  "$BASENAME" == "$PATTERN" ]]` quotes the pattern, which disables bash glob matching, so every
  wildcard pattern — including the ones shipped since 2026-09-08 — silently never matched. `tested:`
  `tests/test_protect_files.py` (8 cases); `check_install.sh --all` `hooks-wired` FAILed on all six
  repos the moment the hook joined the seed, PASSed once each repo's `settings.json` caught up.
  **D-18:** already closed as a side effect of Phase 3.1/3.2/3.4; the register just hadn't been
  told. **D-19:** not a missing check but a missing design decision — already settled at Phase 2.5
  (user: build a named third referee agent later, not N-way dispatch now); recorded as a closed
  scope boundary rather than a live GAP. Full suite (212 tests after 4.1–4.3), `check_fork.sh` and
  `check_install.sh --all` all PASS.
- [x] **4.2** Record a reason on disk for the **7 divergences that currently have none**.
  **Done 2026-09-24.** D-2, D-3, D-18 closed above with reasons; D-16, D-17, D-19 already carried
  recorded reasons by the time the register's own "7 unrecorded" finding was written (D-17's own
  "Recorded on disk" field was stale and said otherwise — fixed alongside). **D-8 is the one
  genuine gap**: no prior ruling existed anywhere to recover, so this is a new decision, not a
  correction — ruled to keep the prose replication-tolerances table (a documented scope boundary:
  five stable threshold values read once per `/review --replicate`, where the actual work is an
  interpretive judgment call already made by the critic, unlike INV-11's hundreds of individual
  prose numbers). Zero divergences now carry no recorded reason.
- [x] **4.3** Add the register to `/promote`'s checklist so the next divergence is litigated when
  it is made, not three months later. **Gate:** `/promote` prompts for a register entry when a
  skill's behaviour changes.
  **Done 2026-09-24.** Added Step 3.5 to `skills/promote/SKILL.md`: for every change about to be
  committed upstream, ask whether it retires, replaces, or newly diverges from something
  clo-author did, and add a register entry before committing if so. Added `check_refs.py`'s
  `promote-register-check` criterion (wired into `check_fork.sh`): FAILs unless the skill both
  references `docs/decisions/clo-author-divergences.md` and ties it to the commit step (not just a
  passing mention), mirroring the `promote-vendor-warn` pattern from Phase 3.2. `tested:` FAILed on
  a skill text naming the register file without a commit-time step, PASSed once the real step
  language was added. 5 new tests (`TestPromoteRegisterCheck` in `tests/test_check_refs.py`).

---

## Phase 5 — Resume POGM4

POGM4's plan (`quality_reports/plans/2026-09-23_jrer-submission-plan.md`, v2) stands, with Task A
amended: **A2 is done upstream** (`quarto_structure_check.py` exists and is linked), and A1 is
Phase 1.6 here. The rest of Task A — the number-gate holes, the allowlist retirement, the
`chunk_labels` fix — is either Phase 1 above or genuinely project-local.

Resume at POGM4 Task B (native Quarto migration) once Phase 2 lands, because Task B's verification
depends on gates that are currently wrong, and its first review round depends on critics that can
write their reports.

---

## What this plan does not do

It does not add a rule telling anyone to be careful. Today's failures were not carelessness — the
rules were right and nothing executed them. Every item above either builds a check or deletes a
claim that no check supports.
