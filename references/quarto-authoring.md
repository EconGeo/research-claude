# Quarto Authoring Reference — how to write each object so it actually renders

**Cross-domain.** This file is about the *tool*, not either pipeline, so it applies to
`~/Research/` **and** `~/Courses/`. See "Scope and precedence" below before assuming it overrides
anything.

**Why it exists.** Almost every Quarto failure is **silent**. A wrong chunk label does not error —
it prints a second number. A dropped `keywords:` does not error — the field just never appears. An
over-wide table does not error — LaTeX discards a column. A stale plain-text "Section 5.4" does not
error — it points at the wrong section forever. Nothing in a render log tells you, so the same
mistakes recur across sessions and get fixed one at a time, months later, by a reviewer. Read this
before authoring, not after.

---

## Scope and precedence

| Layer | Owns | Lives in |
|---|---|---|
| **This file** | Quarto authoring mechanics: what syntax renders in which format, and what drops silently | `.claude/references/quarto-authoring.md` in every linked project (source: the `references/` directory of the research-claude repo); `~/.claude/references/quarto-authoring.md` is a symlink to it for `~/Courses/` |
| **Research pipeline** | Document architecture: single-source `.qmd`, caching, `cache.extra`, `dependson`, the write gate, claim-source discipline | each project's `.claude/rules/quarto-empirical.md`, `quarto-pdf.md`, `quarto-word.md` |
| **Courses pipeline** | Slide design, Beamer theme, deck naming, build manifest, five-bullet rule | `~/Courses/CLAUDE.md` (Slide Pipeline) + `~/Courses/slide_pipeline/README.md` |

**Precedence: the domain layer wins on anything it addresses.** If a project rule says "chunk labels
must not start with `fig-`", that beats the general advice here — and §"Cross-references" explains
why a project would say that. This file never redefines the pipeline; it explains the tool the
pipeline is built on.

---

## The one idea that prevents most of these

**Format determines what renders.** A `.qmd` is not a document; it is a source that pandoc lowers
into a target. Anything you write that has no equivalent in the target is dropped, usually without
a warning:

| You write | HTML | PDF/LaTeX | Beamer | DOCX |
|---|---|---|---|---|
| `<span>`, `<br>`, CSS classes | works | **dropped / errors** | **dropped** | **dropped** |
| Raw LaTeX (`\textbf{}`, `\noindent`) | printed literally | works | works | **printed literally** |
| `kableExtra` | ok | works | works | **garbage — use flextable** |
| `flextable` | ok | **wrong** | **wrong** | works |
| Callouts (`.callout-note`) | works | works | works (theme recolors) | works |
| `fig-format: pdf` | n/a | works | works | **errors** |
| `csl:` | works | **ignored** (biblatex path) | ignored | works |
| a `{dot}` cell (Graphviz) | works | works, **as raster PNG** | works, **as raster PNG** | works |
| a `{mermaid}` cell | works | needs `mermaid-format: png` **and** headless Chrome | same | same |

**Before writing anything format-specific, know every format the document renders to.** A document
with both `pdf:` and `docx:` blocks must be written to the intersection, with format-specific bits
guarded — in R, `knitr::is_latex_output()`.

---

## Objects, one at a time

### YAML front matter

- `title`, `subtitle`, `author`, `date`, `abstract` render on the default PDF title page.
- **`keywords:` does NOT render on the page in the default PDF template.** It reaches the PDF's
  *metadata* and stops there — `pdfinfo` shows `Keywords: …` while the rendered text contains
  nothing. Verified twice: a real manuscript declared six keywords and the string "Keyword" appeared
  nowhere in 104 pages, and a minimal test document reproduced it exactly. If a journal requires
  visible keywords, **write them into the body** next to the JEL/classification line, or supply a
  custom template. **General rule: never assume a YAML field is visible because you declared it.**
  Grep the rendered text, not the source.
- **`date: today` prints the render date.** For anything submitted or versioned, pin the date.
- Add `include-in-header:` / `cite-method:` / `pdf-engine:` only inside the `pdf:` block — they are
  LaTeX-only and error elsewhere.
- YAML is whitespace-significant; an abstract belongs in a `|` block. Check word limits *after*
  writing (`abstract: |` blocks are easy to overshoot).

