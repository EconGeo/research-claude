---
date: 2026-09-08
branch: design/quarto-native-pipeline
plan: (none yet — design spec approved, implementation plan not written)
spec: docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md
session-log: (none on disk — research-claude uses docs/SESSION_REPORT.md)
status: in_progress
---

# Checkpoint — Quarto-native pipeline fork

## Goal
Fork research-claude off the `hugosantanna/clo-author` submodule and make it a standalone
Quarto-native research pipeline, cherry-picking clo-author's good ideas and rewriting the
format-bound ones instead of translating them via `pipeline-precedence.md`.

## Where I am
Design phase complete and approved. Ran a full audit of the installed pipeline (47
clo-author files measured for LaTeX coupling; every capability checked for artifact-level
evidence of use across `~/Research/*`). Design spec written, self-reviewed, committed on a
new branch. **No implementation has started — nothing outside `docs/` has been touched, and
no project under `~/Research/` was modified.**

## File pointers
- `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` — the spec; start here
- `:129` (Work items A) — agent harvest table, incl. the coder-critic merge
- `:150` (B) — 8 dormant capabilities to port
- `:170` (D) — 4 standards files to rewrite, not translate
- `:196` — 9 mechanically-checkable success criteria
- `:214` — 3 open items deferred to the implementation plan
- `apply.sh:174-210` — the clo-author copy block that gets replaced
- `rules/pipeline-precedence.md` — to be deleted

## Recent decisions
- **Diagnosis was reframed.** The critics are *not* LaTeX-coupled (0–6%; ten measure 0%). The
  real problems are a dead one-way submodule (pinned 2026-05-10), stranded value, and four
  standards files giving agents wrong instructions that `pipeline-precedence.md` doesn't cover.
- **Orchestrator cut, pairing kept.** It was structurally unreachable — only `/new-project`
  dispatches it and `apply.sh` refuses to install `/new-project`. Its phase graph also
  serializes the coder↔writer looping the research journal shows actually happens.
- **librarian folds into a ZotPilot *bridge* skill**, not an edit to `zotpilot-skills/` —
  those are vendored, and editing them in place would recreate the drift we're escaping.
- **De-projectification is cheaper than feared** — one leaked token (`manuscript_quarto_word`
  in coder-critic) across eight harvest candidates; `editor.md` is fully generic.
- Two errors self-corrected during the session: `domain-referee` is 137 lines in POGM4, not
  351 (I had extrapolated from a diff-line count), and `writer-critic` is 62 lines, not ~100.

## Open questions
- **Q1** Re-apply to POGM4 in place, or verify on a scratch copy first? (Criterion 4 assumes scratch.)
- **Q2** How do future project improvements get promoted back — a `/promote` skill, or a README checklist?
- **Q3** Rollout order for `zoning2026`, `ESG`, `BRI`, `affordable_housing_2026`? All carry the
  same clo-author baseline and the same four wrong standards files; only POGM4 has been patched around.

## Next 1–3 actions
1. Review the spec; answer Q1–Q3 (or defer them into the plan).
2. Invoke `superpowers:writing-plans` to turn the spec into a file-by-file implementation plan.
3. Execute in dependency order: vendor+harvest agents → rewrite D-list → port B-list → rewrite `apply.sh` → delete submodule + `pipeline-precedence.md` → verify against a scratch POGM4.

## Resume prompt
> Resuming from checkpoint `docs/checkpoints/2026-09-08_quarto-native-pipeline-fork.md`. Read it and the spec it points to, then continue with action 1.
