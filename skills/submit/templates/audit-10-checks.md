# Verifier Submission-Mode Audit: 10 Checks

The verifier runs in two modes. Standard mode (checks 1-4) runs between phase transitions. Submission mode (checks 1-10) runs before journal submission. All checks are pass/fail.

## Standard Checks (Always Run)

### 1. Manuscript renders
- Run: `quarto render manuscript_<project>.qmd`
- Pass: exit 0, output artifact newer than the source `.qmd`
- No `ERROR` or `WARNING` in the render log
- No undefined citations, no unresolved cross-references (`?@fig-`, `?@tbl-`)
- A clean render is **not** proof the prose numbers are right — that is check 4b
  below, `prose_number_check.py` (INV-11)

### 2. Chunks execute
- Every chunk ran (no `eval: false` on an estimation chunk)
- No cached chunk older than its `cache.extra` files

### 3. File Integrity
- Every `read_csv(here(...))` / `readRDS(here(...))` path in a chunk resolves
- Every file a chunk reads has a row in `data/raw/data_manifest.md` (INV-23/24)
- Every `@tbl-` and `@fig-` reference resolves to a labelled chunk in the manuscript

### 4. Output Freshness
- The render post-dates the newest input: no chunk cache older than the data it reads
- `cache.extra` is set on every chunk reading an external file, so a changed input
  actually invalidates the cache rather than silently serving a stale result
- No stale rendered artifact (output older than the `.qmd`)

### 4b. Prose numbers are computed, not typed
- Run: `python3 .claude/scripts/prose_number_check.py manuscript_<project>.qmd`
- Pass: exit 0. Every numeric claim in prose is an inline `` `r ` `` expression
  bound to a live object (INV-11)
- This is the check `quarto render` cannot make: a render exiting 0 proves every
  expression *evaluated*, and says nothing about a literal someone typed

## Submission Checks (Additional)

### 5. Package Inventory
- Every acquisition script in `scripts/acquire/` is present and numbered sequentially
- No analysis code outside the manuscript — analysis lives in cached `.qmd` chunks,
  not in `scripts/R/` (a stray analysis script is an orphan by construction) <!-- residue:prohibition -->
- No `source()` call inside any chunk

### 6. Dependency Verification
- R: `renv.lock` or `sessionInfo()` output exists
- Python: `requirements.txt` or `pyproject.toml` exists
- Non-standard packages documented with install instructions

### 7. Data Provenance
- Every dataset has a documented source
- Access instructions for restricted data
- No hardcoded paths
- Data availability statement present

### 8. Execution Verification
- Run `quarto render` from a cold cache; report runtime
- Capture all output and errors

### 9. Output Cross-Reference
- Every table and figure traced to a `tbl-`/`fig-` chunk
- No orphan outputs (generated but not referenced)
- No missing outputs (referenced but not generated)

### 10. README Completeness (AEA Format)
- Data availability statement
- Computational requirements (software, packages, hardware, runtime)
- Description of programs (numbered, with inputs/outputs)
- Instructions for replication
- List of tables and figures with generating chunk labels

## Content Invariants Checked

The verifier also enforces these invariants (any violation is FAIL):
- INV-9: pandoc `@key` citations; `cite-method: biblatex` on the PDF path; no top-level `csl:`
- INV-10: when a preamble is supplied, hyperref second-to-last, cleveref after
- INV-14: `set.seed()` once, in the setup chunk
- INV-15: All packages loaded at top
- INV-16: No absolute paths
- INV-19: No prohibited functions (`setwd()`, `rm(list = ls())`, `install.packages()`, `attach()`)

## Scoring

Pass/fail per check. Binary for aggregation: 0 (any failure) or 100 (all pass). Contributes 5% to weighted overall score.