### Code chunks

Use the `#|` comment-option form, not the legacy brace form:

````
```{r}
#| label: build-panel
#| echo: false
#| cache: true
```
````

- **A chunk label is an identifier, not a description.** It is also what cross-referencing keys off
  (see below), so the prefix is semantically load-bearing.
- Chunks that read an external registry, a CSV, or anything the render is supposed to re-check must
  be **`cache: false`**. A cached chunk replays a stale value after the registry changes, silently.
- Anything stochastic: `set.seed()` once, in an uncached setup chunk.

### Figures

````
```{r}
#| label: fig-event-study
#| fig-cap: "Event study. *Notes:* 95% CI shown."
#| fig-width: 6
#| fig-height: 4
```
````

- To be cross-referenceable the label **must** start with `fig-` **and** the chunk **must** have a
  `fig-cap`. One without the other silently produces no reference.
- Titles go in `fig-cap`, never inside the plot (`ggtitle`/`suptitle`) — otherwise the title prints
  twice. Panel labels inside a multi-panel figure are fine.
- `fig-width: 6.5` matches Word's text width. Don't force `fig-format` — Quarto picks vector for
  PDF and PNG for Word, and overriding breaks one of them.

### Diagrams — Graphviz and Mermaid

**Quarto renders diagrams natively. No R or Python package is involved, and none needs to be
installed.** Two engines ship with it, both written as executable cells:

````
```{dot}
//| fig-width: 4.5
//| fig-height: 1.2
digraph G {
  rankdir=LR;
  node [shape=box, style=rounded, fontname="Helvetica", fontsize=11];
  Site -> Program -> Budget -> DCF;
}
```
````

````
```{mermaid}
%%| fig-width: 4.5
flowchart LR
  A[Thesis] --> B[Market] --> C[Site] --> D[Verdict]
```
````

Mermaid additionally requires `mermaid-format: png` inside the target's block for any
non-HTML format, plus a headless Chrome on the machine. Graphviz requires nothing — it
needs no `dot` binary on `PATH`.

**Tested 2026-09-17, Quarto 1.9.37, `format: beamer`, macOS:** both engines rendered
correctly and the document exited 0. Graphviz rendered in seconds. Mermaid's *first*
render stalled past three minutes bringing Chrome up, then was fast; on a batch build
that cold start is paid once, but it is paid.

#### The failure that matters: diagrams overflow the page silently

**Neither engine sizes its output to the page, and neither warns when it does not fit.**
The same test document, written without `fig-width`, put the last node of the mermaid
flowchart off the right edge and scaled the Graphviz digraph to roughly four times the
slide. Exit code 0, nothing in the log. This is the same silent-drop class as the
overwide table in §Tables, and it is caught the same way: **look at the rendered page.**

**Always declare `fig-width` on a diagram cell.** Treat an undeclared one as a defect, the
way an unlabelled figure chunk is a defect.

#### Diagram output is raster, not vector

Both engines embed a PNG, even in a PDF/Beamer target — measured at 184 ppi for Graphviz
and 383 ppi for mermaid in the test above. Two consequences:

- **The diagram's text is not in the PDF text layer.** `pdftotext` on the rendered page
  returns the slide title and nothing from inside the diagram, so a proofreading pass that
  greps the rendered text will not see a typo in a node label.
- It does not scale like the surrounding type. Acceptable on a projector; visible in a
  printed manuscript figure.

#### Neither engine knows your theme

Mermaid applies its own default palette (lavender fills) regardless of the document's
colors. Graphviz defaults to plain black on white and takes explicit `node [color=...]` /
`fillcolor=` attributes, which makes it the easier of the two to bring into a house style —
but the color still has to be written into the cell, so a hardcoded hex in a deck is the
failure mode to watch for.

#### Choosing between these and TikZ

| Want | Use |
|---|---|
| A pure graph — boxes and arrows where auto-layout beats placing coordinates by hand | `{dot}` |
| Vector output, theme colors by name, text in the PDF text layer, precise placement | TikZ |
| The same, plus review tooling that checks it | TikZ — see the Courses `tikz-*.md` rules |

