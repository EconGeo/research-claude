# Reference: write

**Delegates to:** `/write full`

**Creator:** writer (kind: agent — `.claude/agents/writer.md`).
**Critic:** writer-critic (kind: agent — `.claude/agents/writer-critic.md`).
**Component recorded:** `manuscript` — the latest **whole-manuscript** score; `/write`'s
per-section scores during drafting are recorded with `--scope section:<name>` and do not
overwrite it (weight and threshold: `.claude/rules/quality.md`).

`requires`: `code` score ≥ 80, at least one `tbl-*` chunk, and a clean render.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre writer
                                                   # invoke /write full
python3 .claude/scripts/pipeline.py post writer
```
`/write full` walks GATE 1–3, dispatching writer then writer-critic after each section
(Step 5), recording `state record-score manuscript <score> --critic writer-critic --report
<path> --scope section:<name>` per section. `post writer` needs a whole-manuscript score, not
just section scores (`.claude/rules/lifecycle.md`) — run a final `/write full` pass (or
`/review --proofread`) to close it if only sections were scored.

## Approval-gate summary
Each GATE's drafted section(s), the writer-critic score, the Claim–Evidence Table
(`quality_reports/reviews/claim_evidence_<project>_<date>.md`), and BLOCKED/VERIFY/VOICE
flags.

## Escalation (strike 3, target: user)
"writer-critic flags <a claim with no supporting estimate in the Claim–Evidence Table> after
3 rounds — soften the claim, or does the analysis need to produce the missing evidence?"
