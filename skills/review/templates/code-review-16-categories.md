# Code Review: 16 Check Categories

Extracted from `coder-critic.md`. Used by the coder-critic agent for code review.

---

## Prerequisite Checks

**Before running categories:**

- Read `.claude/rules/content-invariants.md` -- enforce INV-11, INV-13 through INV-19, INV-23, INV-24. Cite invariant numbers (e.g., "violates INV-16") in report alongside deductions.
- Identify the paper type (reduced-form, structural, theory+empirics, descriptive) from the strategy memo or the code itself. This determines which checks apply.

---

## Strategic Alignment (Categories 1-4)

### 1. Code-Strategy Alignment
- Does the code implement EXACTLY what the strategy memo specifies?
- Same estimator? Same fixed effects? Same clustering? Same sample restrictions?
- Any silent deviations?

### 2. Paper-to-Code Naming Map
- Does a naming map exist (in the `setup` chunk comment block)?
- Do code variable names match the paper notation consistently?
- Are all key parameters traceable from paper equation to code variable?

### 3. Sanity Checks

**Reduced-form:**
- **Sign:** Does the direction of the effect make economic sense?
- **Magnitude:** Is the effect size plausible? (Compare to literature)
- **Dynamics:** Do event study plots look reasonable?
- **Balance:** Are treatment and control groups comparable?
- **First stage:** Is the F-stat strong enough? (for IV)
- **Sample size:** Did you lose too many observations in cleaning?

**Structural:**
- **Parameter values:** Are estimated parameters in plausible ranges from the literature?
- **Model fit:** Does the model reproduce data moments not used in estimation?
- **Convergence:** Did the optimizer converge? Multiple starting values tried?
- **Counterfactual magnitudes:** Are simulated policy effects plausible?

**Theory + empirics:**
- **Test results coherent?** Do findings tell a consistent story across predictions?
- **Effect magnitudes:** Are they consistent with what the model predicts?

**Descriptive:**
- **Magnitudes meaningful?** Are documented patterns large enough to matter?
- **Construction choices defensible?** Would alternatives change the key facts?

### 4. Robustness
- Did the Coder implement ALL robustness checks from the strategy memo?
- Results stable across specifications?
- Suspicious patterns? (results only work with one bandwidth/sample/period)

---

## Code Quality (Categories 5-16)

### 5. Manuscript Layout
- One `setup` chunk, `cache: false`, first; `execute: cache: true` in YAML?
- Every chunk labelled; labels follow `build-*`, `estimate-*`, `robustness-*`, `tbl-*`, `fig-*`?
- The dependency DAG documented in the setup chunk matches the `dependson` links?

### 6. Chunk Headers
- Wrangling chunks carry `cache.extra` on every raw file; estimation/table/figure chunks carry `dependson`?
- Every raw file read has a manifest row (INV-24)?

### 7. Console Output Hygiene
- No `cat()`, `print()`, `sprintf()` for status -- use `message()`
- No ASCII banners or decorative output
- No `rm(list = ls())` at top

### 8. Reproducibility
- Single `set.seed()` at top, seed defined in the `setup` chunk
- `library()` not `require()`
- Relative paths only via `here()` -- no `setwd()`, no absolute paths
- For parallel bootstrap: `future.seed = TRUE` or `RNGkind("L'Ecuyer-CMRG")`

### 9. Numerical Discipline
**This category is critical.**
- **Float comparison:** Never `==` on floats. Uses `all.equal()` or tolerance?
- **CDF values:** Clamped to `[0, 1]` after computation?
- **Inverse link guards:** Protected against `qnorm(0)`, `qnorm(1)`, `log(0)`?
- **Integer literals:** Uses `1L`, `0L` in R? `seq_len(n)` not `1:n`?
- **Pre-allocation:** Matrices/vectors pre-allocated before loops? No growing lists in loops?
- **NaN/Inf checks:** Results checked for `NA`, `NaN`, `Inf` after numerical operations?

### 10. Function Design
- `snake_case` naming, verb-noun pattern (`estimate_att`, `test_oir`, `compute_weights`)
- Roxygen-style docs for non-trivial functions
- Default parameters, no magic numbers
- `stopifnot()` preconditions at function top
- Named list return values (not positional)
- No `<<-` global assignment

### 11. Figure Quality
- `fig-` label, `fig-cap` present (INV-2); no title inside the plot (INV-12)
- `fig-width`/`fig-height` set; serif family for paper figures; consistent theme
- No `ggsave()`, no `fig-format` override <!-- residue:prohibition -->

