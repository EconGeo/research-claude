---
name: analyze
description: End-to-end analysis inside the declared manuscript — dispatches data-engineer (wrangling chunks) and coder (estimation, robustness, tbl-/fig- chunks), each followed by coder-critic. R primary; Python/Julia via their engines.
argument-hint: "[goal or strategy-memo path]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Analyze

Run the analysis as chunks of the declared manuscript (`manuscript:` in `CLAUDE.md`), by
dispatching **data-engineer** then **coder**, with **coder-critic** after each.

**Input:** `$ARGUMENTS` — analysis goal or path to the strategy memo.

## Workflow

### Step 0: Resolve the manuscript and check inputs
```bash
python3 .claude/scripts/pipeline.py manuscript
python3 .claude/scripts/pipeline.py pre coder      # standalone: informational only; orchestrated: /pipeline enforces it
```

### Step 1: Pre-Code Report (mandatory)
The coder outputs `.claude/skills/analyze/templates/pre-code-report.md` filled in — strategy memo
path, paper type, naming map, planned **chunk labels** (not filenames). If the memo is missing,
proceed on the user's description and flag that categories 1–3 of the review cannot be verified.

### Step 2: Wrangling — data-engineer, then its paired critic
Dispatch **data-engineer**: `build-*` chunks with `cache.extra`, manifest rows, `tbl-summary`
chunk. Then `python3 .claude/scripts/pipeline.py log data-engineer` (standalone) and dispatch
**coder-critic** on the manuscript; record its score:
`python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --report <path>`.

### Step 3: Estimation — coder, then its paired critic
Dispatch **coder**: `estimate-*`, `robustness-*`, `tbl-*`, `fig-*` chunks per
`.claude/skills/analyze/templates/chunk-structure.md`; render clean; prose check clean. Log,
dispatch **coder-critic**, record the score. Three rounds maximum
(`pipeline.py state strike coder` after each failing round; escalation target from the registry).

### Step 4: What coder-critic checks
The twelve deductions in `.claude/rules/quarto-empirical.md` ("What the Coder-Critic Checks")
plus the numerical-discipline rows of `.claude/skills/review/config/scoring-rubrics.md`, using
`.claude/skills/review/templates/code-review-16-categories.md`. Report to
`quality_reports/reviews/coder-critic_<date>.md`.

### Step 5: Present
Rendered output path; chunk labels added; coder-critic score; open items (missing data,
specifications the memo names that could not be run).

## Bundled resources
| File | Purpose |
|---|---|
| `.claude/skills/analyze/templates/chunk-structure.md` | the five chunk patterns |
| `.claude/skills/analyze/templates/pre-code-report.md` | mandatory pre-check |
| `.claude/skills/analyze/templates/paper-to-code-map.md` | naming map (lives in the setup chunk) |
| `.claude/skills/analyze/references/table-standards.md` | tables |
| `.claude/skills/analyze/references/figure-standards.md` | figures |
| `.claude/skills/analyze/gotchas.md` | failure points |

## Principles
- **Reproduce, don't guess.** If the user specifies a regression, run exactly that.
- **Strategy alignment.** If a memo exists, chunks implement it faithfully.
- **Creator then critic, every time.** Each creator's paired critic is declared in `.claude/rules/registry.yaml`, not restated here.
- **One manuscript.** No script tree, no results file, no output directory; the render is the output.
