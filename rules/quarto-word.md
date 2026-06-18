# Quarto Word Output: Format & Rendering Reference

**Word (DOCX) is the optional secondary output of the single `manuscript_<project>.qmd`** —
add a `docx:` format block alongside `pdf:` when a co-author needs Word or a journal
requires a revision in `.docx`. The PDF remains the canonical submission artifact.
There is **no separate Word-first `.qmd`**: one source file, multiple outputs.

The document architecture — single source of truth, caching, inline expressions,
the write gate — is governed by `quarto-empirical.md`. This file covers **only** the
`docx:` format block, flextable mechanics, and the R-package landmines specific to
Word output. Do not redefine `execute:`/`cache:`, the filename, or the analysis
structure here.

---

## The `docx:` format block

Add this under `format:` alongside the `pdf:` block. The surrounding YAML (title,
author, date, abstract, `execute: cache: true`, `bibliography:`) comes from
`quarto-empirical.md`.

```yaml
format:
  pdf:
    # ... (see quarto-pdf.md)
  docx:
    reference-doc: "templates/word-reference.docx"
    csl: "templates/apa.csl"
    toc: false
    number-sections: false
```

**The CSL gotcha (single-file model):** PDF uses `cite-method: biblatex` and ignores
`csl`. Word has no biblatex — it renders citations through pandoc citeproc, which
needs a `csl`. Put `csl: "templates/apa.csl"` **inside the `docx:` block** so Word
uses APA regardless of any top-level/PDF citation setting. Source APA from your local
Zotero styles (`~/Zotero/styles/apa.csl`) — no need to bundle a copy in `templates/`.

Do **not** put `include-in-header:`, `cite-method: biblatex`, or `pdf-engine:` in the
`docx:` block — they are LaTeX-only and cause errors for Word output.

---

## Tables: flextable (Word only)

`kableExtra` emits LaTeX and produces garbage in Word — use **flextable** for the
`docx:` output. Set global flextable defaults once in the setup chunk (the chunk
itself, with its library loads and `set.seed()`, is defined per `quarto-empirical.md`):

````markdown
```{r}
#| label: setup-word
#| cache: false
#| include: false
library(flextable)

set_flextable_defaults(
  font.family = "Times New Roman",
  font.size   = 10,
  theme_fun   = theme_booktabs,
  padding     = 3
)
PAGE_WIDTH <- 6.5
options(modelsummary_factory_default = "flextable")
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

---

## Figures

`fig-width: 6.5` matches Word's 6.5-inch text width (1-inch margins on 8.5-inch paper).
Quarto uses PNG by default for Word output — this is correct; do **not** force PDF
figures (they error in DOCX). Set `fig-dpi: 200` for print-quality raster.

````markdown
```{r}
#| label: fig-event-study
#| fig-cap: "Event Study: Effect of X on Y. *Notes:* 95% CI shown."
#| fig-width: 6.5
#| fig-height: 4
#| fig-dpi: 200
# ggplot code here
```
````

---

## Citations

Same pandoc syntax as PDF (`@smith2024` → Smith (2024); `[@smith2024]` →
(Smith, 2024)). With the APA CSL in the `docx:` block, parenthetical citations render
as "(Smith, 2024)" in the Word doc.

---

## Page breaks

```markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
```

Or place `\newpage` on its own paragraph — Quarto converts it to a Word page break
for DOCX.

---

## R-package / option landmines for Word

| Prohibited in Word output | Reason |
|---------------------------|--------|
| `include-in-header:` in the `docx:` block | PDF/LaTeX only |
| `cite-method: biblatex` in the `docx:` block | PDF/LaTeX only; Word uses citeproc + CSL |
| `kableExtra` | Produces HTML/LaTeX, not Word tables |
| Inline LaTeX (`\textbf{}`, `\noindent`) | Appears as literal text in Word |
| `fig-pos: H` | LaTeX float placement — ignored in Word |
| `dev = "pdf"` / `fig-format: pdf` | Word embeds PNG; PDF causes errors |
| Chicago CSL | Use APA CSL for Word; Chicago/biblatex is the PDF path |

---

## Build

```bash
quarto render manuscript_<project>.qmd --to docx   # Word output from the same file
```

---

## What the writer-critic checks (Word format mode)

Format-specific only. General-architecture checks (`source()`, hardcoded numbers,
caching) are owned by `quarto-empirical.md`'s coder-critic — not duplicated here.
Applies when a `docx:` block is present (i.e. Word output is requested).

**Blocking deductions:**
- `docx:` block missing its `csl:` (Word falls back to the wrong style) (-3)
- `csl:` in the `docx:` block is not APA (-3)
- `include-in-header:` or `cite-method: biblatex` inside the `docx:` block (-3)
- `kableExtra` loaded or used for Word tables (-5)
- Inline LaTeX in prose (-3 per, max -10)
- Tables not using flextable (-5)
- `modelsummary` without `output = "flextable"` or the global option (-5)
- `set_flextable_defaults()` not called in the Word setup chunk (-3)
- `fig-width:` exceeds 6.5 (-2)
