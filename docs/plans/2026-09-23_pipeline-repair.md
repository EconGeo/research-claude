# Pipeline Repair Plan — 2026-09-23

**Scope:** `~/Academic/research-claude` (the pipeline) and the six paper repos that link it.
**Blocks:** POGM4's JRER submission plan, which is paused until Phase 2 lands.

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

- [ ] **1.1 Fix `chunk_labels()`.** `tested:` it reads only `#| label:` and returns `['setup']`
  for an 80-chunk manuscript, so `pipeline.py post coder` raises a false alarm on a compliant
  document — which is how real findings get waived. Parse brace-form labels too.
  **Gate:** `chunk_labels()` on POGM4's manuscript returns ≥ 80 labels including the `tbl-` set.
- [ ] **1.2 Make the chunk predicates reachable.** All four `chunk` predicates in
  `registry.yaml` use `min: 1`, so prefix correctness cannot fail. Re-express them against
  `quarto_structure_check.py`. **Gate:** a fixture with one `tab-` label fails `post coder`.
- [ ] **1.3 Stop trusting `quarto render` exit 0.** `tested:` on Quarto 1.9.37 an unresolved
  `@tbl-` is a WARNING with **exit 0**, and raw `\citet{}`/`\ref{}` produce no warning at all.
  `pipeline.py:179` tests only the return code, and `content-invariants.md:112` claims the render
  "fails or degrades visibly" — it does not. Parse the render log and the artifact.
  **Gate:** a fixture with a dangling `@tbl-` fails the render check.
- [ ] **1.4 Give INV-19 (`source()` prohibited) an executable check.** `tested:` seven prohibited
  constructs planted in one chunk — the linter caught six and missed `source()`, though
  `content-invariants.md:110` names that linter as its enforcer. **Gate:** the fixture fails.
- [ ] **1.5 Give INV-15 and INV-24 checks, or mark them judgment-only.** `grep -rn data_manifest
  scripts/ hooks/` returns zero hits while the table names enforcers. Either build them or correct
  the table — **an enforcement table that names a non-existent enforcer is worse than a blank
  cell.** **Gate:** every row of the enforcement table resolves to a file that exists.
- [ ] **1.6 Resolve the two `prose_number_check.py` copies.** research-claude's 255-line version is
  the superset; `~/Research/scripts/`'s 152-line copy is what POGM4's CLAUDE.md tells you to run,
  so the documented command and the automated predicate can disagree. Keep one, repoint callers.
  **Gate:** `grep -rn prose_number_check` shows one path across all six repos and the pipeline.

---

## Phase 2 — Contracts that contradict themselves

**POGM4 resumes after this phase.** These are the defects that corrupt review output, and POGM4's
next task is a review round.

- [ ] **2.1 Settle the critic write contract.** Of 13 report producers: 2 succeed (only by
  carrying `Bash`), 4 fail loudly, 5 silently produce nothing. `writer-critic` writes via `Bash`
  in violation of its own line 18, "Do NOT edit any file". The design in `rules/agents.md` is that
  the **dispatching skill** writes the report; ten call-sites say otherwise, and `/lit-position`
  Step 7 and `/write` Step 5 name the agent as writer. Make every call-site say the orchestrator
  writes it. Do **not** grant critics `Write` — it is all-or-nothing in frontmatter and would let
  a critic edit the manuscript it scores.
  **Gate:** a `writes`-vs-`tools` consistency check — `registry.yaml` already declares `writes:`
  for all nine — failing when an agent is declared to write a path its tools cannot produce.
- [ ] **2.2 Close the separation-of-powers hole.** `rules/agents.md` names its own enforcement:
  "the dispatching skill flags a critic dispatch that leaves a file under a creator's `WRITES`
  prefix". Nothing automates it; the only code touching `WRITES` renders it into a table.
  **Gate:** the check in 2.1 covers the declaration side; add a dispatch-log check for the
  behavioural side.