In `~/Courses/`, TikZ is the pipeline's answer and is governed by three rules
(`tikz-prevention.md`, `tikz-visual-quality.md`, `tikz-measurement.md`); nothing checks a
`{dot}` or `{mermaid}` cell, so its overflow is yours to catch. `{dot}` still earns its
place on a many-node graph, where hand-placing coordinates to satisfy those rules costs
more than it buys.


### Tables

````
```{r}
#| label: tbl-main
#| tbl-cap: "Main results"
```
````

- Same rule: label must start with `tbl-` **and** `tbl-cap` must be present.
- Markdown tables caption *below*: `: Caption {#tbl-label}`.
- **`kableExtra::footnote(escape = FALSE)` strips backslashes.** Hand-escaping and then passing
  `FALSE` is worse than not escaping at all; the symptom is `Missing $ inserted`. Use
  `escape = TRUE` on body and footnote.
- **Consequence of `escape = TRUE`: no markdown in table notes.** `*italic*` prints as literal
  asterisks. If a note needs emphasis, carry it in the wording, not in markup. (Figure captions are
  ordinary markdown paragraphs, so italics *do* work there — the two are not symmetrical.)
- **LaTeX does not error on a table that overruns the right margin — it drops the column.** Set
  column widths from the data, or rotate. Always look at a wide table in the rendered PDF; the
  render log will not tell you a column is missing.
- Long table + `threeparttable` cannot combine; a `longtable`'s note becomes a plain footnote line. <!-- residue:prohibition -->

### Equations and math

**Write mathematics as a math span. Never type the symbol.**

```
inline:    $x \geq y$, $\sigma$, $R = \frac{\text{NOI}}{V}$
displayed: $$ Y_t = \beta_0 + \beta_1 T_t + \varepsilon_t $$ {#eq-its}
```

- The `{#eq-...}` label goes immediately after the closing `$$`, on the same line.
- **A labelled equation nobody references is an orphan.** Quarto still numbers it, so the document
  gains "(1)" with nothing pointing at it. Either reference it with `@eq-its` or drop the label.
- A symbol typed into markdown (`≥`, `σ`, `∑`) is **ordinary text**. Whether it renders depends on
  whether the output font carries that codepoint — and in a LaTeX target it usually does not.
  Measured against `~/Courses/slide_pipeline/_theme/du-beamer.tex` (LuaHBTeX 1.24, 2026-09-05):
  **40 of 67 common math characters render as a missing-glyph box, including every lowercase Greek
  letter.** The render exits 0 and logs nothing — this file's silent-failure pattern in its purest
  form.
- **Do not fix a missing glyph by mapping it in the preamble.** `\newunicodechar{≥}{\ensuremath{\geq}}`
  fixes one character; the next document to type `σ` fails identically. The fix is math mode.
- **A formula is math, not decorated prose.** `**(Value − Exemption) × Rate**` is bold body text
  containing operators: upright, word-spaced, no subscripts. `$$...$$` typesets it as an equation.
- **HTML targets are not a safe harbour.** MathJax/KaTeX render `$...$` there too, so the math span
  is the portable form across every target; a typed glyph depends on the reader's fonts.
- **Currency is not math.** Pandoc will not open a math span when the closing `$` is followed by a
  digit, so `$1,750/mo`, `$/SF` and `$50 to $60` render literally. Escape `\$` only where a lone `$`
  would otherwise pair with another on the same line.
- **The delimiter rules are strict, and breaking one prints the `$` instead of erroring.** Inline
  math opens only when the opening `$` is followed by a non-space, and closes only when the closing
  `$` is preceded by a non-space and is not followed by a digit. Verified by render:

  | Written | Renders |
  |---|---|
  | `$E = mc^2$` | math |
  | `$ E = mc^2$` | **literal** — no space after the opening `$` |
  | `$E = mc^2 $` | **literal** — no space before the closing `$` |
  | `$x_1$2 units` | **literal** — closing `$` cannot precede a digit |
  | `$$ E = mc^2 $$` | display math — spaces **are** allowed inside `$$` |
  | `$$` + blank line + `$$` | **literal** — a blank line ends the block early |

  A blank line *after* a closing `$$` is normal. Keep the equation itself contiguous.

### Cross-references — the highest-value section here

**Never write a cross-reference as plain text.** "See Section 5.4", "Table 3 shows", "as Figure 2
makes clear" are all unchecked strings. Nothing validates them, so they rot the moment a section
moves, and they rot *silently*.

