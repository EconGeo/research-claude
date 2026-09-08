# Table Standards

Publication-quality tables in the Quarto-native pipeline. Tables are **chunks in
`manuscript_<project>.qmd`**, not `.tex` fragments written to disk and `\input{}`
somewhere else. There is no `paper/tables/` directory and nothing exports a bare
`tabular`.

**Mechanics live in the format rules, not here.** This file covers the judgment
those rules do not: what belongs in a table, how it is laid out, and when a table
should have been a figure.

| Output | Package | Authority |
|---|---|---|
| Word (`docx`) | `modelsummary(..., output = "flextable")`, `set_flextable_defaults()`, `fit_to_width(PAGE_WIDTH)` | `.claude/rules/quarto-word.md` |
| PDF | `modelsummary(..., booktabs = TRUE)` / `kbl(..., booktabs = TRUE)` | `.claude/rules/quarto-pdf.md` |

Both, always:

- The chunk label starts `tbl-` — that is what makes Quarto number it
- `#| tbl-cap:` carries the caption; never a title row inside the table
- `booktabs` three-line rules; never `\hline`, never a vertical rule
- Notes are present on every table (INV-1), via the `notes` argument for PDF or an
  italic paragraph / `custom-style="Footnote Text"` div after the chunk for Word
- Reference it as `@tbl-label`; never write "Table 3"

Journal-specific conventions (significance stars, note format) adapt to the target
journal — see `journal-profiles.md`.

---

## No In-Table Titles or Notes

- **Never** embed a title in the table body or as a header row — it goes in `#| tbl-cap:`
- **Never** embed notes, sources, or footnotes inside the table itself
- The chunk label identifies the table; the caption describes it

---

## Coefficient Display

- Point estimates on one row, standard errors in parentheses on the row below
- Standard errors identified in the note, e.g. "Robust standard errors in
  parentheses" or "Clustered at the municipality level" — an unlabelled SE is
  an unreadable table

**Significance reporting depends on the target journal:**

| Context | Convention |
|---------|-----------|
| **Working papers (default)** | Stars: `*` p < 0.10, `**` p < 0.05, `***` p < 0.01, declared in the note |
| **AEA journals** (AER, AEJ:Applied, AEJ:Policy, AER:Insights) | No significance stars. Standard errors in parentheses; exact p-values or confidence intervals for key results. |
| **All other journals** | Stars acceptable. Follow `journal-profiles.md`. |

```r
#| label: tbl-main
#| tbl-cap: "Effect of Treatment on Log Wages"
modelsummary(
  models,
  stars = c("*" = 0.10, "**" = 0.05, "***" = 0.01),  # set FALSE for AEA journals
  coef_rename = c(treatment = "Treatment", log_income = "Log income"),
  gof_map = c("nobs", "r.squared", "adj.r.squared"),
  notes = "Robust standard errors in parentheses. Clustered at the municipality level.",
  escape = FALSE
)
```

`fixest::etable()` is an acceptable alternative when the models are `fixest`
objects and you need its fixed-effects reporting; the same rules apply.

---

## Column and Row Structure

- **Column (1), (2), …** headers in the first row
- **Dependent variable** stated in a spanning header or the first subheader row
- **Variable names** left-aligned and human-readable — this is what `coef_rename`
  is for:
  - `Log wages`, not `ln_wage_deflated`
  - `Female`, not `sex_2`
  - `Years of education`, not `educ_yrs`
- **Numeric columns** right- or decimal-aligned
- **N**, **R²**, **Fixed effects** (Yes/No), **Controls** (Yes/No) at the bottom

## Panel Structure

For multi-panel tables use `modelsummary`'s `shape` argument or bind grouped
outputs — panel labels italic, left-aligned, spanning all columns, with a rule
under each label and a small gap between panels. Do not hand-write
`\multicolumn` rows: that only renders for PDF and silently degrades in Word.

---

## Table Type Templates

Defaults. Adapt columns to the paper.

**Descriptive statistics** — Mean and SD in separate columns, never stacked in
parentheses. Categorical/binary variables report a percentage in the Mean column
with SD blank. Sample size stated once in the notes, not as a column. Add Min/Max
only when the range is substantively important.

**Regression results** — one column per specification, column headers naming the
estimator (OLS / IV / PPML). Treatment coefficient first, then the bottom block:
Controls, Fixed Effects, Observations, R².

**Multi-outcome** — one panel per outcome, specifications constant across panels,
the bottom block reported once at the end.

**Balance table** — Treatment, Control, Difference, SE, p-value. Report the joint
test somewhere; a table of fifteen individually insignificant differences is not
evidence of balance.

**Robustness** — column headers describe *what changes* (Baseline, Alt. controls,
Alt. sample, Alt. estimator). Same outcome across all columns, or it is not a
robustness table.

---

## When a table should be a figure

A table the reader has to scan to find a pattern is a figure. Specifically:

- More than ~8 estimates the reader is meant to *compare* → coefficient plot
- Anything with a time dimension (event study, dynamic effects) → figure, always
- A robustness table where the point is "the estimate is stable" → specification
  curve; the reader should see stability, not verify it arithmetically

Keep the table in an appendix when a referee will want the exact numbers.

---

## Prohibited Patterns

| Pattern | Reason |
|---------|--------|
| Title row inside the table | Titles go in `#\| tbl-cap:` |
| Notes embedded in the table body | Notes go below the table |
| `\hline` | Use booktabs rules |
| Vertical rules | Never used in economics journals |
| `stargazer` | Deprecated workflow; use `modelsummary` or `fixest::etable` |
| `xtable` without booktabs | Not journal quality |
| Raw variable names in labels | Human-readable labels required (`coef_rename`) |
| Writing a `.tex` fragment to disk | Tables are chunks in the manuscript; there is no `paper/tables/` |
| `kableExtra` in Word output | Produces LaTeX/HTML, not a Word table — use flextable |
| Chunk label without a `tbl-` prefix | Quarto will not number or cross-reference it |
| A number typed into prose from a rendered table | INV-11 — use an inline `` `r ` `` expression against the model object |
