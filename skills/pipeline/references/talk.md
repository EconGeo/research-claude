# Reference: talk (parallel, advisory)

**Delegates to:** `/talk create [format]`

**Creator:** storyteller (kind: agent — `.claude/agents/storyteller.md`).
**Critic:** storyteller-critic (kind: agent — `.claude/agents/storyteller-critic.md`).
**Component recorded:** none — talk scores are advisory and never gate a commit, PR or
submission (registry: `component: none`).

`requires`: `manuscript` score ≥ 80. Can run any time after `write` closes; never blocks the
`submit` path and is not part of the `--until` sequence unless named explicitly.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre storyteller
                                                       # invoke /talk create [format]
python3 .claude/scripts/pipeline.py post storyteller
```
Because the component is `none`, `post`'s `critic-ran` check only needs the dispatch log
(storyteller-critic completing after storyteller) — no score is ever recorded for this
component, so `state record-score` is not called here.

## Approval-gate summary
Generated `talks/[format]_talk.qmd`, slide count and format compliance, the
storyteller-critic score (advisory), and TODO items (missing figures/tables).

## Escalation (strike 3, target: writer — not user)
"storyteller-critic flags <a claim not traceable to the paper> after 3 rounds — does the
manuscript need a result to support this slide, or should the slide be cut?"
