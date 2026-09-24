# Review Skill -- Gotchas

Known failure points and edge cases for paper/code/strategy review.

- Editor's desk review may desk-reject incomplete drafts -- specify submission stage explicitly if the paper is early-stage.
- Early-stopping in causal audit: Phase 2 critical issues override Phases 3-4 checks. This is by design -- fatal identification flaws make downstream checks moot.
- Peer review dispositions are assigned by the editor, not random -- user can influence by specifying journal culture in the request.
- Advisory scoring for talks means low scores don't block pipeline progression.
- Cold-read protocol means critics don't see prior rounds -- they may flag the same issue differently across rounds. This is a feature, not a bug.
- Code review checks both the script AND its output. A script that runs clean but produces wrong numbers still fails.
- Writer-critic format deductions come from `.claude/rules/quarto-pdf.md` / `quarto-word.md` and are required (blocking), not advisory. Architecture deductions (caching, inline numbers, `source()`) come from `quarto-empirical.md` and belong to the coder-critic — do not double-count them.
- Voice fidelity (writer-critic category 7) is only scored when `.claude/references/personal-style-guide.md` has real content. If the style guide is still a template, skip and report.
- The strategist-critic classifies each issue CRITICAL/MAJOR/MINOR, and each severity carries a fixed deduction (`.claude/skills/review/config/scoring-rubrics.md`, Strategist-Critic). Until 2026-09-14 the rubric had no point values and critics invented their own weightings, so a `strategy` score recorded before then is not comparable with one recorded after.
- Theorist-critic should not lecture authors on their own methods. Check `.claude/references/domain-profile.md` for the paper's authors before flagging textbook issues.
- Explorer-critic flags concerns but does NOT suggest specific alternative datasets (separation of powers).
- R&R second round reloads same referee dispositions and pet peeves from round 1. Max 3 rounds total.
- The editor is NOT a third referee -- they synthesize and decide, not add new substantive criticisms.
- When reviewing structural papers, don't penalize for missing parallel trends. When reviewing descriptive papers, don't penalize for missing identification. Paper-type awareness is mandatory for all critics.
- The Explorer's own task spec (`.claude/skills/discover/templates/data-assessment.md`) uses a 5-point critique, but the explorer-critic actually scores against 6 categories (`.claude/skills/review/templates/data-review-6-categories.md`) -- they don't map 1:1. Use the template's full 6, not the spec's 5.
- Save each report the moment its critic returns, and record that score then — not after all three. Critics are read-only, returning reports as text for the session to write; a session that dies before the last critic finishes loses every report not yet on disk (observed: strategist-critic done, report unsaved, run lost).
- Check the tree around the verifier: `git status --porcelain` before dispatching it and again when it returns. Put every tracked path that changed — other than the manuscript's rendered outputs — in front of the user, keep it out of any commit of the scores, and do not revert it unasked. The verifier is told not to run a project's own gate scripts; this check is what notices when one did anyway (observed: a project gate restamped two committed reports).
- `--stress` records no `referees` score: stress mode returns a concern-list gauntlet, not an `editorial_decision.md`, so there is nothing for `record-score` to read from. Deliberate (R-106 class), like `--replicate`.
- `--variance N` is specified in `.claude/agents/editor.md` and deliberately not wired into `/review` (D-19, 2026-09-24). Refuse the flag; do not dispatch N referees by hand.
