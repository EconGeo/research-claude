# Pipeline Precedence: Quarto-Empirical Overrides Legacy Layout

**This rule resolves the file-layout contradiction between research-claude's
single-`.qmd` pipeline and clo-author's inherited LaTeX/multi-file layout.**

research-claude installs clo-author's research-phase skills and rules (`/analyze`,
`/write`, `/revise`, `working-paper-format.md`, `content-invariants.md`,
`permissions.md`). Those files are mature and actively maintained upstream, and their
**methodological** content — analysis rigor, writing moves, revision discipline,
referee simulation, numerical discipline — fully applies. Only their **file-layout
assumptions** predate the quarto-empirical pipeline.

## Precedence Rule

When `quarto-empirical.md` is present in `.claude/rules/`, it is **authoritative over
all file-layout instructions** in the following clo-author files:

- `skills/analyze/SKILL.md`
- `skills/write/SKILL.md`
- `skills/revise/SKILL.md`
- `rules/working-paper-format.md`
- `rules/content-invariants.md` (specifically INV-12 and INV-13)
- `rules/permissions.md`

Follow those files for *how to think* (what makes a good analysis, a good section, a
good revision). Follow `quarto-empirical.md` for *where things live*. Where they
conflict on layout, quarto-empirical wins — no exceptions.

## Translation Map (legacy layout → quarto-empirical)

| clo-author layout instruction | quarto-empirical equivalent |
|---|---|
| `scripts/R/*.R`; `saveRDS()` to `scripts/R/output/` | cached code chunks inside the manuscript `.qmd` (`#\| cache: true`, `#\| dependson:`) |
| `paper/sections/*.tex` section files | prose sections written directly in the manuscript `.qmd` |
| `paper/main.tex` (the assembled paper) | `manuscript_<project>.qmd` (see Naming below) |
| LaTeX `\caption{}` on figures/tables (INV-12) | `#\| fig-cap:` / `#\| tbl-cap:` chunk options |
| Scripts export bare `tabular`, `main.tex` wraps the float (INV-13) | `modelsummary` / `kableExtra` emit the complete float from inside the chunk |
| `permissions.md` gates requiring/producing `paper/tables/*.tex`, `paper/main.tex`, `paper/sections/*.tex` | the gate is `quarto render` exits 0 with no NA/NaN inline expressions (see quarto-empirical "Write Gate") |
| Response letters as `paper/.../*.tex` | response letters as `.qmd` or `.md`, per project preference |

A reference to any legacy path above is satisfied by producing its quarto equivalent.
Do not create `scripts/R/`, `paper/sections/`, or `paper/main.tex` for a project that
follows quarto-empirical.

## Manuscript Naming Convention

The manuscript file is named **`manuscript_<project>.qmd`**, where `<project>` is the
**project directory basename**. Example: in a project directory named `zoning2026/`,
the manuscript is `manuscript_zoning2026.qmd`. This is the single source of truth for
the naming convention; `quarto-empirical.md`, `quarto-pdf.md`, `quarto-word.md`, and
`data-manifest.md` use `manuscript_<project>.qmd` as a placeholder for the same name.

Render artifacts (`manuscript_<project>_files/`, `manuscript_<project>_cache/`) already
match the `*_files/` and `*_cache/` gitignore globs — no gitignore change is needed.

## Scope

This rule governs **layout precedence and naming only**. It does not alter any
clo-author file (those remain pristine upstream submodule content) and does not change
the methodological guidance in the skills it references.
