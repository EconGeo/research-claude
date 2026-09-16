# Cross-Language Replication — Comparison Tolerances

Read at the comparison step of `/review --replicate [language]`, after the coder has
re-implemented the estimation chunks.

---

## Tolerances

| Quantity | Tolerance |
|---|---|
| Point estimates | relative 1e-6, absolute 1e-10 |
| Standard errors | relative 1e-4 |
| p-values | relative 0.01 — significance boundaries 0.10 / 0.05 / 0.01 are flagged regardless of tolerance |
| Sample sizes | must match exactly |

## Common divergence sources

Check these before reporting a genuine replication failure:

- BFGS vs L-BFGS optimizer defaults
- Floating-point handling in fixed-effects absorption
- Clustering variance estimation — small-sample corrections differ by package
- Random seed implementations across languages
- NA/NaN handling defaults (`na.rm` vs `dropna`)
- Factor / categorical variable ordering
