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

`templates/word-reference.docx` is project-created: `quarto pandoc -o templates/word-reference.docx --print-default-data-file reference.docx`, then edit styles in Word.

**The CSL gotcha (single-file model):** PDF uses `cite-method: biblatex` and ignores
`csl`. Word has no biblatex — it renders citations through pandoc citeproc, which
needs a `csl`. Put `csl: "templates/apa.csl"` **inside the `docx:` block** so Word
uses APA regardless of any top-level/PDF citation setting. Copy APA from your local
Zotero styles (`~/Zotero/styles/apa.csl`) to `templates/apa.csl` once; the manuscript
references the project copy so a coauthor's render does not depend on a Zotero install.

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
# tested: modelsummary 2.6.0 stars with p ≤ cutoff but its automatic note says p <
options(modelsummary_stars_note = FALSE)
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
  notes  = "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01",
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

### Post-render repair (required)

Quarto (1.9) wraps every cross-referenced float in a one-cell layout table whose XML breaks
the Word schema: a flextable float leaves the cell ending in a `<w:tbl>`, and each caption
gets two `<w:pPr>` blocks. Word then reports "unreadable content" and offers to recover.
`.claude/scripts/fix_docx_floats.py` repairs both in place; the project's `_quarto.yml`
runs it after every render:

```yaml
project:
  type: default
  post-render: python3 .claude/scripts/fix_docx_floats.py
```

`apply.sh` seeds this file; a project that already has a `_quarto.yml` adds the
`post-render:` line by hand. The script needs `lxml` and is idempotent. To repair a docx
rendered without it: `python3 .claude/scripts/fix_docx_floats.py <file>.docx`.

---

## Source comments

A claim about the outside world (a finding, number, date or fact from a source) is tagged in the
manuscript: `[claim]{.src ref="<registry id>" id="<tag id>"}`. Brackets inside the claim are fine
(citations, emphasis). Tag ids are one word and unique in the manuscript; `design` is reserved for
the design block's quote. A repeated id, or a `.src` tag with id `design`, is FAILED. Tag every
such claim, and tag when unsure; in the final message list any untagged outside-world claim you
noticed.

- **Registry** `quality_reports/sources.csv`, columns `id,file,label,page,sentence,cleanup,ocr`.
  `file` is relative to the project root and inside it (an absolute path or one leaving the
  project is FAILED); `sentence` is the source's own supporting sentence typed exactly as it
  appears there (it must occur verbatim, word-bounded, in exactly one paragraph, after normalising
  quotes, whitespace and ligatures and joining line-end hyphenation); `cleanup` is `;`-separated
  rule names (currently `trailing-line-numbers`: drops a number ending a line only when it runs in
  sequence with the numbers ending nearby lines, and a line holding only such a number); `ocr` is
  `true`/`false`.
- **What the comment shows** is the file's own paragraph after the entry's cleanup rules, with
  whitespace runs collapsed to one space and nothing else changed (no ligature, quote or
  character normalisation); inside the underlined sentence only, a line-end hyphen break is joined
  the way it matched.
- **Design treatment quote:** registry id `design:<cite>`; tag id `design`; see `quarto-empirical.md`.
- **Approvals** `quality_reports/source_approvals.csv`, columns
  `tag_id,ref,claim_sha256,entry_sha256,file_sha256,approved_at` (`entry_sha256`: the registry
  entry's id, sentence, cleanup, label and page). Written only by
  `python3 .claude/scripts/pipeline.py sources approve <id>…`, which needs a fresh token from the
  author's own line `approve sources: <id>[, <id>…]` (grammar and freshness: core rule 13; the ids
  must equal the command's). The token records each claim, entry and source file as they stood at
  the author's line; if any changed since, the command refuses and the author approves again.
  Never write the file by hand or from Bash.
- **Five states:** APPROVED; UNREVIEWED; NEEDS REVIEW (claim text, registry entry or source file
  changed since approval); FAILED (no registry entry, sentence not found verbatim or ambiguous,
  unreadable source, file outside the project, malformed or repeated tag id); NOT ON THIS MACHINE
  (source file missing).
- **Offer.** Before building a Word draft for the author, ask once: plain, or with source comments
  (`python3 .claude/scripts/pipeline.py sources docx`)? The sourced build writes
  `<manuscript stem>_sourced.docx` beside the manuscript and never overwrites the plain `.docx`. In
  it, each tag carries a comment by "Source check": `<label>, p. <page>. [OCR] <STATE>: ` then the
  source paragraph with the sentence underlined; FAILED and NOT ON THIS MACHINE comments give the
  reason and no source text. `sources docx` supplies the filter `source_comments.lua` itself
  (`--lua-filter`, with `-M source-comments:true`) and warns if the docx's comment count differs
  from the tag count. Nothing is added to a project's `_quarto.yml` for this feature.
- **Warnings, never blocking:** every render (`fix_docx_floats.py`, the post-render step above,
  runs `source_check.py` when it is linked beside it), `pipeline.py commit-check` (WARN lines) and
  `pipeline.py critic-inputs` (its own log section).

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
