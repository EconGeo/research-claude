# Quarto Empirical Pipeline: Single-Document Standard

**This is the required pipeline for all new empirical research projects in research-claude.**

The single `.qmd` file is the source of truth for all analysis, tables, figures, and prose.
No external R analysis scripts. No results registry. No ground-truth CSV.
The rendered PDF is the paper.

> **File name and declaration.** A new project is scaffolded with `manuscript_<project>.qmd`
> (`<project>` = the directory basename). Whatever the file is called, the project's `CLAUDE.md`
> declares it on a line of its own: `manuscript: manuscript_<project>.qmd`. Every predicate in
> `.claude/scripts/pipeline.py`, every hook and every skill resolves "the manuscript" through
> that line, and `check_install.sh` fails when it is absent or names more than one file. Examples
> below write `manuscript_<project>.qmd` and mean the declared manuscript.

---

## Architecture

```
project/
├── data/
│   └── raw/           ← raw data files (gitignored if large/proprietary)
├── manuscript_<project>.qmd  ← single source of truth: code + prose
├── _cache/            ← gitignored; knitr cache (persists across sessions)
├── manuscript_<project>_files/  ← gitignored; render artifacts
├── references.bib
└── templates/
    └── quarto-preamble.tex   ← biblatex style set here; the PDF path uses no CSL
```

External R scripts are permitted **only** for:
- Data acquisition from APIs or databases requiring authentication
- Raw file downloads from restricted sources (WRDS, Census restricted-use, etc.)

All data cleaning, wrangling, estimation, robustness checks, tables, and figures
live inside `manuscript_<project>.qmd` as cached code chunks. There is no `scripts/R/` <!-- residue:prohibition -->
analysis directory, no `00_master.R`, and no `results_ground_truth.csv`. <!-- residue:prohibition -->

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
link-citations: true
# No top-level csl: the PDF path renders citations via biblatex (cite-method above).
# Word output, when added, sets its own APA csl inside the docx: block (see quarto-word.md).
---
```

`templates/quarto-preamble.tex` is seeded into every project by `apply.sh`
(`seeds/quarto-preamble.tex`); edit the project copy, never the seed.

`execute: cache: true` is **required** globally. Individual chunks override with
`cache: false` only for genuinely fast operations (printing objects, inline setup).

---

## Design block and claim helpers

The research design is declared once, in the manuscript's YAML front matter under `design:`, and
signed by the author in chat (core rule 13). It carries no significance level and no verdict
words: the inference rule says how standard errors are computed, and the conventional star
levels (core rule 14) say what "statistically significant" means.

```yaml
design:
  inference: {rule: cluster-robust, cluster: region, id: INF-1}
  treatment:
    definition: "…operational test…"
    date: YYYY-MM-DD
    source: {cite: key2024, page: 12, quote: "…"}
  sample: ["…rule…", "…rule…"]
  hypotheses:
    H1: {estimand: "…", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.021, target_effect: 0.03, file: explorations/power.qmd}
    size:  {rejection_at_0.10: 0.104, reps: 1000, file: explorations/size.qmd}
