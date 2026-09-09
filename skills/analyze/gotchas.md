# Analyze Skill -- Gotchas

Known failure points and edge cases for data analysis.

## R Packages

- `modelsummary` silently drops coefficients when `coef_rename` keys don't match variable names exactly. Always check output dimensions against model object.
- Clustering syntax differs between `fixest` and `lm` -- always use `fixest::feols()` for cluster-robust standard errors.
- R's `haven::read_dta()` preserves Stata value labels as attributes -- use `as_factor()` explicitly or they'll be invisible numeric codes.
- `did::att_gt()` requires the group variable to be the year of first treatment (0 for never-treated). Miscoding this produces silent wrong results.
- `rdrobust` returns an object where `$coef` is a matrix, not a vector. Access the point estimate with `$coef[1]` or `$Estimate[1]`.

## Data Handling

- Pre-Code Report blocks on strategic alignment if strategy memo doesn't exist. Run `/strategize` first, or proceed with user description and flag the gap.
- Nothing is saved to disk; chunks cache. A `saveRDS()` in a chunk is a coder-critic deduction. <!-- residue:prohibition -->
- `here()` resolves from `.here` file or `.Rproj` file -- make sure one exists at project root.
- Never use `setwd()` -- it breaks reproducibility across machines (INV-19).
- When merging datasets, always check merge rates. A 60% merge rate is a red flag. Document non-merges.

## Numerical Issues

- Never compare floats with `==`. Use `all.equal()` or tolerance: `abs(a - b) < 1e-10`.
- `qnorm(0)` returns `-Inf` and `qnorm(1)` returns `Inf`. Guard inverse link functions with `pmin(pmax(p, eps), 1 - eps)`.
- `1:n` when `n == 0` produces `c(1, 0)`. Use `seq_len(n)` instead.
- `sapply()` returns a list when lengths differ and a matrix when they match. Use `vapply()` for type safety.

## Output

- Figures: no in-plot titles (INV-12) — titles go in `#| fig-cap:`.
- Tables: `tbl-` chunks with `booktabs = TRUE` and notes (INV-1, INV-3).
- Quarto picks the figure format per output; never set `fig-format`.

## Cross-language replication (`/review --replicate`)

- R and Python handle NA differently in groupby/aggregate operations. Explicit `na.rm = TRUE` in R; `dropna()` in pandas.
- Factor ordering in R defaults to alphabetical; pandas categoricals preserve insertion order. This affects dummy variable encoding.
- `fixest` and `pyfixest` may differ slightly in cluster-robust SEs due to small-sample corrections.
- Sample sizes must match exactly across languages. Any difference is a data handling bug.
