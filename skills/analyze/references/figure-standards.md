# Figure Standards

Publication-quality figures for economics papers. Figures are produced by **chunks
in `manuscript_<project>.qmd`** — Quarto sizes and embeds them. Nothing is
`ggsave()`d to disk and re-included by hand.

**Mechanics live in the format rules:** `.claude/rules/quarto-pdf.md` (vector,
automatic) and `.claude/rules/quarto-word.md` (PNG at `dpi: 200`,
`fig-width: 6.5`). This file covers the design judgment those rules do not.

---

## Core Rules

- **Never add titles or subtitles inside ggplot** -- use `labs(title = NULL, subtitle = NULL)`
- **Figure information goes in two places:**
  1. **Chunk label** -- descriptive and `fig-` prefixed, e.g. `fig-enrollment-event-study`
  2. **`#| fig-cap:`** -- the authoritative title, numbered by Quarto and editable
     without re-running the chunk
- **Panel labels are the exception** -- "Panel A: Employment" inside multi-panel figures (via `patchwork`, `cowplot`, etc.) is fine since they identify sub-panels, not the whole figure
- **Axis labels must be publication-quality** -- "Employment Rate" not "emp_rate". Clean labels stay in the figure; titles and context go in the caption
- **Use serif fonts** -- figures should match the paper's body text
- **Show all years on the x-axis** when the panel spans ~20 years or fewer --
  `scale_x_continuous(breaks = min_year:max_year)`. Only thin the labels when they
  actually overlap (roughly >20 ticks)
- **Color-independent design** -- the figure must be readable in grayscale.
  Pair color with `shape` and `linetype` so series stay distinguishable when a
  referee prints it
- **Never `ggsave()` to a file and include it by hand.** Let Quarto render the
  chunk: it emits vector for PDF and PNG for Word automatically. Quarto cannot
  embed a PDF figure in a Word document — a hand-saved `fig.pdf` is exactly the
  bug this rule exists to prevent

---

## Font and Theme

Set serif fonts to match the paper's body text:

```r
theme_paper <- theme_minimal(base_family = "serif", base_size = 11) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position  = "bottom",
    plot.title       = element_blank(),  # No titles -- INV-12
    plot.subtitle    = element_blank()
  )

theme_set(theme_paper)
```

For Python (matplotlib):
```python
import matplotlib.pyplot as plt
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
})
```

---

## Axis Labels

- **Show all years on the x-axis** when the panel spans ~20 years or fewer:
  ```r
  scale_x_continuous(breaks = min_year:max_year)
  ```
  Only thin out labels when they overlap (roughly >20 ticks).

- **Human-readable labels:**
  - "Log Wages (2010 USD)" not "ln_wage_deflated"
  - "Share of Female Workers" not "pct_female"
  - Include units where applicable

---

## Color

- **Colorblind-friendly palettes** -- use `scale_color_brewer(palette = "Set2")`, `viridis`, or similar
- **Never rely on red/green contrast alone**
- **Color-independent design** -- figures must be readable in grayscale:
  - Combine color with shape (`shape` aesthetic)
  - Combine color with linetype (`linetype` aesthetic)
  - Series remain distinguishable without color

Recommended palettes:
```r
# Option 1: ColorBrewer
scale_color_brewer(palette = "Set2")

# Option 2: Viridis (perceptually uniform)
scale_color_viridis_d()

# Option 3: Manual (maximum control)
scale_color_manual(values = c("#1b9e77", "#d95f02", "#7570b3"))
```

---

## Figure Size

Set per chunk, not per file:

```r
#| label: fig-event-study
#| fig-cap: "Event study estimates of the treatment effect. Points are period-specific
#|   coefficients with 95% confidence intervals; the dashed line marks treatment onset.
#|   Pre-treatment coefficients are not distinguishable from zero. Source: [data source]."
#| fig-width: 6.5
#| fig-height: 4
```

- `fig-width: 6.5` matches the text width of a Word page with 1-inch margins —
  never exceed it for a full-width figure
- Single panel: 6.5 x 4. Side-by-side: build one figure with `patchwork`, do not
  emit two and place them manually
- A figure that genuinely needs landscape is usually two figures

---

## Common Figure Types

### Event Study Plot
```r
ggplot(es_data, aes(x = relative_time, y = estimate)) +
  geom_point(size = 2) +
  geom_errorbar(aes(ymin = ci_lower, ymax = ci_upper), width = 0.2) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
  geom_vline(xintercept = -0.5, linetype = "dotted", color = "gray50") +
  labs(x = "Periods Relative to Treatment", y = "Estimated Effect") +
  theme_paper
```

### Coefficient Plot
```r
library(modelsummary)
modelplot(models, coef_omit = "Intercept") +
  geom_vline(xintercept = 0, linetype = "dashed") +
  theme_paper
```

### RDD Plot
```r
rdplot(y = df$outcome, x = df$running_var, c = cutoff,
       x.label = "Running Variable", y.label = "Outcome")
```

---

## Captions (INV-2)

Every caption answers three things, in this order:

- **What is shown** — the estimand, the sample, the units
- **How to read it** — what the bands are, what the reference line marks
- **Where it came from** — the data source

The caption lives in `#| fig-cap:`, never inside the plot. It is the one part of
a figure a reader can consult without re-running anything, so it carries the
context the axes cannot.

---

## Prohibited Patterns

| Pattern | Reason |
|---------|--------|
| `ggtitle()` or `labs(title = "...")` | Titles go in `#\| fig-cap:` (INV-12) |
| `plt.title()` in matplotlib | Same reason |
| Default ggplot theme (gray background) | Use `theme_minimal` or custom theme |
| Red/green only color schemes | Not colorblind-friendly |
| `ggsave()` inside a manuscript chunk | Quarto emits the figure; saving it to disk produces a stale duplicate and breaks Word output |
| Chunk label without a `fig-` prefix | Quarto will not number or cross-reference it |
| Hardcoded "Figure 2" in prose | Use `@fig-label` |
| Axis labels with underscores | Human-readable labels required |
| Legend inside plot area (overlapping data) | Use `legend.position = "bottom"` |
