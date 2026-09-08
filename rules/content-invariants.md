# Content Invariants

These are non-negotiable. Every agent checks against them. Violations are deductions,
not suggestions. Critics cite invariant numbers (e.g., "violates INV-3") in their reports.

**Every invariant names what enforces it.** The spec's own lesson from this pipeline:
*a rule with no executable check is a suggestion.* Where the enforcement column says
`reviewer-judgment`, that is a deliberate admission, not an oversight — nobody should
assume a script is quietly catching it.

---

## Paper

**INV-1.** Every table has notes explaining key variables, sample, and data source —
via `modelsummary(notes = ...)` / `kbl() |> add_footnote()` for PDF, or an italic
paragraph or `custom-style="Footnote Text"` div after the chunk for Word.

**INV-2.** Every figure has a `#| fig-cap:` explaining what is shown, how to read it,
and the data source.

**INV-3.** Booktabs three-line rules only. No `\hline`, no vertical rules.

**INV-4.** Significance stars follow the journal profile. AEA journals: no stars,
report standard errors and use confidence intervals. Default: stars with a note
defining the thresholds.

**INV-5.** Abstract is 150 words or fewer.

**INV-6.** JEL codes and keywords present after the abstract.

**INV-7.** Notation is consistent across all sections — the same symbol means the
same thing everywhere. Different concepts get different symbols.

**INV-8.** Every causal claim has a corresponding identification section. No causal
language in descriptive papers.

**INV-9.** Citations are pandoc `@key` syntax against the `bibliography:` field, with
a `csl:`. For PDF output, `cite-method: biblatex`. Never raw `\citet{}` / `\citep{}`
in prose — it renders as literal text in Word.

**INV-10.** Any custom LaTeX preamble supplied via `include-in-header:` loads
`hyperref` second-to-last and `cleveref` immediately after it. Applies only when the
project supplies a preamble; Quarto's default needs no intervention.

**INV-11.** **Every number in prose is an inline `` `r ` `` expression evaluated
against a live object. Never a typed literal.** This is the load-bearing one. A
hardcoded value survives a clean render, survives review, and is how a paper ends up
describing a coefficient as significant beside a table showing p = 0.759.

**INV-12.** No titles inside ggplot/matplotlib figures. Titles go in `#| fig-cap:`.
Panel labels ("Panel A: …") inside multi-panel figures are fine.

**INV-13.** Tables and figures are produced by labelled chunks inside
`manuscript_<project>.qmd` — `tbl-` prefix for tables, `fig-` for figures. Nothing is
written to a file and included by hand; there is no `paper/tables/` or
`paper/figures/`.

## Code

**INV-14.** `set.seed()` (or language equivalent) called exactly once, in the
`cache: false` setup chunk, if any stochastic element exists.

**INV-15.** All packages/libraries loaded in the setup chunk, before any data loading
or computation.

**INV-16.** No absolute paths. All paths relative to project root via `here()` (R),
`pathlib.Path` (Python), or `joinpath(@__DIR__, ...)` (Julia).

**INV-17.** No growing vectors/lists in loops. Pre-allocate result containers or use
vectorized operations.

**INV-18.** Output files go to the path specified by the Output Organization setting
in `CLAUDE.md`.

**INV-19.** No prohibited functions: `setwd()` / `os.chdir()` / `cd()`,
`rm(list = ls())`, `install.packages()` in scripts, `attach()` / `detach()`.
No `source()` inside any chunk.

## Data

**INV-23.** Raw data is ingested directly. No derived or intermediate file is written
into `data/raw/` — cleaning lives in cached chunks reading the true raw files.

**INV-24.** Every external file a chunk reads has a row in `data/raw/data_manifest.md`.

## Talk

**INV-20.** Notation in the talk matches the paper exactly — same symbols, same
subscripts, same definitions.

**INV-21.** Every claim on a slide is traceable to the paper. No orphan results or
numbers that do not appear in the manuscript.

## Traceability

**INV-22.** *RETIRED 2026-09-08.* Formerly required a hand-maintained claim-source map
at `quality_reports/claim_source_map_{project}.md`. Superseded by INV-11 plus
`prose_number_check.py`, which enforce the same property mechanically. The number is
kept rather than reused so older reports and reviews still resolve.

---

## What enforces each invariant

| Invariant | Enforced by |
|---|---|
| INV-11 | `python3 prose_number_check.py .` — exit 0 required |
| INV-14, INV-15, INV-16, INV-19 | lint hook + `verifier` |
| INV-23, INV-24 | `coder-critic` Correctness Layer, against `data/raw/data_manifest.md` |
| INV-9, INV-13 | `quarto render` fails or degrades visibly |
| INV-1..INV-8, INV-10, INV-12, INV-17, INV-18, INV-20..INV-21 | `reviewer-judgment` — no script checks these |

**`quarto render` exiting 0 enforces nothing about literals.** It proves every inline
expression *evaluated*. Treating a clean render as proof of numerical consistency is
the specific false assumption this pipeline was rebuilt to remove.

---

## How Agents Use This File

| Agent | Checks | Action on Violation |
|-------|--------|-------------------|
| **writer-critic** | INV-1 through INV-13 | Deduct per scoring rubric |
| **coder-critic** | INV-11, INV-13 through INV-19, INV-23, INV-24 | Deduct per scoring rubric |
| **storyteller-critic** | INV-20, INV-21 | Deduct per scoring rubric |
| **verifier** | INV-9, INV-11, INV-14, INV-15, INV-16, INV-19, INV-24 | FAIL if present |
| **lint hook** | INV-14, INV-15, INV-16, INV-19 | Advisory warning |
