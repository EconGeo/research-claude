# Reference: data

**Delegates to:** `/discover data [requirements]`

**Creator:** explorer (kind: agent — `.claude/agents/explorer.md`).
**Critic:** explorer-critic (kind: agent — `.claude/agents/explorer-critic.md`).
**Component recorded:** `data` (weight and threshold: `.claude/rules/quality.md`).

`requires: []` — nothing gates this stage; it can run in parallel with literature.

## Driver sequence
```
python3 .claude/scripts/pipeline.py pre explorer          # trivially passes (no REQUIRES)
                                                             # invoke /discover data [requirements] [--yes if run carried it]
python3 .claude/scripts/pipeline.py post explorer
```
`/discover data` dispatches explorer, then explorer-critic (its Step 6), and records the
score itself: `state record-score data <score> --critic explorer-critic --deductions <total> --report
quality_reports/reviews/explorer-critic_<date>.md`.

## Approval-gate summary
`quality_reports/data-assessment/<project>/data_sources.md` (the file `strategist.requires`
keys on), `data_dictionary.md`, `access_instructions.md`, the feasibility grades (A–D), the
rejection table, and the explorer-critic score.

## Escalation (strike 3, target: user)
"The critic rejects every candidate on identification compatibility — accept a lower
feasibility grade for <dataset>, or does the research question need to change?"

Alternatives (rank 1 first; the driver offers these as the option gate, never invents its own):
1. Accept the lower feasibility grade for the best-fitting dataset and disclose the limitation.
2. Apply for the restricted version the critic's compatibility check would pass.
3. Switch to a proxy dataset that measures the outcome less directly but covers the variation.
4. Narrow the geography or period to where a public dataset is compatible.
5. Change the unit of observation to one the data support, and redesign around it.