### 12. Table Quality
- `tbl-` label, `tbl-cap`, `booktabs = TRUE`, notes (INV-1, INV-3)
- Human-readable labels; stars per journal profile (INV-4); SE labelled in notes
- `output = "kableExtra"` for PDF, `"flextable"` for Word — never both in one chunk

### 13. Cache and Freshness
- Setup chunk `cache: false`; every other chunk `cache: true`
- `cache.extra` uses `file.mtime()`; no chunk writes to disk (`saveRDS`, `write_csv` outside `scripts/acquire/`) <!-- residue:prohibition -->
- **Stale cache after a raw-file change = HIGH severity**

### 14. Comment Quality
- Comments explain WHY, not WHAT
- Paper equation references where implementing specific formulas
- No dead code (commented-out blocks)

### 15. Error Handling
- `stopifnot()` for preconditions
- `stop()` with informative messages for business-logic errors
- Never silently return `NULL` or `NA` on failure
- Simulation results checked for NA/NaN/Inf
- Failed reps counted and reported
- Parallel backend registered AND cleaned up (`on.exit()`)

### 16. Prohibited Patterns

| Pattern | Severity | Reason |
|---------|----------|--------|
| `setwd()` | HIGH | Use `here()` |
| Hardcoded absolute paths | HIGH | Breaks portability |
| `rm(list = ls())` | MEDIUM | Restart R instead |
| `T` / `F` for booleans | MEDIUM | Can be overwritten |
| `sapply()` | MEDIUM | Unpredictable return type |
| `attach()` / `detach()` | MEDIUM | Namespace ambiguity |
| `<<-` | MEDIUM | Global side effects |
| `library()` inside functions | LOW | Load at script top |
| `1:n` instead of `seq_len(n)` | LOW | Breaks when `n == 0` |

---

## Data Cleaning (Stage 0)

- Merge rates documented? (< 80% = flag)
- Sample drops explained with counts?
- Missing data handling documented?
- Variable construction matches strategy memo definitions?

---

## Paper-Type-Specific Checks

### Structural Code
- Optimization uses multiple starting values?
- Convergence reported (gradient norm, iterations, exit code)?
- Log-likelihood / moment function returns correct dimensions?
- Counterfactual simulation re-solves the model (not just changing one variable)?
- Welfare computation documented and correct?
- Parameter standard errors computed correctly for the estimation method?

### Simulation / Monte Carlo Code
- DGP function is standalone (takes seed, returns data)?
- Seeds pre-generated and documented?
- Simulation parameters defined as named constants, not scattered?
- Coverage, bias, RMSE computed and reported correctly?
- Parallel seeds handled properly (`future.seed`, `L'Ecuyer-CMRG`)?

---

## Standalone Mode

When invoked via `/review --code <file under scripts/acquire/ or explorations/>`, run categories **5-16 only** (code quality + numerical discipline). No strategy memo comparison -- just code quality and best practices.

---

## Report Format

```markdown
# Code Audit -- [Project Name]
**Date:** [YYYY-MM-DD]
**Reviewer:** coder-critic
**Paper type:** [Reduced-form / Structural / Theory+Empirics / Descriptive]
**Score:** [XX/100]
**Mode:** [Full / Standalone (code quality only)]

## Code-Strategy Alignment: [MATCH/DEVIATION]
## Paper-to-Code Map: [PRESENT/MISSING]
## Sanity Checks: [PASS/CONCERNS/FAIL]
## Numerical Discipline: [PASS/CONCERNS/FAIL]
## Robustness: [Complete/Incomplete]

## Code Quality (12 categories)
| Category | Status | Issues |
|----------|--------|--------|
| Manuscript layout | OK/WARN/FAIL | [details] |
| Chunk headers | OK/WARN/FAIL | [details] |
| Console output | OK/WARN/FAIL | [details] |
| Reproducibility | OK/WARN/FAIL | [details] |
| Numerical discipline | OK/WARN/FAIL | [details] |
| Function design | OK/WARN/FAIL | [details] |
| Figure quality | OK/WARN/FAIL | [details] |
| Table quality | OK/WARN/FAIL | [details] |
| Cache and freshness | OK/WARN/FAIL | [details] |
| Comment quality | OK/WARN/FAIL | [details] |
| Error handling | OK/WARN/FAIL | [details] |
| Prohibited patterns | OK/WARN/FAIL | [details] |

## Score Breakdown
- Starting: 100
- [Deductions]
- **Final: XX/100**

## Escalation Status: [None / Strike N of 3]
```
