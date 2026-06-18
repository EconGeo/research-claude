# Design: Pipeline Precedence + Per-Project Manuscript Naming

**Date:** 2026-06-17
**Status:** Approved design (pre-implementation)

## Problem

`apply.sh` runs cleanly and correctly excludes clo-author's `new-project` skill
(superseded by research-claude's single-`manuscript.qmd` quarto-empirical pipeline).
But excluding only `new-project` left **six downstream clo-author files installed and
active** that still instruct the old LaTeX multi-file / `scripts/R` / results-registry
layout. When a forking researcher's Claude reads both `quarto-empirical.md` and these
files, it receives contradictory file-layout instructions.

### Conflicting installed files

| Installed file (from clo-author) | Conflict with `quarto-empirical.md` |
|---|---|
| `skills/analyze/SKILL.md` | Saves analysis to `scripts/R/`, `saveRDS()` to `scripts/R/output/` — rule forbids a `scripts/R/` analysis dir |
| `skills/write/SKILL.md` | Outputs LaTeX `paper/sections/[section].tex` — rule keeps prose in the `.qmd` |
| `skills/revise/SKILL.md` | Reads `paper/main.tex`, writes `paper/sections/*.tex`, `.tex` response letters |
| `rules/working-paper-format.md` | Entirely LaTeX-first (`\documentclass`, `paper/main.tex`); marked "Legacy only" only *in another rule*, no marker in the file itself |
| `rules/content-invariants.md` (INV-12, INV-13) | Assume LaTeX `\caption{}` + `main.tex` table wrapping; quarto uses `tbl-cap`/`fig-cap` chunk options |
| `rules/permissions.md` | Lifecycle gates require/produce `paper/tables/*.tex`, `paper/main.tex`, `paper/sections/*.tex` |

### Second requirement

The manuscript file (today hardcoded as `manuscript.qmd` across four research-claude
rules) should default to `manuscript_<project>.qmd`, where `<project>` is the project
directory basename — e.g. the `zoning2026` project's manuscript is
`manuscript_zoning2026.qmd`.

## Constraints / context that shaped the design

- **clo-author is a live, actively-maintained submodule.** 131 commits in ~3 months;
  `analyze`/`write`/`revise` saw 13 commits in the last 6 months (~biweekly, last
  touched 2026-05-09). Recent work is substantive (paper-type architecture,
  numerical-discipline enforcement, referee-simulation realism).
- **The skills' content is good; only their file-layout assumptions clash.** Forking
  them to rewrite would mean chasing a biweekly-moving target to "fix" something that
  is not a quality defect.
- **research-claude already has a no-divergence override pattern.** `apply.sh` installs
  clo-author's `rules/` and `state/` first, then research-claude's own versions on top
  (steps 6–7), so research-claude wins while the submodule stays pristine and
  `apply.sh --update` keeps pulling upstream cleanly.

## Decision

Resolve the conflict by **declaring precedence**, not by editing or forking any
clo-author file. Zero submodule edits. No skill rewrites. No `apply.sh` scaffolding of
a starter `.qmd`. No git-remote parsing.

### Part 1 — `rules/pipeline-precedence.md` (new, research-claude-owned)

A single new rule, shipped by `apply.sh`'s existing research-claude `rules/` install
step (so it lands in every target project alongside `quarto-empirical.md`). It:

1. **Declares precedence.** When `quarto-empirical.md` is present, it overrides the
   file-layout instructions in clo-author's `/analyze`, `/write`, `/revise` skills and
   in the `working-paper-format`, `content-invariants` (INV-12, INV-13), and
   `permissions` rules. Their *methodological* content (analysis rigor, writing moves,
   revision discipline, referee simulation) still applies — only the **file layout** is
   overridden.

2. **Provides an old→new translation map** so that good content remains actionable:

   | clo-author layout instruction | quarto-empirical equivalent |
   |---|---|
   | `scripts/R/*.R`, `saveRDS()` to `scripts/R/output/` | cached code chunks inside the `.qmd` (`cache: true`, `dependson`) |
   | `paper/sections/*.tex` | prose sections inside the `.qmd` |
   | `paper/main.tex` | `manuscript_<project>.qmd` |
   | LaTeX `\caption{}` (INV-12), bare `tabular` wrapped by `main.tex` (INV-13) | `#\| tbl-cap:` / `#\| fig-cap:` chunk options; `modelsummary`/`kableExtra` emit the full float |
   | response letters as `paper/.../*.tex` | response letters as `.qmd`/`.md` per project preference |

3. **Documents the manuscript naming convention** (shared with Part 2):
   `manuscript_<project>.qmd`, `<project>` = project directory basename.

This resolves all six conflicts at once, survives every upstream update, and leaves the
upstream template fully intact.

### Part 2 — per-project manuscript naming (rules convention only)

Update the four research-claude rules that hardcode `manuscript.qmd` to document the
convention `manuscript_<project>.qmd` (basename of the project directory). No file is
scaffolded; the rule tells Claude the correct name when it creates the manuscript.

Files to update:
- `rules/quarto-empirical.md` — architecture diagram, Required YAML comment, Write Gate,
  coder-critic trigger sentence, render-command examples.
- `rules/quarto-pdf.md` — `manuscript.qmd` references.
- `rules/quarto-word.md` — `manuscript.qmd` references.
- `rules/data-manifest.md` — `manuscript.qmd` references.

Each gets a one-line convention note on first mention:
> `manuscript_<project>.qmd` — `<project>` is the project directory basename (e.g.
> `manuscript_zoning2026.qmd` in the `zoning2026/` project). Examples below use
> `manuscript_<project>.qmd` as a placeholder.

Render artifacts (`manuscript_<project>_files/`, `manuscript_<project>_cache/`) already
match the existing `*_files/` / `*_cache/` gitignore globs — no gitignore change needed.

## Components & boundaries

- **`rules/pipeline-precedence.md`** — one new file. Sole responsibility: declare that
  quarto-empirical's layout wins and translate clo-author's layout terms. Depends on
  nothing; consumed by Claude as loaded rule context. Self-contained.
- **Four edited rules** — documentation-only string/convention updates. No behavioral
  coupling between them beyond the shared naming convention, which the precedence rule
  also states (single source of truth for the convention is `pipeline-precedence.md`;
  the four rules reference the same placeholder).
- **`apply.sh`** — unchanged. The new rule rides the existing `RC_RULES` copy loop
  (step 6). Update only the install-summary comments (`--list` text, header banner) to
  mention `pipeline-precedence.md`.

## What this does NOT do (YAGNI)

- No edits to any `submodules/clo-author/**` file.
- No rewrite of `analyze`/`write`/`revise` SKILL.md.
- No `apply.sh` scaffolding of a starter `manuscript_<project>.qmd`.
- No git-remote parsing for the project name.
- No gitignore changes.

## Testing / verification

1. **apply.sh smoke test** — run into a temp project dir named `zoning2026`; confirm
   `.claude/rules/pipeline-precedence.md` lands and `apply.sh --list` mentions it.
2. **Convention coverage** — `grep -rn "manuscript\.qmd" rules/` returns only intentional
   generic mentions (or none); every operative reference uses `manuscript_<project>.qmd`.
3. **No submodule drift** — `git submodule status` and `git -C submodules/clo-author
   status` show the submodule unmodified.
4. **Contradiction check** — read `pipeline-precedence.md` against each of the six
   conflicting files and confirm every old-layout instruction has a translation-map row.

## Open questions

None. Decisions locked: project-dir basename for `<project>`; rules-convention-only
mechanism; precedence rule rather than skill rewrite.
