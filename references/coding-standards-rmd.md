# Coding Standards: R Markdown

These standards apply to code chunks in `manuscript.Rmd`.
They extend `coding-standards-r.md` — all R standards still apply inside chunks.
The rmd-coder-critic enforces these rules.

---

## 1. Setup Chunk (Required)

Every `manuscript.Rmd` must begin with a setup chunk immediately after the YAML:

```r
knitr::opts_chunk$set(
  echo    = FALSE,
  message = FALSE,
  warning = FALSE,
  cache   = FALSE
)
library(here)
library(data.table)
library(fixest)
library(modelsummary)
library(kableExtra)
library(ggplot2)

set.seed(42L)
```

Rules:
- `include=FALSE` on the setup chunk — setup chunk output never shown
- `echo = FALSE` globally — no code in the output paper
- `message = FALSE, warning = FALSE` globally — no R messages in the paper
- `cache = FALSE` globally — override per-chunk only for provably expensive operations
- All packages loaded here, never inside analysis chunks
- `set.seed()` called once here, not inside individual chunks

---

## 2. Chunk Naming Conventions

| Type | Prefix | Example |
|------|--------|---------|
| Figure | `fig-` | `fig-event-study` |
| Table | `tab-` | `tab-main-results` |
| Data prep (hidden) | `data-` | `data-load-panel` |
| Analysis (hidden) | `run-` | `run-main-regression` |
| Setup | always `setup` | `setup` |

- Use kebab-case labels, not underscores
- No spaces in chunk labels
- Labels must be unique across the entire document

---

## 3. Hidden Analysis Chunks

Run computations in hidden chunks before display chunks:

```r
# Run expensive estimation and cache it
# {r run-main-regression, cache=TRUE}
m1 <- feols(outcome ~ treatment | unit_id + year,
            data = dt,
            cluster = ~property_id)
m2 <- feols(outcome ~ treatment + controls | unit_id + year,
            data = dt,
            cluster = ~property_id)
```

```r
# Display table — never cache display chunks
# {r tab-main-results}
modelsummary(
  list("(1)" = m1, "(2)" = m2),
  output   = "kableExtra",
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  title    = "Main Results",
  notes    = "Clustered standard errors at property level in parentheses.",
  escape   = FALSE
) |> kable_styling(latex_options = "hold_position")
```

- Separate computation (`run-*`) from display (`tab-*`, `fig-*`)
- Cache `run-*` chunks when they take > 5 seconds
- Display chunks should never be cached (fast; cache-invalidation bugs are hard to spot)

---

## 4. Data Loading Pattern

Load cleaned data from `data/cleaned/` at the top of the document, not inline:

```r
# {r data-load, cache=FALSE}
dt <- readRDS(here("data", "cleaned", "main_panel.rds"))
```

**Do NOT** run data preparation inside `manuscript.Rmd`. Data prep lives in `scripts/R/`:

```
scripts/R/
  01_data_preparation.R   # produces data/cleaned/main_panel.rds
  02_data_descriptive.R   # optional separate descriptive prep
```

Run `01_data_preparation.R` once before knitting. The Rmd only loads cleaned outputs.

---

## 5. Table Output Standards

### Regression Tables: `modelsummary`

```r
modelsummary(
  models,
  output   = "kableExtra",    # NOT "latex_tabular" — Rmd wraps the float
  booktabs = TRUE,             # Required (INV-23)
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  coef_rename = c(
    "treatment"  = "Treatment",
    "log_income" = "Log income"
  ),
  gof_map  = c("nobs", "r.squared", "adj.r.squared"),
  title    = "Effect of X on Y",
  notes    = "Notes: ...",     # Required (INV-23)
  escape   = FALSE
) |> kable_styling(latex_options = "hold_position")
```

### Summary / Descriptive Tables: `kableExtra`

```r
kbl(
  df,
  format   = "latex",
  booktabs = TRUE,
  digits   = 3,
  caption  = "Summary Statistics",
  escape   = FALSE
) |>
  kable_styling(latex_options = "hold_position") |>
  add_footnote(
    "Notes: Sample restricted to ...",
    notation = "none"
  )
```

### Key Differences from Standalone Pipeline

| Standalone R scripts | Rmd chunks |
|---------------------|-----------|
| `output = "latex_tabular"` | `output = "kableExtra"` |
| File exported to `paper/tables/` | Renders inline in document |
| `\begin{table}` wrapper in `main.tex` | bookdown creates the float |
| Caption in `main.tex` | `title = "..."` argument |

---

## 6. Figure Output Standards

```r
# {r fig-event-study, fig.cap="Event Study: Effect of Treatment on Outcome. \\textit{Notes:} 95\\% CIs shown. N = 10,000 properties.", fig.width=6, fig.height=4, dev="pdf"}
ggplot(event_dt, aes(x = year_rel, y = coef, ymin = ci_lo, ymax = ci_hi)) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
  geom_pointrange() +
  scale_x_continuous(breaks = min(event_dt$year_rel):max(event_dt$year_rel)) +
  labs(x = "Years Relative to Treatment", y = "Coefficient") +
  theme_minimal(base_family = "serif") +
  theme(panel.grid.minor = element_blank())
# No labs(title = ...) — caption goes in fig.cap (INV-24)
```

Rules:
- `dev = "pdf"` for vector output (PDF target); bookdown sets this automatically for PDF
- `fig.width` and `fig.height` in inches
- `fig.cap` contains the full caption including notes
- Escape LaTeX in `fig.cap` with double backslash: `\\textit{}`, `\\%`
- Colorblind-friendly palette; color + shape/linetype together

---

## 7. Caching Rules

```r
# Cache expensive operations; never cache display chunks
# {r run-bootstrap, cache=TRUE, cache.extra=digest::digest(dt)}
boot_results <- future_lapply(seq_len(N_BOOT), \(b) { ... }, future.seed = TRUE)
```

- `cache = TRUE` only on computation chunks taking > 5 seconds
- Add `cache.extra = digest::digest(dt)` to invalidate cache when data changes
- NEVER cache: data loading, table display, figure display chunks
- After adding new data or changing a `run-*` chunk, delete `*_cache/` and re-knit

---

## 8. Prohibited Patterns (Rmd-Specific)

| Pattern | Reason | Replacement |
|---------|--------|-------------|
| `echo = TRUE` in production | Code appears in paper | `echo = FALSE` globally |
| `output = "latex_tabular"` in chunks | Creates raw LaTeX, breaks Word output | `output = "kableExtra"` |
| `setwd()` anywhere | Breaks `here()` | Never use |
| Inline `install.packages()` | Breaks reproducibility | `renv` |
| `\citet{}` / `\citep{}` in prose | LaTeX-only commands | `@key` / `[@key]` |
| `\section{}` in prose | LaTeX-only commands | `#` headings |
| `labs(title = ...)` in ggplot | Adds title inside figure (INV-24) | Put in `fig.cap` |
| Hardcoded "Figure 1" / "Table 3" | Breaks when order changes | `\@ref(fig:label)` |
| Chunk label with underscore | bookdown label issue | Use kebab-case |
| Duplicate chunk labels | Knit error | Unique labels required |
