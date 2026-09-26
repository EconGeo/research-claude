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
                                                       # invoke /strategize [question] [--yes if run carried it]
python3 .claude/scripts/pipeline.py post strategist
```
`/strategize` dispatches strategist, then strategist-critic (its Step 4), and records the
score itself: `state record-score strategy <score> --critic strategist-critic --deductions <total> --report
quality_reports/reviews/strategist-critic_<date>.md`.

## Approval-gate summary
the newest `quality_reports/strategy/<project>/strategy_memo_<YYYY-MM-DD_HHMM>.md` (all 5 required sections: Estimand,
Specification, Assumptions, Robustness Plan, Threats), `pseudo_code.md`,
`robustness_plan.md`, `falsification_tests.md`, the decision record, and the score.

## Escalation (strike 3, target: user)
"The critic finds <the identifying assumption> not defensible after 3 rounds — accept the
design with that limitation disclosed, or pivot to <alternative design>?"

Alternatives (rank 1 first; the driver offers these as the option gate, never invents its own):
1. Accept the design with the assumption's limitation disclosed in *Threats*.
2. Pivot to the design the strategist ranked second in `/strategize`'s option gate.
3. Pivot to the design ranked third.
4. Add the falsification test the critic says would make the assumption defensible, and re-run.
5. Return to `/discover data` for the variation the assumption needs.
