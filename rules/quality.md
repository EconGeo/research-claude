# Quality: Scoring and Thresholds

## 1. Weights

The overall score that gates submission is a weighted aggregate of critic scores. The weights
live here and in `.claude/rules/registry.yaml`; `check_fork.sh` (`weights-sum`) fails if the two
disagree or if the non-conditional weights do not sum to 100. `python3 .claude/scripts/pipeline.py score`
computes it; nothing else does.

| Component | Weight | Scored by |
|---|---|---|
| literature | 10 | lit-critic |
| data | 10 | explorer-critic |
| strategy | 25 | strategist-critic |
| theory | 20 | theorist-critic — `CONDITIONAL`: counted only when a theory section exists and was scored; the total renormalises from 120 |
| code | 15 | coder-critic (latest score over coder and data-engineer work) |
| manuscript | 10 | writer-critic (latest **whole-manuscript** score; section scores from `/write` are recorded separately) |
| referees | 25 | mean of domain-referee and methods-referee (12.5 each) |
| replication | 5 | verifier (PASS = 100, FAIL = 0) |

**Renormalisation.** A component with no score is excluded and the remaining weights are scaled
to sum to 100. An applied paper with no theory section therefore scores over exactly 100.

**Score sources.** Each critic starts at 100 and deducts per its rubric in
`.claude/skills/review/config/scoring-rubrics.md`. Latest score per component counts.
`quality_reports/pipeline_state.json` is authoritative; the research journal entry is written
from it, never the other way round.

## 2. Thresholds

| Gate | Overall | Per component | Enforced by |
|---|---|---|---|
| Commit | ≥ 80 | — | `pipeline.py score --gate commit` |
| PR | ≥ 90 | — | `pipeline.py score --gate pr` |
| Submission | ≥ 95 | every scored component ≥ 80 | `pipeline.py score --gate submission`, called by `/submit final` |

No component below 80 at submission. A perfect literature review cannot compensate for broken
identification.

## 3. Severity

Retired 2026-09-08 (R-2). Critics carry their own rubrics; no caller supplies a phase severity.
Reversible if the driver ever supplies one. <!-- residue:historical -->
