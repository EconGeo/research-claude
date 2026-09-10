# Reference: theory (conditional)

**Delegates to:** `/strategize theory [target]`

**Creator:** theorist (kind: agent — `.claude/agents/theorist.md`).
**Critic:** theorist-critic (kind: agent — `.claude/agents/theorist-critic.md`).
**Component recorded:** `theory`, conditional — counted only when a `# Theory` heading
exists in the manuscript and the component was scored (weight and threshold:
`.claude/rules/quality.md`).

`requires`: `strategy` score ≥ 80. Skip this stage entirely for an applied paper using an
off-the-shelf estimator — the strategy memo is sufficient (see `/strategize` SKILL.md).

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre theorist
                                                    # invoke /strategize theory [target]
python3 .claude/scripts/pipeline.py post theorist
```
`/strategize theory` dispatches theorist, then theorist-critic (its Step 4), and records the
score itself: `state record-score theory <score> --critic theorist-critic --report
quality_reports/reviews/theorist-critic_<date>.md`.

## Approval-gate summary
The `# Theory` section and proofs appendix written into the manuscript,
`quality_reports/theory/[topic]/theory_memo.md`, `notation_glossary.md`, the decision
record, and the score.

## Escalation (strike 3, target: user)
"The critic finds <the proof step or assumption> unresolved after 3 rounds — accept it with
the caveat stated in the manuscript, or is the theoretical claim not supportable as posed?"