- [ ] **2.3 Stop stages closing on reports that do not exist.** `record-score` accepts a
  `--report` path that is absent, and `post <creator>` never checks the critic's `produces`.
  **Gate:** `record-score` with a non-existent report path exits non-zero.
- [ ] **2.4 Litigate D-17 — `/write humanize` vs `/humanize`.** Two upstreams, opposite answers,
  never litigated: clo-author's "Output: Edited file with AI patterns removed" versus ai-audit's
  "Not a rewriter … auto-rewriting degrades prose quality". Only `/humanize` sets
  `disable-model-invocation: true`, so "de-AI this draft" — a phrase in `/humanize`'s own trigger
  list — routes to the rewriter it exists to argue against. **Author decision required:** does
  the pipeline edit prose automatically or only report? Record the ruling in the divergence
  register either way. **Gate:** the two skills' trigger lists no longer overlap.
- [ ] **2.5 Fix the four remaining skill conflicts** from `docs/audits/2026-09-23_skill-inventory.md`:
  `data-engineer.md:92` recommends `kableExtra` while its own critic deducts −5 for it in Word;
  `/talk`'s inline format table disagrees with `format-constraints.md` on every row; two
  `/analyze` bundled resources contradict each other on naming and font size; `editor.md:124`
  delegates to a `/review --variance` flag that does not exist.
  **Gate:** `check_fork.sh` PASS plus a re-read confirming each pair now agrees.

---

## Phase 3 — Wiring gaps

- [ ] **3.1 Wire `ai-audit`.** `/humanize` and `/verify-claims` are referenced only in the README —
  no registry entry, no `/pipeline` stage, no `/review` route — so `/submit final` can pass at ≥95
  with no hallucination check ever run. **Gate:** `/submit final` refuses without a recorded
  `verify-claims` result.
- [ ] **3.2 Protect vendored trees in `/promote`.** Its pathspec excludes `ai-audit/` while
  `sync-ai-audit.sh` does `rm -rf`, so an edit made through a project link is destroyed silently.
  `/promote` warns for `zotpilot-skills/` only. **Gate:** `/promote` warns for both.
- [ ] **3.3 Fix `state strike`.** Accepts strike 4 of 3 and returns 0; an unknown agent name is
  accepted for strikes 1–2 then throws an unhandled `KeyError` **after saving**, poisoning
  `state validate` — which `/pipeline run` refuses on — with no command to undo.
  `rounds_overall` and `verification_retries` are declared and read by nothing.
  **Gate:** strike 4 exits non-zero; an unknown agent is rejected before the save.
- [ ] **3.4 Register `claim-verifier` and `humanize-auditor`.** `registry_check()` globs only
  `<root>/agents/*.md`, so both are installed in every project and invisible to the registry.
  **Gate:** `registry check` counts them.
- [ ] **3.5 Close the two parity gaps.** `/submit` claims to replace `data-deposit` and has no
  deposit step; `narrative-arcs.md` shipped inside `/talk` rather than independent of it.

---

## Phase 4 — Re-home the orphaned purposes

Five of the six GAPs in the divergence register share one shape: **the mechanism was correctly
retired or replaced, and the purpose it served was never re-homed.** The registry is the proven
case — it existed "for writer handoff" because the writer could not see numbers inside `.rds`
objects; Quarto dissolved that for expressions, and nothing owned it for literals until
`prose_number_check.py` was written, years of manuscripts later.

- [ ] **4.1** Work D-2, D-3, D-18 and D-19 the same way: name the purpose, decide whether it still
  exists under Quarto, and either re-home it in a gate or record it OBSOLETE with the reason.
- [ ] **4.2** Record a reason on disk for the **7 divergences that currently have none**.
- [ ] **4.3** Add the register to `/promote`'s checklist so the next divergence is litigated when
  it is made, not three months later. **Gate:** `/promote` prompts for a register entry when a
  skill's behaviour changes.

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
