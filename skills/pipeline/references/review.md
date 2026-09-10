# Reference: review

**Delegates to:** `/review --all`

No new creator is dispatched here — this stage re-validates artifacts strategist, writer and
coder already produced. It re-runs three critics **in parallel**:
- strategist-critic → re-scores `strategy`
- writer-critic → re-scores `manuscript`
- verifier → re-scores `replication` (render + prose check; PASS=100, FAIL=0)

There is no registry agent named `review`, so the driver does not call `pipeline.py pre/post
review` — it checks the three components' freshness via `pipeline.py score` instead.

## Driver sequence
```
                                # invoke /review --all
python3 .claude/scripts/pipeline.py state record-score strategy <score> --critic strategist-critic --report <path>
python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --report <path>
python3 .claude/scripts/pipeline.py state record-score replication <score> --critic verifier --report quality_reports/verification_report.md
python3 .claude/scripts/pipeline.py score
```

## Approval-gate summary
The weighted aggregate from `pipeline.py score`, and each of the three reports'
paths — `quality_reports/reviews/strategist-critic_<date>.md`,
`quality_reports/reviews/writer-critic_<date>.md`, `quality_reports/verification_report.md`.

## Escalation
No new strike counter here. A low score sends the work back to its own creator's stage
(`strategy` → `/strategize`, `manuscript` → `/write`, `replication` → `/analyze`), which
carries that creator's own escalation target and question template.
