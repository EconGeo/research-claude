# Reference: strategy

**Delegates to:** `/strategize [question]` (default/`strategy` mode)

**Creator:** strategist (kind: agent — `.claude/agents/strategist.md`).
**Critic:** strategist-critic (kind: agent — `.claude/agents/strategist-critic.md`).
**Component recorded:** `strategy` (weight and threshold: `.claude/rules/quality.md`).

`requires`: `positioning.md` **or** `data_sources.md` must exist (either producer is enough),
and — only if it was ever scored — `literature` and `data` must each be ≥ 80.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre strategist
                                                       # invoke /strategize [question]
python3 .claude/scripts/pipeline.py post strategist
```
`/strategize` dispatches strategist, then strategist-critic (its Step 4), and records the
score itself: `state record-score strategy <score> --critic strategist-critic --report
quality_reports/reviews/strategist-critic_<date>.md`.

## Approval-gate summary
`quality_reports/strategy/<project>/strategy_memo.md` (all 5 required sections: Estimand,
Specification, Assumptions, Robustness Plan, Threats), `pseudo_code.md`,
`robustness_plan.md`, `falsification_tests.md`, the decision record, and the score.

## Escalation (strike 3, target: user)
"The critic finds <the identifying assumption> not defensible after 3 rounds — accept the
design with that limitation disclosed, or pivot to <alternative design>?"
