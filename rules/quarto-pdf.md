# Quarto PDF Output: Format & Rendering Reference

**PDF is the canonical output of the single `manuscript.qmd`.** The document
architecture — single source of truth, caching, inline expressions, the write
gate — is governed by `quarto-empirical.md` and applies to every output format.

This file covers **only** the PDF-specific `format: pdf:` block, table/figure
mechanics, and the R-package landmines we hit getting clean LaTeX output. Do not
redefine `execute:`/`cache:`, the filename, the bibliography, or the analysis
structure here — those belong to `quarto-empirical.md`.

---

## The `pdf:` format block

Add this under `format:` in `manuscript.qmd`. The surrounding YAML (title, author,
date, abstract, `execute: cache: true`, `bibliography:`) comes from `quarto-empirical.md`.

```yaml
format:
  pdf:
    pdf-engine: xelatex
    include-in-header: "templates/quarto-preamble.tex"
    toc: false
    number-sections: true
    keep-tex: false        # flip to true only to inspect generated LaTeX while debugging
    cite-method: biblatex
```

`cite-method: biblatex` makes the PDF render citations through biblatex/biber, not
pandoc citeproc. **The document-level `csl:` field is ignored for PDF output** — it
only affects Word (see `quarto-word.md`).

---

## Tables: kableExtra (PDF only)

kableExtra emits LaTeX, so it works **only** in PDF output. The two recurring gotchas:

- **`escape = FALSE` is required** whenever variable names, notes, or cell contents
  contain LaTeX-special characters (`$`, `_`, `%`, `&`). Without it kableExtra
  escapes them and they render as literal backslashed text.
- **`kable_styling(latex_options = "hold_position")`** pins the table where you place
  it instead of letting LaTeX float it to the next page.

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

Quarto automatically uses vector PDF format for figures in PDF output. Do **not**
set `fig-format` — overriding it forces raster output and degrades print quality.

---

## Citations

Use pandoc syntax (works in both prose and Quarto):

| Syntax | Result |
|--------|--------|
| `@smith2024` | Smith (2024) |
| `[@smith2024]` | (Smith, 2024) |
| `[@smith2024, p. 12]` | (Smith, 2024, p. 12) |

Never use `\citet{}` / `\citep{}` — LaTeX-only, renders as raw text in any non-PDF
output (and breaks the single-source model the moment you also render to Word).

---

## Build

```bash
quarto render manuscript.qmd            # default format (PDF)
quarto render manuscript.qmd --to pdf
```

---

## What the writer-critic checks (PDF format mode)

Format-specific only. General-architecture checks (`source()`, missing `fig-cap`,
`booktabs`, hardcoded numbers, caching) are owned by `quarto-empirical.md`'s
coder-critic — not duplicated here.

**Blocking deductions:**
- Missing `format: pdf:` block (-5)
- `pdf-engine:` not `xelatex` (-3)
- Missing `cite-method: biblatex` (-3)
- Missing `include-in-header:` (-3)
- `\citet{}` / `\citep{}` in prose (-3 per, max -10)
- kableExtra table missing `escape = FALSE` when names/notes contain LaTeX (-3)
- Tables rendered with flextable in PDF output — wrong package (-5)
