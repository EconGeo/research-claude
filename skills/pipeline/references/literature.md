# Reference: literature

**Delegates to:** `/lit-position [research question or topic]`

**Creator:** lit-position (kind: skill — runs in the main thread, not an Agent dispatch; it
calls `/ztp-research` and `/ztp-review` itself).
**Critic:** lit-critic (kind: agent — `.claude/agents/lit-critic.md`).
**Component recorded:** `literature` (weight and threshold: `.claude/rules/quality.md`).

`requires: []` — nothing gates this stage; it can run first.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre lit-position          # trivially passes (no REQUIRES)
                                                                 # invoke /lit-position
python3 .claude/scripts/pipeline.py post lit-position
```
`/lit-position` (Step 7 of its own SKILL.md) dispatches lit-critic itself and records the
score itself: `state record-score literature <score> --critic lit-critic --report <path>`.
Standalone runs additionally call `pipeline.py log lit-position` there, since nothing else
would log a skill that never went through the Agent tool; orchestrated runs still need that
log entry for `post`'s `critic-ran` check, so confirm it happened before trusting `post`.

## Approval-gate summary
`quality_reports/literature/<project>/annotated_bibliography.md`, `frontier_map.md`,
`positioning.md`, the lit-critic score, and any scooping risks flagged in Step 1.

## Escalation (strike 3, target: user)
"The critic requires coverage of X, which the library lacks and external search did not
find — narrow the claim or extend the search?"
