# Quarto PDF Pipeline

**One file, one output: PDF only via XeLaTeX.**

Use `manuscript_quarto_pdf.qmd` for academic paper PDF output. Do NOT add a `docx:` format block to this file — the rendering paths are incompatible (biblatex vs pandoc CSL, kableExtra vs flextable, LaTeX prose vs markdown-only).

For Word output, use a **separate** `manuscript_quarto_word.qmd` (see `quarto-word.md`).

---

## YAML Header (Required)

```yaml
---
title: "Paper Title"
author:
  - name: "Author Name"
    affiliation: "Institution"
    email: "email@university.edu"
date: today
abstract: |
  Abstract text here. Must be 150 words or fewer.
format:
  pdf:
    pdf-engine: xelatex
    include-in-header: "templates/quarto-preamble.tex"
    toc: false
    number-sections: true
    keep-tex: true
    cite-method: biblatex
execute:
  echo: false
  message: false
  warning: false
  cache: false
bibliography: "references.bib"
link-citations: true
---
```

Do NOT include `docx:` or `cite-method: biblatex` in a Word-output file.

---

## Tables: kableExtra (PDF only)

````markdown
```{r}
#| label: tbl-main-results
#| tbl-cap: "Main Results: Effect of X on Y"
kbl(df, booktabs = TRUE, digits = 3, escape = FALSE) |>
  kable_styling(latex_options = "hold_position") |>
  add_footnote("Notes: Robust standard errors in parentheses.", notation = "none")
```
````

For regression tables, use `modelsummary` with `output = "kableExtra"`:

````markdown
```{r}
#| label: tbl-main-reg
#| tbl-cap: "Main Regression Results"
modelsummary(
  models,
  output   = "kableExtra",
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  notes    = "Robust standard errors in parentheses.",
  escape   = FALSE
)
```
````

---

## Figures

````markdown
```{r}
#| label: fig-event-study
#| fig-cap: "Event Study: Effect of X on Y. *Notes:* 95% CI shown."
#| fig-width: 6
#| fig-height: 4
# ggplot code here
```
````

Quarto automatically uses vector PDF format for figures in PDF output.

---

## Citations

Use pandoc syntax (works in both prose and Quarto):

| Syntax | Result |
|--------|--------|
| `@smith2024` | Smith (2024) |
| `[@smith2024]` | (Smith, 2024) |
| `[@smith2024, p. 12]` | (Smith, 2024, p. 12) |

Never use `\citet{}` / `\citep{}` — LaTeX-only, renders as raw text in any non-PDF output.

---

## Build

```bash
quarto render manuscript_quarto_pdf.qmd         # PDF only
quarto render manuscript_quarto_pdf.qmd --to pdf
```

---

## What the writer-critic checks (Quarto PDF mode)

**Blocking deductions:**
- `docx:` format block present (-10) — prohibited in PDF-only file
- Missing `format: pdf:` section (-5)
- `pdf-engine:` not `xelatex` (-3)
- Missing `cite-method: biblatex` (-3)
- Missing `bibliography:` field (-5)
- Missing `include-in-header:` (-3)
- `\citet{}` / `\citep{}` in prose (-3 per, max -10)
- Figure chunk missing `#| fig-cap:` (-5)
- Table chunk missing `booktabs = TRUE` (-5)
- Table chunk missing notes (-5)
- Any `source()` call in a chunk (-10)
