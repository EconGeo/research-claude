# Readable code, standard packages first

**The rule (author decision, 2026-10-14).** Every project's code is written so a research
assistant can check it line by line, and every estimator, test and data operation comes from an
established package. Custom code is written only when no package does the job.

Why: hand-written, self-checking estimation code can be correct and still impossible for a human
to audit. An independent rewrite of one paper's main models in plain tidyverse R with package
estimators (`fixest`, `fwildclusterboot`, `Synth`) took a small fraction of the original's lines
and matched every quantity it compared (388 of them, none differing). The rewrite is checkable; the
original was not.

Read this file before writing or reviewing any manuscript chunk, acquisition script or
exploration. coder-critic scores it as category 17 (`.claude/skills/review/templates/code-review-17-categories.md`).

## Where the existing invariants win

This rule sits under `.claude/rules/content-invariants.md`. Where they meet, the invariant holds:

- **INV-14.** The seed is set once, in the `cache: false` setup chunk. A bootstrap or permutation
  never sets its own seed; it states its number of draws (below).
- **INV-15.** Every package is loaded in the setup chunk, including the ones this rule adds.
- **INV-18.** No chunk writes a file, so the package-version record is written from the console,
  never from a chunk (below).
- **INV-19.** No `source()`. A helper that earns its place lives in the setup chunk or the chunk
  that uses it.
- **INV-11.** A number of draws, a tolerance or a package version cited in prose is an inline
  `` `r ` `` expression like any other number.
- The coding standards' prohibited patterns (`sapply()`, `T`/`F`, `==` on floats, `print()`
  for status, growing vectors) still apply, even where the rewrite cited above used them.

## 1. Package first, in this order

1. An established CRAN package (`fixest`, `did`, `rdrobust`, `modelsummary`, `fwildclusterboot`).
2. A maintained GitHub package with no CRAN equivalent, pinned to a commit SHA recorded in the
   version record (§3).
3. Custom code, only when no package does the job. It carries a comment naming why no package
   fits and the formula's source (paper and equation number), and is checked against a toy
   example with a known answer or a published number before any result uses it. The check lives
   in `explorations/`; the comment names it.

Re-implementing a package estimator to "check" it does not belong in the manuscript. If a check
is worth running, it is a one-time replication in `explorations/` (§6).

## 2. Know what the package does by default

- State every option that matters explicitly in the call: clustering, SE type, weights, solver,
  scaling, tolerances (for example `fixef.tol`), bootstrap type and draws. **A reported number
  never depends on a default.**
- Any comment that says how a package behaves is labelled `tested:` (you ran it) or `per docs:`
  (with the help page or vignette named). Anything else is `unverified:` and is not relied on.
- Where the package's method differs from what the strategy memo describes, say so in a comment
  and to the strategist; never let the package silently redefine the estimand.

**The case that shows why.** `Synth::synth` divides every predictor by its standard deviation
across units before weighting (tested: in a replication, equal predictor weights left the post
gap 0.4–0.6 pp away from a least-squares fit to the pre-period path; passing each predictor's
cross-unit variance as `custom.v` undid the scaling and matched to solver precision). The call ran
cleanly and the figure looked right. Only knowing the default caught it.

## 3. Maintained packages, recorded versions

- Prefer actively maintained packages. Do not adopt one archived on CRAN or unmaintained (no
  release or commit in several years, open breaking issues) when a maintained one does the job.
- Record versions in `package_versions.txt` at the project root: R version, then one line per
  package with its version and source (CRAN, or GitHub with the commit SHA). From the console,
  never a chunk (INV-18):

  ```bash
  Rscript .claude/scripts/package_versions.R manuscript_<project>.qmd package_versions.txt
  ```

  Re-run it whenever a package is added or updated, and commit the file. It reads the `library()`
  calls; a package used only through `pkg::` needs its own `library()` line in the setup chunk.
  A project that already uses `renv` keeps `renv.lock` instead. Python acquisition records
  `requirements.txt` with pinned versions.
- A package update that moves a reported number is a model change (`.claude/rules/agents.md`
  §6): re-render, compare, and report the difference.

## 4. Written for a research assistant

- Tidyverse-style pipelines (`dplyr`, `tidyr`, native `|>`) for wrangling. `data.table` only
  where size demands it (reading a file of a gigabyte or more), with a comment saying so.
- Descriptive, source-identifying names (`sales_closed`, not `d2`). Never assign a base or builtin
  name at top level (`data`, `df`, `c`, `t`, `T`, `F`, `list`, `table`, `mean`, `sum`, `file`,
  `str`, `base`): package code can find a global value by that name. A `for` loop is not a scope;
  short names belong inside a function, `local({})` or a pipe.
- One model or one exhibit per chunk. Short chunks; a chunk past roughly 80 lines is split.
- The model formula is visible in full where it is fit (or assembled from named pieces in the
  same chunk), not hidden in a helper three calls away.
- Comments are written for the RA and say *why*: which sample rule, which paper equation, why
  this option. They do not narrate what the next line does.
- No deep helper layers. Write a function only when it is used at least 3 times or isolates
  genuinely custom math, and never a helper that calls another of your own helpers to fit a
  model.
- Read results through accessors (`coef()`, `se()`, `pvalue()`, `nobs()`, `broom::tidy()`),
  never by position inside a fitted object's internals.
- Never wrap an estimator call in `suppressWarnings()`. A convergence or collinearity warning
  is read and dealt with.

## 5. Checks stay, but plain

Before a result is used: a few `stopifnot()` lines, each with a message, on sample sizes, merge
keys (unique where they must be, no rows lost unexpectedly) and the invariants the design needs.

```r
stopifnot("one row per unit" = !anyDuplicated(exposure_by_unit$unit_id),
          "sample lost rows in the join" = nrow(sample_joined) == nrow(sample_cohort))
```

No guard machinery beyond that: no in-chunk re-derivations of a package's own output, no
size tests run inside the manuscript, no hand-written bootstraps to check a package's bootstrap,
and no code that polices prose wording. Prose is checked by `prose_number_check.py` and nothing
else.

## 6. Porting or rewriting earlier code

When code is ported or rewritten, the new results are matched to the old within tolerances
stated before the comparison runs:

| Quantity | Tolerance |
|---|---|
| Coefficients and SEs from the same package on the same data | relative 1e-6 |
| Counts (observations, clusters, units) | exact |
| Bootstrap and permutation p-values | Monte Carlo error at the stated number of draws |
| Optimisation output (weights, fitted paths) | the solver's tolerance, stated |

The comparison is a table, one row per quantity, with a PASS/DIFFERS status, kept in
`explorations/`. **A difference is a finding to report, never tuned away**: never loosen a
tolerance, change a specification or drop a row to make it pass. Explain it or escalate it.

## 7. Bootstraps and permutations

The seed is set once (INV-14). The number of draws is stated in the call (`B = 9999`), held in a
named constant when used more than once, and reported in the table or figure note.

## 8. Python and Julia

The same principle. Python is mainly for acquisition (`scripts/acquire/`): `requests`, `pandas`,
`pyarrow`. Where Python estimates anything, use `statsmodels`, `linearmodels` or `pyfixest`
before writing custom code. Julia: `FixedEffectModels`, `GLM`, `WildBootTests`. Versions are
pinned in the language's own lock or requirements file.
