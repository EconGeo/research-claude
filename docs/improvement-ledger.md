# Improvement ledger

Append-only. Written by `/checkpoint` (one row per pipeline improvement candidate), read by `/promote`. A target named by 2 distinct projects is flagged REPEATED by `.claude/scripts/ledger.py show`. Status is `open`, `landed <sha>` or `declined: <reason>`. Notes are generic — no dataset, journal or paper nouns; this repo is public.

| id | date | project | target | note | status |
|---|---|---|---|---|---|
| L-001 | 2026-09-04 | NAR_settlement | rules/quarto-empirical.md | Author correction: .qmd written without reading the Quarto authoring reference; silent render failures (dropped YAML field, doubled exhibit numbers, plain-text section refs). Nothing in the shipped tree names the reference. | landed 98c776d |
| L-002 | 2026-09-21 | NAR_settlement | rules/quarto-empirical.md | Same class twice in one session: kableExtra footnote boxed to table width clipped a column, then clipped words from a note; render exit 0. Only a check of the rendered page catches it. | landed 98c776d |
| L-003 | 2026-06-08 | zoning2026 | rules/quarto-empirical.md | R-generated .tex tables: unescaped % and Unicode outside math mode; fixed per file, never as a pre-render check. | landed 98c776d |
| L-004 | 2026-09-25 | NAR_settlement | rules/registry.yaml | The writer pre-predicate requires a tbl-* chunk label, but projects that caption exhibits by hand must avoid tbl-/fig- labels (Quarto adds a second number), so pre writer fails on a valid manuscript; accept a configurable exhibit label glob. | open |
| L-005 | 2026-09-25 | NAR_settlement | agents/writer-critic.md | writer-critic scores a Render category but has only Read/Grep/Glob, so it cannot run the render or project gate; either grant Bash or have the dispatching skill run the gate and pass the log in. | open |
| L-006 | 2026-09-25 | NAR_settlement | references/personal-style-guide.md | The pipeline lock links the project style guide to the research-claude template rather than the user's filled guide in ~/Research/.claude/references, so Voice Fidelity cannot be scored after a re-link. | landed a4af1ea |