| Target | Label | Reference |
|---|---|---|
| Section | `## Heading {#sec-results}` + `number-sections: true` | `@sec-results` |
| Figure | chunk `label: fig-x` + `fig-cap` | `@fig-x` |
| Table | chunk `label: tbl-x` + `tbl-cap` | `@tbl-x` |
| Equation | `$$…$$ {#eq-x}` | `@eq-x` |
| Listing | `#lst-x` | `@lst-x` |

An unresolved `@ref` renders visibly in the output as `?@sec-does-not-exist` — which is the point:
it is *visible*, where a plain-text number is not. **But the render still exits 0** (verified: a
document with two unresolved references rendered successfully), so nothing stops you shipping it.
The check is therefore yours: `grep '?@'` the rendered text before you ship. Visible-but-non-fatal
is still enormously better than a plain-text "Section 5.4", which leaves no trace at all.

**The known exception, and why it exists.** A project that numbers exhibits manually — because a
frozen registry id *is* the printed number (`Table B1`, `Figure G3`) — must **not** use `fig-`/`tbl-`
chunk labels, because Quarto would add a second, conflicting number beside the manual one. Such a
project uses a different chunk prefix (e.g. `exhibit-`) and builds captions as markdown paragraphs.
That is a deliberate trade: it buys registry-controlled numbering and it gives up automatic
cross-reference checking, so those projects need their own audit that every registry exhibit is
captioned exactly once. **Know which regime you are in before you write a chunk label.**

### Citations

- Pandoc syntax only: `@smith2024` → Smith (2024); `[@smith2024]` → (Smith, 2024);
  `[@smith2024, p. 12]`.
- **Never `\citet{}` / `\citep{}`.** LaTeX-only; prints as raw text in every other format. <!-- residue:prohibition -->
- `cite-method: biblatex` (PDF) **ignores `csl:`**. Word has no biblatex and needs its own `csl:`
  *inside the `docx:` block*. A top-level `csl:` on a dual-format document is a silent no-op for PDF.

### Callouts

```
::: {.callout-important}
Body text.
:::
```

Five types: `note`, `warning`, `important`, `tip`, `caution`. Supported in HTML, PDF, Beamer, DOCX,
Typst, EPUB and revealjs. In a format that doesn't support them they degrade to a bold-titled
blockquote. **Do not invent CSS classes** — they are an HTML/revealjs concept and every LaTeX-family
format drops them silently.

### Columns and layout

```
:::: {.columns}
::: {.column width="50%"}
:::
::::
```

Note the fence widths: the outer `::::` must be longer than the inner `:::`. Equal-length fences
close in the wrong place and the layout collapses without an error.

### Raw HTML and raw LaTeX

- Raw HTML in a PDF/Beamer/Word target: dropped or literal. Don't.
- Raw LaTeX in an HTML or Word target: printed as literal text. Don't.
- If a document has more than one output format, everything format-specific must be guarded.

### Inline computed values

Write every number as an inline expression — `` `r round(x, 2)` `` — never a typed literal. A typed
number does not update when the analysis changes and nothing in the render can detect that it has
gone stale. This is the same failure as a plain-text cross-reference, in a different costume.

---

## The gotchas ledger

