# Quarto Empirical Pipeline: Single-Document Standard

**This is the required pipeline for all new empirical research projects in research-claude.**

The single `.qmd` file is the source of truth for all analysis, tables, figures, and prose.
No external R analysis scripts. No results registry. No ground-truth CSV.
The rendered PDF is the paper.

---

## Architecture

```
project/
├── data/
│   └── raw/           ← raw data files (gitignored if large/proprietary)
├── manuscript.qmd     ← single source of truth: code + prose
├── _cache/            ← gitignored; knitr cache (persists across sessions)
├── manuscript_files/  ← gitignored; render artifacts
├── references.bib
└── templates/
    ├── quarto-preamble.tex
    └── chicago-author-date.csl
```

External R scripts are permitted **only** for:
- Data acquisition from APIs or databases requiring authentication
- Raw file downloads from restricted sources (WRDS, Census restricted-use, etc.)

All data cleaning, wrangling, estimation, robustness checks, tables, and figures
live inside `manuscript.qmd` as cached code chunks. There is no `scripts/R/`
analysis directory, no `00_master.R`, and no `results_ground_truth.csv`.

---

## Required YAML

```yaml
---
title: "Paper Title"
author:
  - name: "Author Name"
    affiliation: "Institution"
    email: "email@university.edu"
date: today
abstract: |
  Abstract text. 150 words or fewer.
format:
  pdf:
    pdf-engine: xelatex
    include-in-header: "templates/quarto-preamble.tex"
    toc: false
    number-sections: true
    keep-tex: false
    cite-method: biblatex
execute:
  echo: false
  message: false
  warning: false
  cache: true
bibliography: "references.bib"
csl: "templates/chicago-author-date.csl"
link-citations: true
---
```

`execute: cache: true` is **required** globally. Individual chunks override with
`cache: false` only for genuinely fast operations (printing objects, inline setup).

---

## Cache Setup Patterns

### Setup Chunk — never cached

```r
#| label: setup
#| cache: false
#| include: false
library(here)
library(tidyverse)
library(fixest)
library(did)
library(modelsummary)
library(kableExtra)

set.seed(20240101L)

# Dependency chain (document the full DAG here):
# build-panel → estimate-main → event-study
#                             → robustness-never-treated
#                             → robustness-balanced
#             → figure-trends
```

### Data / Wrangling Chunks — cache.extra required

`cache.extra` forces cache invalidation when raw data files change.
Without it, a changed raw file will not invalidate the cached panel.

```r
#| label: build-panel
#| cache: true
#| cache.extra: !expr list(file.mtime(here("data/raw/permits.csv")),
#|                         file.mtime(here("data/raw/wrluri.csv")))
panel <- read_csv(here("data/raw/permits.csv")) |>
  left_join(read_csv(here("data/raw/wrluri.csv")), by = "cbsa") |>
  filter(year >= 2000) |>
  mutate(log_permits = log(permits + 1))
```

Use `!expr list(...)` for multiple files. Use `file.mtime()` not `file.info()`.

### Estimation Chunks — dependson required

```r
#| label: estimate-main
#| cache: true
#| dependson: "build-panel"
att_result <- att_gt(
  data        = panel,
  yname       = "log_permits",
  tname       = "year",
  idname      = "cbsa",
  gname       = "treat_year",
  clustervars = "cbsa"
)
es <- aggte(att_result, type = "dynamic")
```

`dependson` takes the chunk label as a string. Chain it through the full DAG:
if `estimate-main` depends on `build-panel`, and `table-main` depends on
`estimate-main`, declare each link explicitly — do not skip levels.

### Figure and Table Chunks

```r
#| label: fig-event-study
#| cache: true
#| dependson: "estimate-main"
#| fig-cap: "Event Study: Effect of Zoning Reform on Permitting. *Notes:* ..."
#| fig-width: 6
#| fig-height: 4
ggplot(es_df, aes(x = t, y = att, ymin = att - 1.96*se, ymax = att + 1.96*se)) +
  geom_pointrange() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  theme_minimal(base_family = "serif")
```

```r
#| label: tbl-main-results
#| cache: true
#| dependson: "estimate-main"
#| tbl-cap: "Main Results: Effect of Zoning Reform on Log Permits"
modelsummary(
  list("Baseline" = m1, "Controls" = m2, "Never-Treated" = m3),
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  notes    = "Clustered SEs at the CBSA level. Sample: 2000–2020."
)
```

---

## Inline Expression Requirement (Non-Negotiable)

Every numerical claim in prose must be an inline R expression. No hardcoded numbers.

**Required:**
```markdown
The average treatment effect is `r round(es$overall.att, 3)` log points
(SE = `r round(es$overall.se, 3)`), significant at the 1% level.
```