```

Each hypothesis names its model object on `spec:`; `rc_fingerprint()` stops when that object is
missing.

**Power and size checks** are `explorations/power.qmd` and `explorations/size.qmd`. Their results
are copied into `design.checks` before signing (`pipeline.py design sign` refuses without both
entries and their files), and they are re-run on an amendment that touches the inference rule,
the sample, the treatment or an outcome. A check chunk never goes in the manuscript (core rule 2).

**The setup chunk** pastes the helpers from `.claude/templates/claims-helpers.R.txt` below the
`library()` calls (pasted, never sourced) and then sets:

```r
design <- rc_design("manuscript_<project>.qmd")
knitr::opts_chunk$set(cache.extra = list(rc_design_hash(design), rc_data_hash()))
# tested: modelsummary 2.6.0 stars with p ≤ cutoff but its automatic note says p <
options(modelsummary_stars_note = FALSE)
```

The global `cache.extra` makes a design amendment or a data change invalidate every model cache.
No chunk sets its own `cache.extra`: a chunk-level value replaces the global key rather than adding
to it, so that chunk would survive a design or data change. `modelsummary_stars_note = FALSE`
drops modelsummary's automatic star note — tested (modelsummary 2.6.0): it assigns stars with
p ≤ cutoff, but its note says p < — so pass the legend `* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01` in
the table's `notes` instead. The default PDF font has no `≤` glyph; the seeded
`templates/quarto-preamble.tex` maps it with `\usepackage{newunicodechar}` and
`\newunicodechar{≤}{\ensuremath{\leq}}` — a paper whose preamble was seeded before those lines
existed adds them, or its legend prints a missing-character box.

**The final chunk** writes the results fingerprint:

```r
#| label: fingerprint
#| cache: false
#| include: false
rc_fingerprint()
```

It writes `quality_reports/render_fingerprint.json` under the project root, which is committed
with the manuscript. The root is `rc_root()`, the nearest directory at or above the working
directory that holds `CLAUDE.md`: Quarto runs chunks in the manuscript's directory, so a manuscript
in a subdirectory still writes the root's `quality_reports/`, and `rc_data_hash()` hashes the root's
`data/raw` and `data/derived`. Relative path arguments to either resolve under the root.
`pipeline.py` compares that file with the fingerprint each score was earned under to decide which
reviews a re-estimation reopens (core rule 15).

**Design changes are disclosed in the paper.** Once `quality_reports/design_amendments.csv` has
a row, the manuscript carries this chunk, cited in the prose with `@tbl-design-changes`; the
author writes the prose around it:

```r
#| label: tbl-design-changes
#| cache: false
#| tbl-cap: "Changes to the research design"
design_changes <- read.csv(here("quality_reports/design_amendments.csv"), stringsAsFactors = FALSE)
knitr::kable(design_changes, col.names = c("Date", "Field", "Before", "After", "Reason"))
```

**Result words.** Every significance, direction, comparison or universality word beside a value
is helper output (`rc_sig`, `rc_stars`, `rc_dir`, `rc_cmp`, `rc_num`, `rc_pct`), a raw inline
`if`, or a typed word in a sentence that carries a result guard,
`` `r local({stopifnot("<claim>" = <condition>); ""})` `` — inside the sentence it guards
(`.claude/rules/readable-code.md` §5).

**Run `pipeline.py render --cold` before committing a model-chunk change.** A warm cache can hide
a chunk that no longer runs or an estimate that moved. The receipt binds the chunk code, not the
file, so a prose-only edit after the cold render needs no second one. The pre-commit check
requires the receipt once the manuscript carries a `design:` block; before the retrofit it warns.

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

### Data / Wrangling Chunks — cache.extra required until the design block exists

`cache.extra` forces cache invalidation when raw data files change.
Without it, a changed raw file will not invalidate the cached panel. Once the setup chunk sets
the global key (`rc_data_hash()`, above), every chunk is covered and this chunk-level form is
deleted — a chunk-level `cache.extra` replaces the global key. The form below is for a manuscript
that has no `design:` block yet.

```r
#| label: build-panel
#| cache: true
#| cache.extra: !expr list(file.mtime(here("data/raw/outcomes.csv")),
#|                         file.mtime(here("data/raw/treatment_index.csv")))
panel <- read_csv(here("data/raw/outcomes.csv")) |>
  left_join(read_csv(here("data/raw/treatment_index.csv")), by = "unit_id") |>
  filter(year >= 2000) |>
  mutate(log_y = log(y + 1))
