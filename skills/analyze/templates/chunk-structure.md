# Chunk Structure — the five chunk patterns of the one manuscript

Every analysis chunk lives in the declared manuscript. There is no script scaffold. The
patterns below are the only shapes the coder and data-engineer write; the coder-critic deducts
per `.claude/rules/quarto-empirical.md` ("What the Coder-Critic Checks") when a chunk departs
from them.

## 1. Setup chunk — `cache: false`, once, first

```{r}
#| label: setup
#| cache: false
#| include: false
library(here); library(tidyverse); library(fixest); library(modelsummary); library(kableExtra)
set.seed(20240101L)                 # exactly once, here (INV-14)

# Paper-to-code naming map (established in the Pre-Code Report; never invented mid-chunk)
#   Y_it     -> outcome        (data/raw/<file>.csv: <column>)
#   D_it     -> treated        (constructed in build-panel)
#   alpha_i  -> unit FE        (absorbed)
#   gamma_t  -> year FE        (absorbed)
# Dependency chain (the full DAG, every link explicit):
#   build-panel -> estimate-main -> tbl-main
#                                -> fig-event-study
#               -> robustness-alt-clusters -> tbl-robustness
```

Helper functions used by more than one chunk are defined **here**, in the setup chunk, not in a
`functions/` directory and never `source()`d (INV-19, −10).

## 2. Wrangling chunk — `cache.extra` on every raw file it reads

```{r}
#| label: build-panel
#| cache: true
#| cache.extra: !expr list(file.mtime(here("data/raw/permits.csv")), file.mtime(here("data/raw/units.csv")))
panel <- read_csv(here("data/raw/permits.csv"), show_col_types = FALSE) |>
  left_join(read_csv(here("data/raw/units.csv"), show_col_types = FALSE), by = "unit") |>
  filter(year >= 2000) |>
  mutate(log_permits = log1p(permits))
n_units <- n_distinct(panel$unit)
```

Every file read here has a row in `data/raw/data_manifest.md` (INV-24). Sample drops are
documented with counts in a comment. Nothing is written back to disk: no `.rds`, no cleaned
CSV in `data/raw/` (INV-23).

## 3. Estimation chunk — `dependson` on its data source

```{r}
#| label: estimate-main
#| cache: true
#| dependson: "build-panel"
m_main <- feols(log_permits ~ treated | unit + year, data = panel, cluster = ~unit)
beta_hat <- coef(m_main)[["treated"]]; se_hat <- se(m_main)[["treated"]]
```

Robustness chunks follow the same shape with their own label (`robustness-<what>`) and
`dependson`. Objects the prose cites (`beta_hat`, `n_units`) are named here so the inline
expressions read like the paper.

## 4. Table chunk — `tbl-` label, `tbl-cap`, `booktabs = TRUE`, notes

```{r}
#| label: tbl-main
#| cache: true
#| dependson: "estimate-main"
#| tbl-cap: "Effect of Treatment on Log Permits"
modelsummary(
  list("Baseline" = m_main),
  output   = "kableExtra",            # PDF; Word uses output = "flextable" (quarto-word.md)
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),   # FALSE for AEA journals (INV-4)
  notes    = "Standard errors clustered by unit in parentheses. Sample: 2000–2020.",
  escape   = FALSE
)
```

Referenced in prose as `@tbl-main`, never "Table 3".

## 5. Figure chunk — `fig-` label, `fig-cap`, no in-plot title

```{r}
#| label: fig-event-study
#| cache: true
#| dependson: "estimate-main"
#| fig-cap: "Event Study: Effect of Treatment. *Notes:* 95% CI, clustered by unit."
#| fig-width: 6
#| fig-height: 4
ggplot(es_df, aes(t, att, ymin = att - 1.96 * se, ymax = att + 1.96 * se)) +
  geom_pointrange() + geom_hline(yintercept = 0, linetype = "dashed") +
  theme_minimal(base_family = "serif")
```

No `ggsave()`: Quarto emits vector output for PDF and PNG for Word (INV-13). <!-- residue:prohibition -->

## Prose

Every number in prose is an inline expression against an object from a chunk above:
`` `r round(beta_hat, 3)` `` (INV-11). `python3 .claude/scripts/prose_number_check.py <manuscript>`
must exit 0 before the coder is done.