Each of these was found in a real document, after it had rendered cleanly for weeks.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | A field declared in YAML never appears | `keywords:` is not rendered by the default PDF template | Put it in the body, or use a custom template. Grep the render. |
| 2 | Two numbers beside one exhibit | Chunk label starts with `fig-`/`tbl-` in a manually-numbered document | Use a neutral prefix; see the exception above |
| 3 | `Missing $ inserted` from a table note | `kableExtra::footnote(escape = FALSE)` strips backslashes | `escape = TRUE` on body *and* footnote |
| 4 | Asterisks print literally in a table note | `escape = TRUE` means no markdown in notes | Carry emphasis in the wording |
| 5 | A table column is missing from the PDF | LaTeX silently drops an overwide column | Set widths from the data; rotate; **look at the page** |
| 6 | A cross-reference points at the wrong section | It was plain text ("Section 5.4") and the structure moved | `{#sec-}` + `@sec-` |
| 7 | A section reference points at a section that does not exist | Same cause, later stage | Same fix; `?@ref` would have failed loudly |
| 8 | An equation is numbered but nothing refers to it | Labelled `{#eq-}`, never referenced | Reference it or drop the label |
| 9 | A stale value reappears after a registry changed | Chunk that reads the registry was cached | `cache: false` on any chunk that re-checks something |
| 10 | Title page date changes every render | `date: today` | Pin the date for anything submitted |
| 11 | Word output has garbled tables | `kableExtra` in a `docx:` target | `flextable` for Word, `kableExtra` for PDF, guarded |
| 12 | Citations render in the wrong style in Word | `csl:` set at top level; PDF's biblatex ignores it, Word never saw it | Put `csl:` inside the `docx:` block |
| 13 | A callout or `<span>` vanishes from a deck | HTML/CSS concept in a Beamer target | Native callouts only; no raw HTML |
| 14 | Layout collapses with no error | `:::` fences not nested by length | Outer fence longer than inner |
| 15 | A math symbol renders as a black box | Typed `≥`/`σ`/`∑` as text; the font has no such glyph | Write it as math — `$\geq$`, `$\sigma$`. Never map it in the preamble |
| 16 | A `$` prints on the page where an equation should be | Space inside the `$…$` delimiters, or a blank line inside `$$` | Close the delimiters up; keep display math contiguous |
| 17 | Half a diagram is off the edge of the page or slide | A `{dot}`/`{mermaid}` cell with no `fig-width`; neither engine fits itself to the page and neither warns | Declare `fig-width` on every diagram cell; **look at the page** |
| 18 | A typo inside a diagram survives a proofreading pass | Diagrams embed as raster PNG, so their labels are not in the PDF text layer | Proofread the diagram source; grepping the rendered text cannot see it |

---

## Pre-render checklist

1. What formats does this render to? Is every format-specific construct guarded?
2. Does every figure chunk have **both** a `fig-`-prefixed label and a `fig-cap`? Tables likewise —
   *unless* this project numbers manually, in which case neither prefix is allowed.
3. Is every cross-reference an `@ref`, not a typed number or section name?
4. Is every number in prose an inline expression?
5. Do any chunks that read external state have `cache: false`?
6. Does every `{dot}` / `{mermaid}` cell declare a `fig-width`?

## Post-render checklist — these only show up in the output

1. `grep '?@' ` the rendered text — unresolved cross-references.
2. Grep for any YAML field you expect to be visible (keywords, subtitle, thanks).
3. Open every wide table and count the columns against the source.
4. Check for doubled exhibit numbers.
5. Grep for literal `*asterisks*`, `\commands`, or `<tags>` that should have rendered.
6. **Look at every diagram on its page.** Overflow is silent, and its labels are raster — no
   grep of the rendered text can find them.

---

## How the claims here were verified

Doc-checked against `quarto.org` (cross-references, callouts, tables, PDF basics) and, where the
docs are silent or the behaviour is what actually bites, confirmed by rendering a minimal test
document. Confirmed empirically, 2026-09-04:

- `keywords:` lands in PDF metadata (`pdfinfo`) and never on the page.
- An unresolved `@ref` prints as `?@name` and the render **still exits 0**.
- A labelled equation that nothing references still consumes a number.
- `@sec-` resolves to "Section N" only with `number-sections: true`.
- Callouts render in the LaTeX/PDF path.

Confirmed empirically, 2026-09-17 (Quarto 1.9.37, `format: beamer`, macOS), by rendering minimal
test documents and inspecting the PDFs with `pdfimages`, `pdftotext` and `pdftoppm`:

- A `{dot}` cell renders with no `dot` binary on `PATH` and no R or Python package installed.
- A `{mermaid}` cell renders in Beamer with `mermaid-format: png`; its first render paid a
  multi-minute headless-Chrome cold start.
- Without `fig-width`, both engines overran the frame — one node clipped off the slide edge, the
  digraph scaled to several times the slide — and the render still **exited 0** with nothing in
  the log. Adding `fig-width` fixed both.
- Both embed a raster PNG in the PDF (184 ppi and 383 ppi respectively); `pdftotext` returned the
  slide title and no text from inside either diagram.

If you find a claim here that is wrong, fix it here — do not work around it in a document.