```

Use `!expr list(...)` for multiple files. Use `file.mtime()` not `file.info()`.

### Estimation Chunks — dependson required

```r
#| label: estimate-main
#| cache: true
#| dependson: "build-panel"
att_result <- att_gt(
  data        = panel,
  yname       = "log_y",
  tname       = "year",
  idname      = "unit_id",
  gname       = "treat_year",
  clustervars = "unit_id"
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
#| fig-cap: "Event Study: Effect of the Treatment on the Outcome. *Notes:* ..."
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
#| tbl-cap: "Main Results: Effect of the Treatment on the Log Outcome"
modelsummary(
  list("Baseline" = m1, "Controls" = m2, "Never-Treated" = m3),
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  notes    = c("Clustered SEs at the unit level. Sample: 2000–2020.",
               "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01")
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

## The Write Gate (4 Items)

```
[ ] 1. Raw data is in place: every file referenced in cache.extra exists in data/raw/
[ ] 2. quarto render manuscript_<project>.qmd exits 0 with no NA/NaN in inline expressions
[ ] 3. python3 .claude/scripts/prose_number_check.py manuscript_<project>.qmd exits 0
[ ] 4. python3 .claude/scripts/check_render.py <rendered .pdf> --expect "<each phrase the page must show>" exits 0
```

A deliberate missing-value placeholder in a table is written "n.a." or "—", never "NA": item 4
reports `NA`/`NaN`/`Inf` on the page as a failure.

No script inventory. No registry coverage audit. No timestamp check.

**Item 4 reads the page, not the source.** Item 2 proves the render ran; it proves nothing
about what the page shows, because Quarto's failures are silent: an unresolved `@ref` prints
`?@name` at exit 0, a note wider than the text block clips words out of its own sentence, an
overwide table drops a column, a declared `keywords:` never appears. Two projects corrected
these by hand before this line existed (`docs/improvement-ledger.md`, L-001..L-003). Pass
`--expect` for every phrase a journal or an invariant requires on the page, and `--columns`
for every wide table — `--columns` reads the block below the caption, so the caption must sit
above its table. The check is `.claude/references/quarto-authoring.md`'s post-render
checklist, executed.

**Item 3 is not optional, and item 2 does not subsume it.** A clean render proves
every *expression* agrees with the analysis. It proves nothing about a number that
was typed as a literal, because a literal is not an expression and there is nothing
for the render to fail on. This gate previously listed only items 1 and 2 and
asserted that a clean render made all numbers consistent "by construction." That
was wrong, and it was wrong in the way that matters: it told every agent and every
reviewer that the render was sufficient proof, so no project built the check.

A project in this pipeline is the worked example. It scored 100/100 on its own quality gate while
carrying 24 hardcoded values in prose, four of them provably wrong and each
contradicted by a table on the same page — an NL coefficient described as
"significant" beside a live p of 0.759, "all p>0.20" where the estimate gives 0.33,
a "58th percentile" that computes as the 59th, and "significant at the 0.1% level"
for a sweep whose largest p is 0.003. Three separate critic passes read past them.
Reading does not catch this class; searching does.

The checker requires a per-project allowlist at
`quality_reports/prose_number_allowlist.csv` (columns: `literal,reason`). **Per-project
means the project root**, which is where the checker looks — it walks up from the
manuscript to the nearest directory carrying a `.claude`, so a manuscript in `paper/`
still reads the project's one allowlist, not `paper/quality_reports/`. If that file is
absent the checker says so rather than reporting every literal as unexplained; a missing
allowlist and an incomplete one are different findings. Literals
that cannot come from your R — calendar years, docket numbers, a figure quoted from
a cited paper — belong there with a written reason. The standard is not that
literals are forbidden; it is that each surviving one is a decision someone made on
purpose and can defend.

The project's CLAUDE.md (where `manuscript:` is declared) also carries two declarations item 3
reads: `prose-verdict-words:` extends the lexicon of result-describing words (e.g.
"significant", "outperforms") the checker looks for beside a live value, and
`prose-verdict-ceiling: N` turns a count over N into a failure — omitted, the count is
advisory and printed with the result.

If any chunk fails or any inline expression evaluates to NA, quarto render exits
non-zero and identifies the exact chunk and line. There are no silent wrong values.

---

## Word Output (Optional Secondary)

Word output is available from the **same** `manuscript_<project>.qmd` by adding a `docx:`
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
- The files they produce are what `manuscript_<project>.qmd` reads via `cache.extra`

Acquisition scripts are not analysis scripts. Their outputs are inputs to the
`.qmd`, not intermediate products in a pipeline.

---

## What the Coder-Critic Checks (Quarto Empirical Mode)

Invoked when the reviewed artifact is `manuscript_<project>.qmd` and this rule is present.

### Blocking Deductions

| Issue | Deduction |
|-------|-----------|
| `execute: cache: true` absent from YAML | −10 |
| `set.seed()` absent from setup chunk | −5 |
| Setup chunk has `cache: true` (must be `false`) | −5 |
| Data/wrangling chunk missing `cache.extra` for external files (no global `rc_data_hash()` key) | −5 per chunk |
| A chunk that sets its own `cache.extra` while the setup chunk sets the global key | −5 per chunk |
| Estimation chunk missing `dependson` pointing to its data source | −5 per chunk |
| Full dependency chain not documented in setup chunk | −3 |
| Prose number hardcoded (not an inline `r` expression) | −10 per instance |
| `source()` call inside any chunk | −10 |
| Analysis script outside `scripts/acquire/` (any language) | −5 per script |
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
| `.claude/references/quarto-authoring.md` | **Required reading before any `.qmd` edit** — tool mechanics: what renders in which format, what drops silently; its post-render checklist is gate item 4 |

`quarto-pdf.md` and `quarto-word.md` are **format-reference** docs for the two output
formats of the single `manuscript_<project>.qmd` — they describe rendering mechanics and
R-package landmines, not a competing file architecture. This rule owns the
source-of-truth, caching, and data-integrity governance; they own format details.

For any project starting after this rule was introduced, the Quarto empirical
pipeline is the default. Deviations require explicit justification in CLAUDE.md.