**Prohibited:**
```markdown
The average treatment effect is −0.142 log points (SE = 0.038).
```

Hardcoded numbers do not update when estimation changes. They are the Quarto
equivalent of a missing registry key — invisible to the render pipeline, silently
wrong after any change.

A render that exits 0 with all inline expressions populated is a proof of internal
consistency. A hardcoded number is a gap in that proof.

---

## The Write Gate (2 Items)

```
[ ] 1. Raw data is in place: every file referenced in cache.extra exists in data/raw/
[ ] 2. quarto render manuscript.qmd exits 0 with no NA/NaN in inline expressions
```

That is the complete gate. No script inventory. No registry coverage audit. No
timestamp check. If the render exits 0, all numbers are consistent with the current
analysis by construction.

If any chunk fails or any inline expression evaluates to NA, quarto render exits
non-zero and identifies the exact chunk and line. There are no silent wrong values.

---

## Word Output (Optional Secondary)

Word output is available from the **same** `manuscript.qmd` by adding a `docx:`
format block alongside `pdf:`. See `quarto-word.md` for the block contents,
flextable table mechanics, and the CSL gotcha (PDF uses biblatex and ignores `csl`;
Word needs an APA `csl` inside its `docx:` block). Word is for co-author sharing and
revision responses only — the PDF is the canonical submission artifact.

Do NOT maintain a separate Word-first `.qmd`. One source file, multiple outputs.

---

## Gitignore Requirements

```
*_cache/
*_files/
*.rdb
*.rdx
```

The cache is machine-local and must not be committed. Collaborators re-render from
scratch on first clone (slow once, fast on all subsequent renders). Never commit
cache files — they are binary, large, and machine-specific.

---

## Acquisition Scripts (When Required)

If data requires API authentication or database access, a thin acquisition script
is permitted:

```
scripts/acquire/
    01_download_permits.py   ← API call → data/raw/permits.csv
    02_query_wrds.R          ← WRDS query → data/raw/compustat.rds
```

Rules for acquisition scripts:
- Save to `data/raw/` only — no wrangling, no panel construction
- One script per data source; no master acquisition script needed
- Must be independently runnable (no dependencies on other scripts)
- The files they produce are what `manuscript.qmd` reads via `cache.extra`

Acquisition scripts are not analysis scripts. Their outputs are inputs to the
`.qmd`, not intermediate products in a pipeline.

---

## What the Coder-Critic Checks (Quarto Empirical Mode)

Invoked when the reviewed artifact is `manuscript.qmd` and this rule is present.

### Blocking Deductions

| Issue | Deduction |
|-------|-----------|
| `execute: cache: true` absent from YAML | −10 |
| `set.seed()` absent from setup chunk | −5 |
| Setup chunk has `cache: true` (must be `false`) | −5 |
| Data/wrangling chunk missing `cache.extra` for external files | −5 per chunk |
| Estimation chunk missing `dependson` pointing to its data source | −5 per chunk |
| Full dependency chain not documented in setup chunk | −3 |
| Prose number hardcoded (not an inline `r` expression) | −10 per instance |
| `source()` call inside any chunk | −10 |
| Analysis R script present in `scripts/R/` beyond acquisition scripts | −5 per script |
| `_cache/` absent from `.gitignore` | −5 |
| Figure chunk missing `#\| fig-cap:` | −5 |
| Table chunk missing `booktabs = TRUE` | −5 |

### Advisory (Reported, Not Deducted)

- More than 3 levels of `dependson` nesting — consider flattening the DAG
- Chunk without `cache: true` runs > 5 seconds — add caching or explain omission
- `cache.extra` uses `file.info()` instead of `file.mtime()` — less reliable
- Inline expression without `round()` for floating-point values

---

## Relation to Other Rules

| Rule | Status for new projects |
|------|------------------------|
| `quarto-empirical.md` (this rule) | **Required** — pipeline architecture, caching, data integrity, single source of ground truth |
| `quarto-pdf.md` | **Required** — `pdf:` format block + kableExtra/figure/citation mechanics for the canonical PDF output |
| `quarto-word.md` | Optional — `docx:` format block + flextable/CSL mechanics, only if Word secondary output is needed |
| `registry-verification-gate.md` | **Legacy only** — registry-pattern projects (e.g. zoning2026) |
| `working-paper-format.md` (clo-author) | **Legacy only** — LaTeX-first projects |

`quarto-pdf.md` and `quarto-word.md` are **format-reference** docs for the two output
formats of the single `manuscript.qmd` — they describe rendering mechanics and
R-package landmines, not a competing file architecture. This rule owns the
source-of-truth, caching, and data-integrity governance; they own format details.

For any project starting after this rule was introduced, the Quarto empirical
pipeline is the default. Deviations require explicit justification in CLAUDE.md.
