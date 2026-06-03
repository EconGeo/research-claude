# Quarto Word Pipeline

**One file, one output: Word (DOCX) only.**

Use `manuscript_quarto_word.qmd` for Word output. Do NOT add a `pdf:` format block to this file — the rendering paths are incompatible.

For PDF output, use a **separate** `manuscript_quarto_pdf.qmd` (see `quarto-pdf.md`).

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
  docx:
    reference-doc: "templates/word-reference.docx"
    toc: false
    number-sections: false
execute:
  echo: false
  message: false
  warning: false
  cache: false
  fig-width: 6.5
  fig-height: 4
  fig-dpi: 200
bibliography: "references.bib"
csl: "templates/apa.csl"
link-citations: true
---
```

**CSL:** Use `apa.csl` (not Chicago). Source from your local Zotero styles: `~/Zotero/styles/apa.csl`. No need to bundle a copy in `templates/` — just point at Zotero's copy.

Do NOT include `include-in-header:`, `cite-method: biblatex`, or `pdf-engine:` — LaTeX-only options, will cause errors.

---

## Tables: flextable (Word only)

Set global flextable defaults in the setup chunk:

````markdown
```{r}
#| label: setup
#| include: false
library(flextable)
library(modelsummary)

set_flextable_defaults(
  font.family = "Times New Roman",
  font.size   = 10,
  theme_fun   = theme_booktabs,
  padding     = 3
)
PAGE_WIDTH <- 6.5
options(modelsummary_factory_default = "flextable")

set.seed(42L)
```
````

Then for regression tables:

````markdown
```{r}
#| label: tbl-main-results
#| tbl-cap: "Main Results: Effect of X on Y"
modelsummary(
  models,
  output = "flextable",
  stars  = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  escape = FALSE
) |>
  fontsize(size = 9, part = "all") |>
  padding(padding = 2, part = "all") |>
  fit_to_width(PAGE_WIDTH)
```
````

Table notes appear as italic prose immediately after the chunk:

```markdown
*Notes: Robust standard errors clustered at the unit level in parentheses.*
```

Do NOT use `kableExtra` — it produces HTML/LaTeX, not Word tables.

---

## Figures

`fig-width: 6.5` matches Word's 6.5-inch text width (1-inch margins on 8.5-inch paper).
Quarto uses PNG by default for Word output — this is correct.

````markdown
```{r}
#| label: fig-event-study
#| fig-cap: "Event Study: Effect of X on Y. *Notes:* 95% CI shown."
#| fig-width: 6.5
#| fig-height: 4
#| dpi: 200
# ggplot code here
```
````

---

## Citations

Same pandoc syntax as PDF:

```markdown
@smith2024          → Smith (2024)
[@smith2024]        → (Smith, 2024)
```

With APA CSL, parenthetical citations render as "(Smith, 2024)" in the Word doc.

---

## Page breaks

```markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
```

Or place `\newpage` on its own paragraph — Quarto converts it to a Word page break for DOCX.

---

## What NOT to use in Word pipeline

| Prohibited | Reason |
|------------|--------|
| `format: pdf:` block | Word-only file |
| `include-in-header:` | PDF/LaTeX only |
| `cite-method: biblatex` | PDF/LaTeX only |
| `kableExtra` | Produces HTML/LaTeX, not Word |
| Inline LaTeX (`\textbf{}`, `\noindent`) | Appears as literal text in Word |
| `fig-pos: H` | LaTeX float placement — ignored in Word |
| `dev = "pdf"` / `fig-format: pdf` | Word embeds PNG; PDF causes errors |
| Chicago CSL | Use APA CSL for Word; Chicago is for PDF biblatex |

---

## Build

```bash
quarto render manuscript_quarto_word.qmd         # Word only
quarto render manuscript_quarto_word.qmd --to docx
```

---

## What the writer-critic checks (Quarto Word mode)

**Blocking deductions:**
- `format: pdf:` block present (-10) — prohibited in Word-only file
- `include-in-header:` present (-5)
- `cite-method: biblatex` present (-3)
- `kableExtra` loaded or used (-5)
- Inline LaTeX in prose (-3 per, max -10)
- Chicago CSL instead of APA (-3)
- Missing `csl:` field (-3)
- Tables not using flextable (-5)
- `modelsummary` without `output = "flextable"` or global option (-5)
- `set_flextable_defaults()` not called in setup chunk (-3)
- `fig-width:` exceeds 6.5 (-2)
- Any `source()` call in a chunk (-10)
