# Reference: submit

**Delegates to:** `/submit final [journal]`

**Creator:** none — this stage's registry agent, verifier, is infrastructure: it checks, it
does not create.
**Critic:** none — verifier has no paired critic; its escalation target is the user directly.
**Component recorded:** `replication`, by verifier (weight and threshold:
`.claude/rules/quality.md`).

`requires`: the **overall** score already ≥ 95 — verifier is the last gate, run only once
every other component is essentially done.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre verifier
                                                    # invoke /submit final [journal]
python3 .claude/scripts/pipeline.py post verifier
python3 .claude/scripts/pipeline.py score --gate submission
```
`/submit final` runs the comprehensive review if stale, the replication audit (dispatches
verifier; records `state record-score replication <score> --critic verifier --report
quality_reports/verification_report.md`), the AI-disclosure audit, then the score gate
itself.

## Approval-gate summary
`quality_reports/quality_gate_[date].md`, the AI-disclosure audit result, and — only on
PASS — the cover letter draft and submission checklist.

## Escalation (target: user)
"The verifier reports check <N> failing (<what>) — fix it and re-run `/submit audit`, or
disclose it as a known limitation in the cover letter?"
