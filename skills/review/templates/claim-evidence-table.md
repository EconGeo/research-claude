# Claim–Evidence Table

Produced by the writer-critic at every review; saved to
`quality_reports/reviews/claim_evidence_<project>_<date>.md`. It replaces the retired
hand-maintained claim-source map: the table is built *from the manuscript* by the critic,
not maintained by the writer. INV-11 stays mechanical (`prose_number_check.py`); this table
is the interpretation check.

| # | Claim (quoted sentence) | Section | Kind | Evidence (chunk label / object / `@tbl-` / `@fig-` / `@key`) | Verdict | Deduction |
|---|---|---|---|---|---|---|
| 1 | "The effect is `r round(beta_hat, 3)` log points" | Results | numeric | `estimate-main` → `beta_hat`; `@tbl-main` col 1 | SUPPORTED | 0 |
| 2 | "Effects are concentrated in supply-constrained markets" | Results | qualitative | `@tbl-heterogeneity` — interaction not significant | OVERSTATED | -10 |

**Kinds:** numeric (a number or comparison of numbers) · qualitative (direction, mechanism, heterogeneity, comparison to literature) · citation (attributes a finding to a paper).

**Verdicts and deductions** (spec §7): CONTRADICTED −25 (evidence shows the opposite) · UNSUPPORTED −15 (no evidence in the manuscript) · OVERSTATED −10 (evidence is weaker than the claim) · UNVERIFIABLE −5 (cannot be traced to a chunk, table, figure or key) · SUPPORTED 0.

Every sentence in Results and Conclusion that asserts something about the world gets a row. Abstract and Introduction claims that restate a result get a row pointing at the Results row.
