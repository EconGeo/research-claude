# Drafting Gates — Approval Checkpoints

Draft sections in this order, pausing for user approval at each gate. Every gate ends with the
writer-critic's score recorded (`pipeline.py state record-score manuscript <score> --scope section:<name>`).

## GATE 1: Introduction + Literature Positioning
Present. Wait. User may redirect framing, contribution, literature emphasis.

## GATE 2: Data + Empirical Strategy (or Model)
Present. Wait. User may adjust sample restrictions, variable definitions, specification.

## GATE 3: Results + Robustness + Conclusion
**Hard prerequisite — never file existence:**
- at least one `estimate-*` chunk and one `tbl-*` chunk exist in the declared manuscript
- `quarto render <manuscript>` exits 0 (`python3 .claude/scripts/pipeline.py pre writer` checks both)

Present. Wait.

## Application rules
- Single-section drafts: that section's gate applies. `/write full`: all three in sequence.
- **BLOCKED:** Results/Conclusion without an estimation chunk and a clean render.
- **VERIFY:** citations needing user confirmation. **VOICE:** style guide not yet extracted.
