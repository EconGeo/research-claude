# Pipeline Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the research-claude fork so the pipeline runs end to end under the one-manuscript contract: every stage pairs a creator with a critic, every handoff is validated by an executable check, every declared contract is gate-enforced, every path reference resolves, and no shipped file instructs an agent to produce anything the contract forbids.

**Architecture:** A machine-readable registry (`rules/registry.yaml`) is read by one stdlib-only Python script (`scripts/pipeline.py`) that evaluates PRE/POST predicates, keeps `quality_reports/pipeline_state.json`, and computes the weighted score. A skill (`/pipeline`) drives dispatch in the main session and calls the script; it never reasons about a predicate. A `SubagentStop` hook logs every agent completion and a `Stop` hook reads that log to prove each creator was followed by its critic. Every gate is red-tested against a committed fixture project before its green is trusted. The instruction layer (agents, skills, rubrics, references, rules) is rewritten to describe only the one-manuscript path.

**Tech Stack:** bash (gates, installer), Python 3.9 stdlib only (pipeline, hooks, path/ref checkers), Quarto 1.9 + R 4.6 (fixture: fixest, modelsummary, ggplot2, here, tidyverse), git worktrees.

**Spec:** `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (v2, approved, rulings R-1..R-7). Evidence: `docs/audits/2026-09-08_full-tree-sweep.md` (the expectation for every verification step), `docs/audits/2026-09-08_repair-spec-review.md`, `docs/audits/2026-09-08_pipeline-audit-findings.md`.

## Global Constraints

- **One manuscript.** `rules/quarto-empirical.md` is the only contract (D-7). No file, template, rubric row, or hook may describe `scripts/R/`, `paper/tables/`, `paper/figures/`, `results_summary.md`, `.tex` side files, Rmd mode, or a separate results file as a live path.
- **One path rule (D-4).** Every pipeline path in a shipped file is written relative to the project root and `.claude/`-prefixed: `.claude/skills/analyze/templates/chunk-structure.md`, never `analyze/templates/...` or `templates/...`. Project-level paths are the enumerated exempt set in Task 3.1.
- **Registry is the single source (D-2, D-10).** No file other than `rules/registry.yaml`, `rules/quality.md` (weights), and the rendered `rules/permissions.md` states a creator→critic pair or a weight number.
- **Weights (set A, R-1):** literature 10, data 10, strategy 25, theory 20 `CONDITIONAL`, code 15, manuscript 10, referees 12.5 + 12.5, replication 5. Non-conditional sum exactly 100.
- **Limits:** 3 rounds per pair, 5 overall, 2 verification retries.
- **Tool name (D-25):** `Agent`, never `Task`, in every `tools:` / `allowed-tools:` line.
- **Python: 3.9 stdlib only** for every script and hook (`/usr/bin/python3` is 3.9.6 with no PyYAML and no jsonschema; hooks run under whatever `python3` is on PATH). No `match`, no `X | Y` runtime unions, no third-party imports.
- **Red before green.** Every new gate criterion and every `pre`/`post` predicate is shown FAILING against the fixture before it is shown passing. A green without a recorded red is a stop condition (spec §12).
- **The sweep is the expectation; the tree is the truth.** Every verification step runs the grep, reads the whole output, and only then records the result. A residue row the sweep did not list is a stop condition: record it in `docs/audits/2026-09-08_full-tree-sweep.md` under a `## Addendum (found during repair)` heading before fixing it.
- **Nothing project-specific ships.** `scripts/check_fork.sh` `project-identity` and `project-nouns` stay green at every commit.
- **Worktree development.** All Stage 0–7b work happens in the worktree `$W` on branch `repair/pipeline`. The shared checkout `$RC` stays on `main` because six paper repos link to it. Only POGM4 (the canary) is re-linked to `$W`, and only from Task 2.9 on.
- **Commit trailers.** Every commit ends with the two attribution lines given in the session's system reminder (`Co-Authored-By: ...` and `Claude-Session: ...`).

---

## 0. How to read this plan

### 0.1 Names used throughout

| Name | Value |
|---|---|
| `$RC` | `/Users/andrew.mueller/Academic/research-claude` — the shared checkout, stays on `main` |
| `$W` | `/Users/andrew.mueller/Academic/research-claude-repair` — the worktree, branch `repair/pipeline` (created in Task 0.2) |
| `$FX` | `$W/tests/fixture-project` — the committed fixture |
| `$T` | a temp copy of the fixture that `tests/run_fixture.sh` creates under `mktemp -d` and links the pipeline into |
| `$R` | `~/Research` — the six paper repos: POGM4 (canary), zoning2026, affordable_housing_2026, ESG, NAR_settlement, BRI |
| shipped dirs | `agents skills rules references hooks templates seeds scripts` (plus `tests` for the identity scan) |

### 0.2 Conventions the executor must follow

1. **Locate by quoted text, not by the sweep's line number, in `agents/*.md`.** The sweep's line numbers for the agents are stale (verified 2026-09-08: `agents/theorist.md` is 87 lines and the sweep cites line 1052; `agents/editor.md` is 366 lines, sweep cites 536/573/637). Its *quoted text* is accurate. Line numbers for `skills/`, `rules/`, `references/`, `hooks/` and `templates/` were spot-checked and match.
2. **Read the whole file before editing it.** `cat -n` to EOF. The per-file rewrite rules in Stage 3b are rows, not a substitute for reading.
3. **Residue markers.** A line that names a forbidden pattern *in order to forbid it* ends with `<!-- residue:prohibition -->`. A line that records history (a dated provenance entry, a decision rationale) ends with `<!-- residue:historical -->`. A file whose **first line** is exactly `<!-- residue:historical -->` is exempt in full (used for `rules/registry-verification-gate.md` only). The old `agent-refs:historical` marker from `fix/critic-dispatch` is replaced by `residue:historical`.
4. **Verification greps are run from `$W`** unless a step says otherwise, and the *whole* output is read before the expected result is written into the commit message or audit note.
5. **Commit per task.** Message prefix by kind: `test(...)`, `feat(...)`, `fix(...)`, `refactor(...)`, `docs(...)`, `chore(...)`. One task, one commit, unless a step says "commit" mid-task.
6. **Stop conditions (spec §12):** an unintended graph delta (`scripts/audit_graph.py` counts move in a direction a task did not intend); a gate green without a prior red; a smoke test passing while `critic-pairing.py` fires; a stage needing a file a later stage builds; a residue row the sweep did not list.

### 0.3 Decisions made by this plan (not in the spec)

These are choices the spec left open or that the ground truth forced. Each is one line here and applied where it lands.

| # | Decision | Why |
|---|---|---|
| P-1 | All Python is 3.9 stdlib. `registry.yaml` is written in a restricted YAML subset parsed by `scripts/registry_lib.py`; a dev-time criterion `registry-parse-agree` cross-checks against PyYAML when PyYAML is importable. State-file validation is hand-rolled. | `/usr/bin/python3` is 3.9.6 with no `yaml` or `jsonschema`; hooks cannot assume the micromamba env. |
| P-2 | Agent line numbers in the sweep are treated as stale; text is the locator. | Verified above. |
| P-3 | `rules/registry-verification-gate.md` is kept per spec §8 (actor nouns reassigned, "registry" disambiguated) and made file-level `residue:historical`. Deleting it would be more consistent with D-7; the spec says keep, so it is kept and flagged in Task 3b.9 for a later ruling. | Spec §8 row is explicit. |
| P-4 | Real-estate profiles: `~/Research/.claude/references/journal-profiles.md` already carries REE, JREFE and a housing "JHE" (lines 351–403). The repo file does not. The housing journal is renamed `JHousE` in both files to end the collision with Journal of Health Economics `JHE`; JRER, JREPM, APSR, AJPS, JOP are added to both. | Measured 2026-09-08. |
| P-5 | `registry-complete` allows `critic: none` only when `role` is `critic`, `referee` or `infrastructure`; a `creator` with weight > 0 must name a critic. `data-engineer` has weight 0 and `scored_under: code`. | The referees (12.5 each) and the verifier (5) have no critic by design; the spec's rule as written would fail them. |
| P-6 | State schema is v2 (Task 1.6), not the clo-author shape; `templates/pipeline-state.json` ships the empty v2 instance. `pipeline.py state init` creates the project file; nothing is seeded. | The upstream template models the deleted orchestrator's bookkeeping. |
| P-7 | `PRODUCES` gains a seventh predicate type, `prose-check` (runs `prose_number_check.py`, exit 0). | Spec §5 lists it in the PRODUCES table but not in the predicate-type table. |
| P-8 | `scripts/SHIPPED` (one filename per line) is the list `apply.sh` links into `.claude/scripts/` and `check_install.sh` wants. Repo-maintenance scripts (`check_fork.sh`, `check_install.sh`, `audit_graph.py`, `sync-zotpilot-skills.sh`, `check_paths.py`, `check_refs.py`, `render_registry.py`) are not shipped. | Keeps `.claude/scripts/X` resolution flat while not linking dev tooling into papers. |
| P-9 | `hooks/post-merge.sh` is deleted, not installed to `.git/hooks/`. | It prints a reminder `/checkpoint` already owns; nothing installs it. |
| P-10 | `critic-pairing.py` (Stop) emits `hookSpecificOutput.additionalContext` + `systemMessage` and, by default, blocks **once per session per pair** with `{"decision":"block","reason":...}` guarded by `stop_hook_active` and a session sentinel. `RC_CRITIC_PAIRING_ADVISORY=1` disables the block. | Review A5: an advisory nobody sees is the repo's recurring failure; block-once is the documented channel. |
| P-11 | `/new-project-ztp` stays a skill; `/pipeline setup` calls it (open item 1). `/promote` is the one promotion mechanism; `meta-governance.md` states the policy and points at `/promote` (open item 2). `pipeline_state.json` is committed; `/checkpoint` reads it for the staleness sweep (open item 5). | Least churn; one mechanism. |
| P-12 | Stage 3 (path layer) and Stage 3b (instruction layer) are executed as one pass per file group, because a path rewritten in Stage 3 to a file Stage 3b creates would dangle in between (a spec stop condition). Stage 3 still owns the gate, the resolution table and the pre-rewrite inventory. | Sequencing. |
| P-13 | `tests/run_fixture.sh` has two tiers: `--mechanical` (default; no LLM; simulates dispatch-log lines) and `--live` (runs `claude -p '/pipeline ...'` in `$T`; used for Stage 5 and Stage 8 sign-off). `unverified:` whether `claude -p` loads project skills — Task 5.7 tests that first. | The spec's end-to-end criterion needs a model; the gate cannot. |
| P-14 | `rules/workflow.md` is **not** restored. Its §2 loop and §4 two-modes text move into `skills/pipeline/SKILL.md`; §3 is the registry. D1 block keeps asserting it absent. | Spec §3 header restores "graph, registry and lifecycle", D-6 lists what is not restored; the loop now lives in the driver. |
| P-15 | `data/cleaned/` is removed from the gitignore seed. | D-7: there is no cleaned-data stage. |

---

## 1. File map

**Created**

| Path | Owner stage | Responsibility |
|---|---|---|
| `tests/fixture-project/` (CLAUDE.md, `manuscript_fixture.qmd`, `references.bib`, `data/raw/panel.csv`, `data/raw/data_manifest.md`, `templates/quarto-preamble.tex`, `quality_reports/prose_number_allowlist.csv`, `.gitignore`, `.claude/settings.json`) | 0 | the fixture every gate is red-tested against (D-12) |
| `tests/make_fixture_data.R` | 0 | regenerates `data/raw/panel.csv` deterministically |
| `tests/run_fixture.sh` | 0 (skeleton), 1, 5 | repeatable end-to-end check |
| `tests/test_pipeline.py` | 1 | unittest suite for `pipeline.py` against `$FX` |
| `scripts/check_refs.py` | 0 | `deleted-things`, `inv-refs`, `skill-refs`, `tool-name`, `hooks-readme`, `manuscript-model`, `latex-residue` criteria |
| `scripts/check_paths.py` | 0 | `path-resolves` with the resolution table |
| `scripts/registry_lib.py` | 1 | restricted-YAML loader, registry validation, weight checks |
| `scripts/render_registry.py` | 1 | renders `rules/permissions.md` from `rules/registry.yaml` |
| `scripts/pipeline.py` | 1, 1b | `manuscript`, `pre`, `post`, `score`, `state`, `conflicts`, `registry check` |
| `scripts/qmd_chunks.py` | 7 | extracts R chunks from a `.qmd` for `lint-scripts.sh` |
| `scripts/SHIPPED` | 2 | list of scripts linked into projects |
| `rules/registry.yaml` | 1 | the declaration registry |
| `rules/permissions.md` | 1 | rendered from the registry |
| `rules/lifecycle.md` | 1 | prose description of what `pipeline.py pre/post` does |
| `rules/meta-governance.md` | 1 | learning promotion policy, no autonomous self-modification |
| `templates/pipeline-state.json` | 2 | empty v2 state instance |
| `templates/journal-profile-template.md` | 2 | from POGM4's copy, cross-refs fixed |
| `seeds/` (`gitignore`, `settings.json`, `bootstrap-pipeline.sh`, `ai-use-log.md`, `data_manifest.md`, `quarto-preamble.tex`) | 2 | copied once, project-owned |
| `skills/analyze/templates/chunk-structure.md` | 3b | replaces the two script scaffolds |
| `skills/review/templates/claim-evidence-table.md` | 4 | Claim–Evidence Table format |
| `agents/lit-critic.md` | 4 | literature critic (D-15) |
| `skills/pipeline/SKILL.md` + `skills/pipeline/references/{setup,literature,data,strategy,theory,analyze,write,review,submit,talk,recovery}.md` | 5 | the driver |
| `hooks/dispatch-log.py`, `hooks/critic-pairing.py` | 5 | SubagentStop log, Stop pairing check |
| `docs/audits/2026-09-08_stage0-red.md`, `docs/audits/2026-09-08_embed-test.md`, `docs/decisions/2026-09-08_d1-superseded.md`, `docs/decisions/2026-09-08_d3-addendum-lit-critic.md` | 0, 2, 1, 4 | records |

**Modified (major):** `scripts/check_fork.sh`, `scripts/check_install.sh`, `apply.sh`, `rules/{agents,quality,logging,content-invariants,data-manifest,content-standards,quarto-word,quarto-pdf,quarto-empirical,revision,registry-verification-gate}.md`, every file in spec §8, `hooks/*`, `hooks/README.md`, `README.md`, `references/{discipline-cards,journal-profiles,domain-profile,coding-standards-r,coding-standards-julia,personal-style-guide}.md`, `~/Research/.claude/references/journal-profiles.md`.

**Deleted:** `templates/{gitignore,settings.json,bootstrap-pipeline.sh,ai-use-log.md,data_manifest.md}` (moved to `seeds/`), `skills/analyze/templates/{r-script-structure.R,python-script-structure.py,results-summary.md}`, `skills/submit/templates/cover-letter.tex` (→ `.qmd`), `references/{coding-standards-rmd,prompt-formatting-core}.md`, `rules/html-dashboard.md`, `skills/dashboard/`, `hooks/post-merge.sh`, `skills/analyze/config/replication-tolerances.json` (consumer was `--dual`; `--replicate` keeps tolerances inline in `review/SKILL.md`).

---

## Stage 0 — Baseline, fixture, every gate failing

**Exit criteria:** worktree exists; `fix/critic-dispatch` and `stash@{0}` are gone with their content preserved; the fixture renders; `tests/run_fixture.sh --mechanical` runs and reports FAIL for every not-yet-built check; `check_fork.sh` prints FAIL for every new criterion and the inverted D1 block; `check_install.sh` has `branch`; `docs/audits/2026-09-08_stage0-red.md` records the red output verbatim.

### Task 0.1: Baseline snapshot

**Files:**
- Create: `docs/audits/baseline-2026-09-08/check_fork.txt`, `docs/audits/baseline-2026-09-08/check_install.txt`, `docs/audits/baseline-2026-09-08/audit_graph.json`, `docs/audits/baseline-2026-09-08/residue_grep.txt`

- [ ] **Step 1: Record the three gates as they stand on `main`**

```bash
cd "$RC" && mkdir -p docs/audits/baseline-2026-09-08
./scripts/check_fork.sh > docs/audits/baseline-2026-09-08/check_fork.txt 2>&1; echo "check_fork exit=$?"
./scripts/check_install.sh --all > docs/audits/baseline-2026-09-08/check_install.txt 2>&1; echo "check_install exit=$?"
python3 scripts/audit_graph.py . docs/audits/baseline-2026-09-08/audit_graph.json
```
Expected: `check_fork exit=0`; `check_install exit=0` (F9: install layer healthy; lock WARNs only); audit_graph prints `dangling path refs : 66` (audit F4). If the numbers differ, read the output in full and record the actual numbers in Step 3 — do not adjust the plan's expectation silently.

- [ ] **Step 2: Record the widened residue grep as it stands**

This is the exact pattern the `latex-residue` criterion will use (spec §11). Run it, read all of it, count it.

```bash
cd "$RC" && grep -rnE 'paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<' \
  agents skills rules references hooks templates > docs/audits/baseline-2026-09-08/residue_grep.txt; wc -l docs/audits/baseline-2026-09-08/residue_grep.txt
```
Expected: on the order of 250–350 lines (sweep §12 counts ≈45 + ≈60 + ≈150 + ≈30 + ≈40 residue rows, not all of which match this pattern). Read the file end to end. Any hit in a file the sweep lists as clean (`agents/writer.md`, `skills/promote/SKILL.md`, `skills/talk/SKILL.md`, ...) is a sweep gap: add it now under `## Addendum (found during repair)` in `docs/audits/2026-09-08_full-tree-sweep.md`.

- [ ] **Step 3: Commit the baseline on `main`**

```bash
cd "$RC" && git add docs/audits/baseline-2026-09-08 docs/audits/2026-09-08_full-tree-sweep.md
git commit -m "docs(audit): baseline snapshot before pipeline repair — gates, graph, residue grep"
```

### Task 0.2: Worktree, branch, fold `fix/critic-dispatch` and `stash@{0}`

**Files:**
- Create: `docs/audits/2026-09-08_stash-discover-lit.patch`

- [ ] **Step 1: Create the worktree**

```bash
cd "$RC" && git worktree add -b repair/pipeline ../research-claude-repair main
git worktree list
```
Expected: two rows — `$RC ... [main]` and `$W ... [repair/pipeline]`. `$RC` stays on `main`.

- [ ] **Step 2: Cherry-pick the 9a/9b criteria onto the branch**

```bash
cd "$W" && git cherry-pick cd1d47a && git log --oneline -2
```
Expected: clean cherry-pick; top commit `test(check_fork): criteria 9a/9b — no skill may name a deleted agent`. These 40 lines are rewritten in Task 0.6 into `check_refs.py`'s `deleted-things`; the cherry-pick preserves their authorship and the `worker-critic` generic-term exemption.

- [ ] **Step 3: Preserve the stash as a patch, then drop it**

The stash holds a partial `/discover lit → /lit-position` pointer that still says "six-category self-check" (Stage 4 replaces that with `lit-critic`) and names `/seed-papers`. It is a starting draft for Task 6.1, not something to apply.

```bash
cd "$RC" && git stash show -p 'stash@{0}' > "$W/docs/audits/2026-09-08_stash-discover-lit.patch"
wc -l "$W/docs/audits/2026-09-08_stash-discover-lit.patch"    # expect ~65 lines
git stash drop 'stash@{0}'
git stash list                                                 # expect empty
```

- [ ] **Step 4: Delete the folded branch**

```bash
cd "$RC" && git branch -D fix/critic-dispatch && git branch
```
Expected: `design/quarto-native-pipeline`, `main`, `repair/pipeline` (the design branch is untouched; it is not in scope).

- [ ] **Step 5: Commit**

```bash
cd "$W" && git add docs/audits/2026-09-08_stash-discover-lit.patch
git commit -m "chore: preserve stash@{0} (/discover lit pointer draft) as a patch; branch fix/critic-dispatch folded"
```

### Task 0.3: Fixture project — data, manuscript, bib, preamble, manifest

**Files:**
- Create: `tests/make_fixture_data.R`, `tests/fixture-project/data/raw/panel.csv`, `tests/fixture-project/data/raw/data_manifest.md`, `tests/fixture-project/manuscript_fixture.qmd`, `tests/fixture-project/references.bib`, `tests/fixture-project/templates/quarto-preamble.tex`, `tests/fixture-project/quality_reports/prose_number_allowlist.csv`, `tests/fixture-project/CLAUDE.md`, `tests/fixture-project/.gitignore`, `tests/fixture-project/README.md`

**Interfaces:**
- Produces: a project that renders clean under the contract; the declared manuscript is `manuscript_fixture.qmd`; sections `# Introduction`, `# Data`, `# Empirical Strategy`, `# Results`, `# Conclusion`, `## AI Use Statement {.unnumbered}`; chunk labels `setup`, `build-panel`, `estimate-main`, `tbl-main`, `fig-trends`; one bib key `fixture2026`.

- [ ] **Step 1: Data generator**

`tests/make_fixture_data.R`:
```r
# make_fixture_data.R — deterministic synthetic panel for tests/fixture-project.
# Run from the repo root: Rscript tests/make_fixture_data.R
set.seed(20260908L)
n_units <- 40L; n_years <- 10L
panel_fixture <- expand.grid(unit = seq_len(n_units), year = 2011L + seq_len(n_years) - 1L)
treat_year <- ifelse(panel_fixture$unit <= 20L, 2016L, 9999L)
panel_fixture$treated <- as.integer(panel_fixture$year >= treat_year[match(panel_fixture$unit, panel_fixture$unit)])
unit_fe <- rnorm(n_units, 0, 0.5)[panel_fixture$unit]
year_fe <- seq(0, 0.45, length.out = n_years)[panel_fixture$year - 2010L]
panel_fixture$outcome <- round(2 + unit_fe + year_fe + 0.30 * panel_fixture$treated + rnorm(nrow(panel_fixture), 0, 0.3), 4)
dir.create("tests/fixture-project/data/raw", recursive = TRUE, showWarnings = FALSE)
write.csv(panel_fixture, "tests/fixture-project/data/raw/panel.csv", row.names = FALSE)
message("wrote ", nrow(panel_fixture), " rows")
```

- [ ] **Step 2: Generate the data and check it**

```bash
cd "$W" && Rscript tests/make_fixture_data.R && head -3 tests/fixture-project/data/raw/panel.csv && wc -l tests/fixture-project/data/raw/panel.csv
```
Expected: `wrote 400 rows`; header `"unit","year","treated","outcome"`; 401 lines.

- [ ] **Step 3: Manifest, allowlist, preamble, bib**

`tests/fixture-project/data/raw/data_manifest.md` — copy the header of `$W/templates/data_manifest.md` (read it in full first) and add exactly one row:

```
| Synthetic panel | unit, year, treated, outcome | data/raw/panel.csv | generated by tests/make_fixture_data.R | manual | 2026-09-08 | free | Deterministic (seed 20260908); 40 units × 10 years; true ATT 0.30 |
```

`tests/fixture-project/quality_reports/prose_number_allowlist.csv`:
```
literal,reason
2011,first panel year (design constant)
2020,last panel year (design constant)
2016,treatment year (design constant)
```

`tests/fixture-project/templates/quarto-preamble.tex` — the same content Task 2.3 puts in `seeds/quarto-preamble.tex` (write it here first; Task 2.3 copies it):

```latex
% quarto-preamble.tex — LaTeX preamble for the PDF output of the declared manuscript
% (quarto-empirical pipeline). Citations are handled by Quarto via cite-method: biblatex;
% do NOT load biblatex here. Working-paper formatting only.
\usepackage{setspace}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\usepackage{microtype}
\usepackage{amssymb, amsmath, amsfonts, mathtools}
\usepackage{booktabs, array, makecell}
\usepackage{siunitx}
\usepackage{rotating, tabularx}
\usepackage{graphicx}
\usepackage{float}
\usepackage{caption}
\captionsetup{font=small, labelfont=bf, justification=justified}
\interfootnotelinepenalty=10000
\setlength{\footnotesep}{0.5cm}
```
(Deliberately omits `\doublespacing` and `threeparttable`, both of which are in the widened residue pattern; the seed must pass the gate it ships under.)

`tests/fixture-project/references.bib`:
```bibtex
@article{fixture2026,
  author  = {Fixture, Ada and Example, Ben},
  title   = {A Synthetic Staggered Adoption},
  journal = {Journal of Fixture Economics},
  year    = {2026},
  volume  = {1},
  pages   = {1--10}
}
```

- [ ] **Step 4: The manuscript**

`tests/fixture-project/manuscript_fixture.qmd` (every prose number is an inline expression; the three calendar constants are allowlisted):

````markdown
---
title: "Fixture: A Synthetic Staggered Adoption"
author:
  - name: "Fixture Author"
    affiliation: "Fixture University"
    email: "fixture@example.edu"
date: today
abstract: |
  A forty-unit synthetic panel with a staggered treatment. The document exists so that
  every pipeline gate can be tested against a manuscript that follows the contract.
format:
  pdf:
    pdf-engine: xelatex
    include-in-header: "templates/quarto-preamble.tex"
    toc: false
    number-sections: true
    keep-tex: false
    cite-method: biblatex
execute:
  echo: false
  message: false
  warning: false
  cache: true
bibliography: "references.bib"
link-citations: true
# No top-level csl: the PDF path renders citations via biblatex (cite-method above).
---

```{r}
#| label: setup
#| cache: false
#| include: false
library(here)
library(tidyverse)
library(fixest)
library(modelsummary)
library(kableExtra)

set.seed(20260908L)

# Paper-to-code naming map
#   Y_it  -> outcome      (data/raw/panel.csv: outcome)
#   D_it  -> treated      (data/raw/panel.csv: treated)
#   alpha_i -> unit FE    (absorbed)
#   gamma_t -> year FE    (absorbed)
# Dependency chain:
#   build-panel -> estimate-main -> tbl-main
#                                -> fig-trends
```

# Introduction

This fixture documents a synthetic staggered adoption in the spirit of @fixture2026.
The panel covers `r n_distinct_units` units observed over `r n_years` years.

# Data

```{r}
#| label: build-panel
#| cache: true
#| cache.extra: !expr list(file.mtime(here("data/raw/panel.csv")))
panel <- read_csv(here("data/raw/panel.csv"), show_col_types = FALSE)
n_distinct_units <- n_distinct(panel$unit)
n_years <- n_distinct(panel$year)
share_treated_units <- mean(tapply(panel$treated, panel$unit, max))
```

Half of the units adopt in 2016; the treated share of units is
`r round(share_treated_units, 2)`. The first and last panel years are 2011 and 2020.

# Empirical Strategy

$$
Y_{it} = \alpha_i + \gamma_t + \beta D_{it} + \varepsilon_{it}
$$ {#eq-twfe}

@eq-twfe is a two-way fixed effects specification with standard errors clustered by unit.

# Results

```{r}
#| label: estimate-main
#| cache: true
#| dependson: "build-panel"
m_main <- feols(outcome ~ treated | unit + year, data = panel, cluster = ~unit)
beta_hat <- coef(m_main)[["treated"]]
se_hat   <- se(m_main)[["treated"]]
```

The estimated effect is `r round(beta_hat, 3)` (SE `r round(se_hat, 3)`), shown in @tbl-main;
@fig-trends plots the raw means.

```{r}
#| label: tbl-main
#| cache: true
#| dependson: "estimate-main"
#| tbl-cap: "Effect of Treatment on the Outcome"
modelsummary(
  list("TWFE" = m_main),
  output   = "kableExtra",
  booktabs = TRUE,
  stars    = c("*" = 0.10, "**" = 0.05, "***" = 0.01),
  notes    = "Standard errors clustered by unit in parentheses. Synthetic data.",
  escape   = FALSE
)
```

```{r}
#| label: fig-trends
#| cache: true
#| dependson: "build-panel"
#| fig-cap: "Mean Outcome by Year and Treatment Group. *Notes:* Synthetic data; treated units adopt in the sixth year."
#| fig-width: 6
#| fig-height: 4
panel |>
  mutate(group = if_else(unit <= 20, "Treated", "Control")) |>
  group_by(group, year) |>
  summarise(outcome = mean(outcome), .groups = "drop") |>
  ggplot(aes(year, outcome, colour = group)) +
  geom_line() +
  labs(x = "Year", y = "Mean outcome", colour = NULL) +
  theme_minimal(base_family = "serif")
```

# Conclusion

The point estimate of `r round(beta_hat, 3)` recovers the design's true effect within
sampling error.

## AI Use Statement {.unnumbered}

No generative AI was used in the preparation of this fixture beyond the pipeline under test.

# References {.unnumbered}
````

- [ ] **Step 5: Project files**

`tests/fixture-project/CLAUDE.md`:
```markdown
# Fixture project

manuscript: manuscript_fixture.qmd

**Pipeline:** quarto-empirical (single `manuscript_fixture.qmd`, PDF primary).
This project exists to red-test research-claude's gates. It has no research content.
Analysis language: R.
```

`tests/fixture-project/.gitignore` — copy `$W/templates/gitignore` verbatim for now (Task 2.4 replaces it with the seed and adds the new lines). `tests/fixture-project/README.md`: three lines saying what the fixture is, that `tests/run_fixture.sh` copies it to a temp dir before linking the pipeline, and that `data/raw/panel.csv` is regenerated by `tests/make_fixture_data.R`.

- [ ] **Step 6: Render and prose-check the fixture (green is required here — this is the manuscript, not a gate)**

```bash
cd "$FX" && quarto render manuscript_fixture.qmd 2>&1 | tail -5; echo "render exit=${PIPESTATUS[0]}"
ls manuscript_fixture.pdf && python3 "$W/scripts/prose_number_check.py" manuscript_fixture.qmd; echo "prose exit=$?"
```
Expected: `render exit=0`, PDF present, `prose exit=0`. If `prose_number_check.py` flags a literal, read its output in full: either it is one of the three allowlisted constants (fix the allowlist path/format per the script's own usage text) or the manuscript has a typed number — make it an expression. Remove render artifacts before committing: `rm -rf manuscript_fixture_cache manuscript_fixture_files manuscript_fixture.pdf .quarto`.

- [ ] **Step 7: Commit**

```bash
cd "$W" && git add tests/ && git commit -m "test(fixture): committed fixture project — synthetic panel, contract-conforming manuscript, manifest, allowlist"
```

### Task 0.4: `tests/run_fixture.sh` skeleton (mechanical tier)

**Files:**
- Create: `tests/run_fixture.sh`

**Interfaces:**
- Produces: a harness that copies `$FX` to `$T`, links the pipeline from `$W` with `apply.sh`, and runs a list of named checks, printing `PASS [name]` / `FAIL [name] reason`; exit 1 if any FAIL. Later tasks append checks to the `CHECKS` list; this task ships the checks that must be red now.

- [ ] **Step 1: Write the harness**

```bash
#!/usr/bin/env bash
# run_fixture.sh — the repeatable end-to-end check against tests/fixture-project.
#   tests/run_fixture.sh               # mechanical tier: no LLM, simulated dispatch log
#   tests/run_fixture.sh --live        # also runs `claude -p '/pipeline ...'` in the temp copy
#   tests/run_fixture.sh --keep        # leave the temp copy on disk and print its path
# Exit 0 = every check passed. Every check is named so a red can be cited.
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIVE=false; KEEP=false
for a in "$@"; do case "$a" in --live) LIVE=true;; --keep) KEEP=true;; esac; done

T="$(mktemp -d)"; export T RC
[[ "$KEEP" == true ]] || trap 'rm -rf "$T"' EXIT
cp -R "$RC/tests/fixture-project/." "$T/"
git -C "$T" init -q && git -C "$T" add -A && git -C "$T" -c user.name=fx -c user.email=fx@x commit -qm "fixture" 
fail=0
ok()  { echo "PASS [$1]"; }
bad() { echo "FAIL [$1] ${2:-}"; fail=1; }
run() { # run <name> <command...>  — PASS iff command exits 0
  local name="$1"; shift
  if out="$("$@" 2>&1)"; then ok "$name"; else bad "$name" "$(printf '%s' "$out" | tail -3 | tr '\n' ' ')"; fi
}
expect_fail() { # expect_fail <name> <command...> — PASS iff command exits non-zero (a red test)
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then bad "$name" "expected non-zero exit"; else ok "$name"; fi
}

echo "══ fixture copy: $T"
run link "$RC/apply.sh" --project-dir "$T" --link

# ── mechanical checks (extended by later tasks; keep the names stable) ──
run manuscript-declared   python3 "$RC/scripts/pipeline.py" --root "$T" manuscript
run state-init            python3 "$RC/scripts/pipeline.py" --root "$T" state init
run state-valid           python3 "$RC/scripts/pipeline.py" --root "$T" state validate
run registry-check        python3 "$RC/scripts/pipeline.py" --root "$RC" registry check
expect_fail pre-writer-red python3 "$RC/scripts/pipeline.py" --root "$T" pre writer      # no coder-critic score yet
run render                bash -c "cd '$T' && quarto render manuscript_fixture.qmd >/dev/null 2>&1"
run prose-check           python3 "$RC/scripts/prose_number_check.py" "$T/manuscript_fixture.qmd"

if [[ "$LIVE" == true ]]; then
  echo "── live tier"
  run live-pipeline bash -c "cd '$T' && claude -p '/pipeline run --until analyze --yes' --permission-mode acceptEdits >/dev/null 2>&1"
  run live-dispatch-log test -s "$T/quality_reports/agent_dispatch.jsonl"
fi

[[ $fail -eq 0 ]] && echo "✓ run_fixture: PASS" || echo "✗ run_fixture: FAIL"
[[ "$KEEP" == true ]] && echo "kept: $T"
exit $fail
```

- [ ] **Step 2: Run it and read the whole output — this is the Stage 0 red**

```bash
cd "$W" && chmod +x tests/run_fixture.sh && tests/run_fixture.sh; echo "exit=$?"
```
Expected: `PASS [link]`, `PASS [render]`, `PASS [prose-check]`; `FAIL [manuscript-declared]`, `FAIL [state-init]`, `FAIL [state-valid]`, `FAIL [registry-check]` (all: `can't open file .../scripts/pipeline.py`); `PASS [pre-writer-red]` (a missing script exits non-zero — this check is vacuously green until Task 1.7 makes it meaningful; note that in the red record); `exit=1`. Paste the full output into `docs/audits/2026-09-08_stage0-red.md` under `## run_fixture.sh`.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add tests/run_fixture.sh docs/audits/2026-09-08_stage0-red.md
git commit -m "test(fixture): run_fixture.sh skeleton — mechanical tier, every pipeline check red"
```

### Task 0.5: `scripts/check_refs.py` — text criteria, written failing

**Files:**
- Create: `scripts/check_refs.py`

**Interfaces:**
- Produces: `python3 scripts/check_refs.py --root DIR --criterion NAME` for `NAME` in `latex-residue`, `manuscript-model`, `deleted-things`, `inv-refs`, `skill-refs`, `tool-name`, `hooks-readme`. Prints `PASS [name]` or `FAIL [name]` followed by indented `path:line: text` rows, and `WARN [name]` rows for vendored trees; exits 0 on PASS/WARN-only, 1 on FAIL. `check_fork.sh` calls it once per criterion.

- [ ] **Step 1: Write the checker**

```python
#!/usr/bin/env python3
"""check_refs.py — text criteria for scripts/check_fork.sh (stdlib, Python 3.9).

Each criterion scans the shipped tree and prints PASS/FAIL/WARN rows. A line ending in
'<!-- residue:prohibition -->' or '<!-- residue:historical -->' is exempt from
latex-residue, manuscript-model and deleted-things. A file whose first line is exactly
'<!-- residue:historical -->' is exempt in full. Vendored trees (zotpilot-skills/,
submodules/) are scanned for deleted-things only and reported as WARN.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
VENDORED = ["zotpilot-skills", "submodules/ai-audit"]
TEXT_SUFFIX = {".md", ".py", ".sh", ".json", ".R", ".qmd", ".yaml", ".yml", ".tex", ".bib", ""}
MARK = re.compile(r"<!-- residue:(prohibition|historical) -->\s*$")

LATEX_RESIDUE = re.compile(
    r"paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|"
    r"\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|"
    r"\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<")
MANUSCRIPT_MODEL = [
    (re.compile(r"ggsave\("), "ggsave( — figures are fig- chunks"),
    (re.compile(r"saveRDS\("), "saveRDS( — no intermediate objects outside scripts/acquire"),
    (re.compile(r"writeLines\([^)]*\.tex"), "writeLines to .tex"),
    (re.compile(r'dir\.create\("paper'), 'dir.create("paper'),
]
DELETED_AGENTS = re.compile(r"\b(orchestrator|librarian-critic|librarian|guide-writer|rmd-coder-critic|domain-reviewer)\b", re.I)
DELETED_SCRIPTS = re.compile(r"generate_(dashboard|html_report)\.py|(^|[^A-Za-z0-9_])guide/|clone .*clo-author|clo-author-upgrade")
ABSENT_SKILLS = ["new-project", "review-paper", "audit-replication", "data-deposit", "audit-reproducibility",
                 "compile-latex", "prompt", "prompt-only", "interview-me", "research-ideation", "preregister",
                 "seven-pass-review", "devils-advocate", "promote-memory", "data-analysis"]
INV_RETIRED = {"INV-22"}
INV_REF = re.compile(r"\bINV-(\d{1,2})\b")
SLASH = re.compile(r"(?<![A-Za-z0-9_/.\-`])/([a-z][a-z0-9-]{2,})\b(?!/)")
# Slash tokens that are not skills: Claude Code built-ins, shell paths, this plan's own vocabulary.
SLASH_ALLOW = {"compact", "clear", "help", "init", "memory", "config", "permissions", "cost", "doctor", "status",
               "login", "logout", "model", "mcp", "agents", "hooks", "resume", "plan", "rewind", "export", "bug",
               "vim", "context", "loop", "schedule", "checkpoint", "tmp", "usr", "opt", "dev", "etc", "var", "bin",
               "home", "users", "private", "library", "applications", "system", "volumes", "workflows", "tasks",
               "artifacts", "code", "docs", "en", "api", "npm", "ajax", "libs", "gh-pages"}
TOOLS_LINE = re.compile(r"^(allowed-)?tools:\s*(.*)$")

def shipped_files(root: Path, dirs):
    for d in dirs:
        p = root / d
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix in TEXT_SUFFIX and ".git" not in f.parts:
                yield f

def lines_of(f: Path):
    try:
        text = f.read_text(errors="ignore")
    except OSError:
        return []
    lines = text.split("\n")
    if lines and lines[0].strip() == "<!-- residue:historical -->":
        return []
    return [(i + 1, ln) for i, ln in enumerate(lines) if not MARK.search(ln)]

def report(name, hits, warns=()):
    if hits:
        print(f"FAIL [{name}]")
        for h in hits: print(f"    {h}")
    else:
        print(f"PASS [{name}]")
    for w in warns: print(f"WARN [{name}] {w}")
    return 1 if hits else 0

def crit_latex_residue(root):
    hits = [f"{f.relative_to(root)}:{n}: {ln.strip()[:120]}"
            for f in shipped_files(root, SHIP) for n, ln in lines_of(f) if LATEX_RESIDUE.search(ln)]
    return report("latex-residue", hits)

def crit_manuscript_model(root):
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for rx, why in MANUSCRIPT_MODEL:
                if rx.search(ln) and "scripts/acquire" not in ln:
                    hits.append(f"{f.relative_to(root)}:{n}: {why}")
    return report("manuscript-model", hits)

def crit_deleted_things(root):
    absent = re.compile(r"(?<![A-Za-z0-9_/.\-])/(" + "|".join(map(re.escape, ABSENT_SKILLS)) + r")\b")
    inv22 = re.compile(r"\bINV-22\b")
    def scan(files):
        out = []
        for f in files:
            for n, ln in lines_of(f):
                if DELETED_AGENTS.search(ln) and "worker-critic" not in ln.lower():
                    out.append(f"{f.relative_to(root)}:{n}: deleted agent named")
                elif DELETED_SCRIPTS.search(ln):
                    out.append(f"{f.relative_to(root)}:{n}: deleted script/dir/upgrade path")
                elif absent.search(ln):
                    out.append(f"{f.relative_to(root)}:{n}: absent skill invoked")
                elif inv22.search(ln) and "RETIRED" not in ln and "retired" not in ln and not str(f).endswith("content-invariants.md"):
                    out.append(f"{f.relative_to(root)}:{n}: INV-22 cited as live")
        return out
    hits = scan(shipped_files(root, SHIP))
    warns = scan(shipped_files(root, VENDORED))
    return report("deleted-things", hits, warns)

def crit_inv_refs(root):
    inv_file = root / "rules" / "content-invariants.md"
    defined = set(re.findall(r"\*\*INV-(\d{1,2})\.\*\*", inv_file.read_text())) if inv_file.exists() else set()
    hits = []
    for f in shipped_files(root, SHIP):
        if f == inv_file: continue
        for n, ln in lines_of(f):
            for m in INV_REF.finditer(ln):
                num = m.group(1); tag = f"INV-{num}"
                if num not in defined:
                    hits.append(f"{f.relative_to(root)}:{n}: {tag} is not defined")
                elif tag in INV_RETIRED and "RETIRED" not in ln and "retired" not in ln:
                    hits.append(f"{f.relative_to(root)}:{n}: {tag} is retired")
    return report("inv-refs", hits)

def crit_skill_refs(root):
    skills = set()
    for d in ["skills", "submodules/ai-audit/skills", "zotpilot-skills"]:
        p = root / d
        if p.is_dir():
            skills |= {c.name for c in p.iterdir() if c.is_dir() and (c / "SKILL.md").exists()}
    hits = []
    for f in shipped_files(root, SHIP):
        for n, ln in lines_of(f):
            for m in SLASH.finditer(ln):
                tok = m.group(1)
                if tok in skills or tok in SLASH_ALLOW: continue
                hits.append(f"{f.relative_to(root)}:{n}: /{tok} names no skill")
    return report("skill-refs", hits)

def crit_tool_name(root):
    hits = []
    for f in shipped_files(root, ["agents", "skills"]):
        for n, ln in lines_of(f):
            m = TOOLS_LINE.match(ln)
            if m and re.search(r"\bTask\b", m.group(2)):
                hits.append(f"{f.relative_to(root)}:{n}: Task in tools line (use Agent)")
    return report("tool-name", hits)

def crit_hooks_readme(root):
    readme = root / "hooks" / "README.md"
    hits = []
    if not readme.exists():
        return report("hooks-readme", ["hooks/README.md missing"])
    rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|", readme.read_text(), re.M)
    for name, event in rows:
        hook = root / "hooks" / name
        if not hook.exists():
            hits.append(f"hooks/README.md: row for {name} but hooks/{name} does not exist"); continue
        m = re.search(r"Hook Event:\s*([A-Za-z|]+)", hook.read_text(errors="ignore"))
        if not m:
            hits.append(f"hooks/{name}: no 'Hook Event: <Event>' line"); continue
        if event.split()[0].strip("*`") != m.group(1).split("|")[0]:
            hits.append(f"hooks/README.md: {name} row says '{event}', hook says '{m.group(1)}'")
        if event.lower().startswith("git"):
            hits.append(f"hooks/README.md: {name} is a git hook listed in the Claude hook table")
    return report("hooks-readme", hits)

CRITERIA = {
    "latex-residue": crit_latex_residue, "manuscript-model": crit_manuscript_model,
    "deleted-things": crit_deleted_things, "inv-refs": crit_inv_refs, "skill-refs": crit_skill_refs,
    "tool-name": crit_tool_name, "hooks-readme": crit_hooks_readme,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--criterion", choices=sorted(CRITERIA) + ["all"], default="all")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    names = sorted(CRITERIA) if a.criterion == "all" else [a.criterion]
    rc = 0
    for n in names:
        rc |= CRITERIA[n](root)
    sys.exit(rc)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run every criterion, read every hit, record the red**

```bash
cd "$W" && for c in latex-residue manuscript-model deleted-things inv-refs skill-refs tool-name hooks-readme; do python3 scripts/check_refs.py --root . --criterion $c; done 2>&1 | tee -a docs/audits/2026-09-08_stage0-red.md | grep -cE '^    '
```
Expected: every criterion prints FAIL. Cross-check the hit set against the sweep: `latex-residue` should list every §1–§5 row that matches the pattern; `deleted-things` must include `skills/discover/SKILL.md` (Librarian), `agents/writer-critic.md` (Orchestrator, INV-22), `skills/tools/SKILL.md` (clo-author, `guide/`), `references/prompt-formatting-core.md` (absent skills), `references/discipline-cards.md` (`/research-ideation` etc.); `inv-refs` must include `agents/coder-critic.md` (INV-26, INV-28 in Rmd Mode) and `references/coding-standards-rmd.md`; `tool-name` must list every phase skill's `allowed-tools` line; `hooks-readme` must list `session-guard.py` (SessionStart vs PreToolUse), `post-compact-restore.py` (PostCompact), `post-merge.sh` (git). **Every hit in a file the sweep marked clean is a sweep gap → Addendum.** Any FALSE POSITIVE (a `/token` that is a shell path, say) is fixed in `SLASH_ALLOW` now, with the reason in the commit message.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add scripts/check_refs.py docs/audits/2026-09-08_stage0-red.md docs/audits/2026-09-08_full-tree-sweep.md
git commit -m "test(check_fork): check_refs.py — seven text criteria, all red against the tree"
```

### Task 0.6: `scripts/check_paths.py` — `path-resolves`, written failing

**Files:**
- Create: `scripts/check_paths.py`

**Interfaces:**
- Produces: `python3 scripts/check_paths.py --root DIR [--list]`. FAIL rows for (a) a `.claude/<dir>/<rest>` reference that does not resolve per the table below, (b) an un-prefixed pipeline path (`templates/X`, `references/X`, `skills/X`, `agents/X`, `rules/X`, `scripts/X`, `hooks/X`) outside the project-level exempt set. `--list` prints every reference and its resolution (the Stage 3 inventory). WARN for vendored trees.

Resolution table (spec §11):

| reference | resolves if any exists |
|---|---|
| `.claude/skills/X` | `skills/X`, `submodules/ai-audit/skills/X`, `zotpilot-skills/X` |
| `.claude/agents/X` | `agents/X`, `submodules/ai-audit/agents/X` |
| `.claude/rules/X` | `rules/X`, `submodules/ai-audit/rules/X` |
| `.claude/references/X` | `references/X` |
| `.claude/templates/X` | `templates/X` |
| `.claude/scripts/X` | `scripts/X` and `X` listed in `scripts/SHIPPED` |
| `.claude/hooks/X` | `hooks/X` |

Project-level exempt set (never rewritten, never checked): anything starting with `data/`, `quality_reports/`, `talks/`, `explorations/`, `scripts/acquire/`, `master_supporting_docs/`, `.claude/state/`, `.claude/settings`, `.claude/pipeline.lock`; and exactly these project templates: `templates/quarto-preamble.tex`, `templates/word-reference.docx`, `templates/ai-use-log.md`, `templates/apa.csl`.

- [ ] **Step 1: Write the checker**

```python
#!/usr/bin/env python3
"""check_paths.py — D-4 path gate for check_fork.sh (stdlib, Python 3.9).

Every pipeline path in a shipped file must be `.claude/`-prefixed and resolve through the
table in RESOLVE. Bare pipeline paths (templates/X, skills/X, ...) fail unless they are in
the project-level exempt set. --list prints the full inventory (Stage 3 uses it).
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

SHIP = ["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]
VENDORED = ["zotpilot-skills", "submodules/ai-audit"]
RESOLVE = {
    "skills":     ["skills", "submodules/ai-audit/skills", "zotpilot-skills"],
    "agents":     ["agents", "submodules/ai-audit/agents"],
    "rules":      ["rules", "submodules/ai-audit/rules"],
    "references": ["references"],
    "templates":  ["templates"],
    "scripts":    ["scripts"],
    "hooks":      ["hooks"],
}
EXEMPT_PREFIX = ("data/", "quality_reports/", "talks/", "explorations/", "scripts/acquire/",
                 "master_supporting_docs/", ".claude/state/", ".claude/settings", ".claude/pipeline.lock")
EXEMPT_EXACT = {"templates/quarto-preamble.tex", "templates/word-reference.docx",
                "templates/ai-use-log.md", "templates/apa.csl"}
# A path token: optional .claude/ prefix, one of the pipeline dirs, then a file-ish tail.
PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])((?:\.claude/)?(?:skills|agents|rules|references|templates|scripts|hooks)/[A-Za-z0-9_./-]*[A-Za-z0-9_])")
MARK = re.compile(r"<!-- residue:(prohibition|historical) -->\s*$")

def files(root, dirs):
    for d in dirs:
        p = root / d
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in {".md", ".py", ".sh", ".json", ".R", ".qmd", ".yaml", ".tex"} and ".git" not in f.parts:
                    yield f

def shipped_scripts(root):
    p = root / "scripts" / "SHIPPED"
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()} if p.exists() else set()

def resolve(root, ref, shipped):
    tail = ref[len(".claude/"):]
    top, _, rest = tail.partition("/")
    for base in RESOLVE.get(top, []):
        if (root / base / rest).exists():
            if top == "scripts" and rest not in shipped:
                return False
            return True
    return False

def check(root, dirs, warn=False):
    shipped = shipped_scripts(root)
    rows = []
    for f in files(root, dirs):
        text = f.read_text(errors="ignore")
        lines = text.split("\n")
        if lines and lines[0].strip() == "<!-- residue:historical -->":
            continue
        for i, ln in enumerate(lines, 1):
            if MARK.search(ln): continue
            for m in PATH_RE.finditer(ln):
                ref = m.group(1)
                if ref.startswith(EXEMPT_PREFIX) or ref in EXEMPT_EXACT: continue
                # a skill's own relative path is NOT exempt (D-4: rewrite skill-relative references too)
                if ref.startswith(".claude/"):
                    status = "ok" if resolve(root, ref, shipped) else "UNRESOLVED"
                else:
                    status = "UNPREFIXED"
                rows.append((str(f.relative_to(root)), i, ref, status))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--list", action="store_true")
    a = ap.parse_args(); root = Path(a.root).resolve()
    rows = check(root, SHIP)
    bad = [r for r in rows if r[3] != "ok"]
    if a.list:
        for r in rows: print(f"{r[0]}:{r[1]}: {r[2]} -> {r[3]}")
        print(f"total={len(rows)} unresolved={sum(r[3]=='UNRESOLVED' for r in rows)} unprefixed={sum(r[3]=='UNPREFIXED' for r in rows)}")
    if bad:
        print("FAIL [path-resolves]")
        for r in bad: print(f"    {r[0]}:{r[1]}: {r[2]} ({r[3]})")
    else:
        print("PASS [path-resolves]")
    for r in check(root, VENDORED):
        if r[3] != "ok": print(f"WARN [path-resolves] vendored {r[0]}:{r[1]}: {r[2]} ({r[3]})")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the inventory and record the red**

```bash
cd "$W" && python3 scripts/check_paths.py --root . --list | tail -1
python3 scripts/check_paths.py --root . >> docs/audits/2026-09-08_stage0-red.md; echo "exit=$?"
```
Expected: `total≈150 unresolved≈66 unprefixed≈44+` (audit F4: 66 dangling; review D4: ~44 skill-relative references that resolved only skill-relatively; D-4 counts both — ≈110). `exit=1`. Read the full `--list` output once: every `UNRESOLVED` row should be in audit F4's three classes (mis-pathed, genuinely absent, illustrative example). Illustrative examples like `scripts/R/FILENAME.R` will disappear in 3b; they are not exempted.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add scripts/check_paths.py docs/audits/2026-09-08_stage0-red.md
git commit -m "test(check_fork): check_paths.py — D-4 resolution table, ~110 references red"
```

### Task 0.7: Rewrite `scripts/check_fork.sh` — every criterion present, D1 block inverted, new criteria red

**Files:**
- Modify: `scripts/check_fork.sh` (full rewrite; keep `scan`, `absent`, `contains`, the identity/noun scans, `cc-*-half`, `course-leak`)

- [ ] **Step 1: Replace the file**

```bash
#!/usr/bin/env bash
# check_fork.sh — the TEMPLATE gate. Exit 0 = the shipped tree is complete, generic and
# conforms to the one-manuscript contract. Every criterion below was red-tested against
# the tree or the fixture before its green was trusted (docs/audits/2026-09-08_stage0-red.md).
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
SHIP=(agents skills rules references hooks templates seeds scripts)

scan() {  # scan <label> <ERE> [dir...]
  local label="$1" pat="$2"; shift 2
  local hits present=() dirs=("$@"); [[ ${#dirs[@]} -eq 0 ]] && dirs=("${SHIP[@]}")
  local d; for d in "${dirs[@]}"; do [[ -d "$RC/$d" ]] && present+=("$d"); done
  hits="$(cd "$RC" && grep -rInE "$pat" "${present[@]}" 2>/dev/null | grep -v 'residue:historical' )"
  if [[ -n "$hits" ]]; then echo "FAIL [$label]"; printf '%s\n' "$hits" | sed 's/^/    /'; fail=1
  else echo "PASS [$label]"; fi
}
absent()  { if [[ -e "$RC/$2" ]]; then echo "FAIL [$1] $2 still present"; fail=1; else echo "PASS [$1] $2 gone"; fi; }
present() { if [[ -e "$RC/$2" ]]; then echo "PASS [$1] $2 present"; else echo "FAIL [$1] $2 missing"; fail=1; fi; }
contains(){ if [[ -f "$RC/$2" ]] && grep -q "$3" "$RC/$2"; then echo "PASS [$1]"; else echo "FAIL [$1] $2 missing /$3/"; fail=1; fi; }
py() {  # py <script> [args] — run a python criterion, fold its exit into $fail
  if [[ ! -f "$RC/scripts/$1" ]]; then echo "FAIL [$1] scripts/$1 absent"; fail=1; return; fi
  local s="$1"; shift; python3 "$RC/scripts/$s" --root "$RC" "$@" || fail=1
}

echo "── identity: nothing project-specific ships ──"
scan project-identity 'POGM|SFPP|WRLURI|zoning2026|NAR_settlement|manuscript_quarto_word' "${SHIP[@]}" tests
scan project-nouns    'JREPM|JRER|CoStar|[^a-z]zoning|WRLURI|[^A-Za-z]NAR[^A-Za-z]' agents skills rules hooks templates seeds scripts
scan course-leak      'academic course materials|Beamer slides|TikZ Freshness'

echo "── structure ──"
absent clo-author-submodule submodules/clo-author
absent pipeline-precedence  rules/pipeline-precedence.md
grep -q 'clo-author' "$RC/.gitmodules" 2>/dev/null && { echo "FAIL [gitmodules]"; fail=1; } || echo "PASS [gitmodules]"
grep -q 'CLO_SKIP_SKILLS' "$RC/apply.sh" 2>/dev/null && { echo "FAIL [apply.sh]"; fail=1; } || echo "PASS [apply.sh]"
contains cc-zoning-half agents/coder-critic.md 'Correctness Layer'
contains cc-pogm-half   agents/coder-critic.md 'INV-23'

echo "── D1 inverted: the registry, lifecycle and governance are back; the agent is not ──"
for p in rules/registry.yaml rules/permissions.md rules/lifecycle.md rules/meta-governance.md \
         agents/lit-critic.md skills/pipeline/SKILL.md scripts/pipeline.py scripts/registry_lib.py \
         hooks/dispatch-log.py hooks/critic-pairing.py tests/run_fixture.sh templates/pipeline-state.json \
         templates/journal-profile-template.md seeds/quarto-preamble.tex scripts/SHIPPED; do present d1-restored "$p"; done
for g in agents/orchestrator.md agents/guide-writer.md agents/librarian.md agents/librarian-critic.md \
         rules/workflow.md rules/working-paper-format.md rules/html-dashboard.md skills/dashboard \
         references/coding-standards-rmd.md references/prompt-formatting-core.md hooks/post-merge.sh \
         skills/analyze/templates/r-script-structure.R skills/analyze/templates/python-script-structure.py \
         skills/analyze/templates/results-summary.md skills/submit/templates/cover-letter.tex root-skills; do absent d1-deletions "$g"; done

echo "── text criteria (scripts/check_refs.py) ──"
for c in latex-residue manuscript-model deleted-things inv-refs skill-refs tool-name hooks-readme; do
  py check_refs.py --criterion "$c"
done

echo "── path layer (scripts/check_paths.py) ──"
py check_paths.py

echo "── registry (scripts/pipeline.py registry check) ──"
py pipeline.py registry check    # prints PASS/FAIL for registry-complete, registry-authority, registry-rendered, weights-sum, registry-parse-agree

echo "── seeds and shipped scripts ──"
if grep -rq 'quarto-preamble\.tex' "$RC/rules" && [[ ! -f "$RC/seeds/quarto-preamble.tex" ]]; then
  echo "FAIL [seeds-complete] rules require templates/quarto-preamble.tex but seeds/ does not ship it"; fail=1
else echo "PASS [seeds-complete]"; fi
if [[ -f "$RC/scripts/SHIPPED" ]]; then
  while read -r s; do [[ -z "$s" || -f "$RC/scripts/$s" ]] || { echo "FAIL [scripts-manifest] $s listed but absent"; fail=1; }; done < "$RC/scripts/SHIPPED"
  echo "PASS [scripts-manifest]"
else echo "FAIL [scripts-manifest] scripts/SHIPPED missing"; fail=1; fi

echo "── fixture ──"
if [[ -x "$RC/tests/run_fixture.sh" ]]; then "$RC/tests/run_fixture.sh" >/tmp/run_fixture.$$ 2>&1 && echo "PASS [fixture]" || { echo "FAIL [fixture]"; tail -15 /tmp/run_fixture.$$ | sed 's/^/    /'; fail=1; }; rm -f /tmp/run_fixture.$$
else echo "FAIL [fixture] tests/run_fixture.sh missing"; fail=1; fi

[[ $fail -eq 0 ]] && echo "✓ check_fork: PASS" || echo "✗ check_fork: FAIL"
exit $fail
```

- [ ] **Step 2: Run it; read the whole output; record**

```bash
cd "$W" && ./scripts/check_fork.sh > /tmp/cf0.txt 2>&1; echo "exit=$?"; grep -cE '^(FAIL|PASS)' /tmp/cf0.txt; grep -E '^FAIL' /tmp/cf0.txt
```
Expected: `exit=1`. PASS: `project-identity`, `project-nouns`, `course-leak`, the four structure rows, `cc-*-half`, and the `d1-deletions` rows for files that are already absent (orchestrator, guide-writer, librarian, librarian-critic, workflow, working-paper-format, root-skills). FAIL: every `d1-restored` row (15), the `d1-deletions` rows for files that still exist (html-dashboard, dashboard, coding-standards-rmd, prompt-formatting-core, post-merge.sh, the three analyze templates, cover-letter.tex), all seven text criteria, `path-resolves`, `pipeline.py` (absent), `seeds-complete`, `scripts-manifest`, `fixture`. Append `/tmp/cf0.txt` to `docs/audits/2026-09-08_stage0-red.md` under `## check_fork.sh`.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add scripts/check_fork.sh docs/audits/2026-09-08_stage0-red.md
git commit -m "test(check_fork): all repair criteria present and red; D1 block inverted (registry/lifecycle return, agent stays gone)"
```

### Task 0.8: `check_install.sh` gains `branch` now (B5)

**Files:**
- Modify: `scripts/check_install.sh` (insert after the `ok checkout "$RC"` line)

- [ ] **Step 1: Add the check**

```bash
  # ── 0. The shared checkout is on main or a detached lock SHA ─────────────
  # Any `git checkout <branch>` in the shared tree re-points all six papers at once.
  # Set RESEARCH_CLAUDE_ALLOW_BRANCH=1 only while a named canary is deliberately linked
  # to a worktree; that downgrades the FAIL to a named WARN.
  local br_rc; br_rc="$(git -C "$RC" symbolic-ref -q --short HEAD 2>/dev/null || echo DETACHED)"
  if [[ "$br_rc" == "main" ]]; then ok branch "checkout on main"
  elif [[ "$br_rc" == "DETACHED" && "$(git -C "$RC" rev-parse HEAD)" == "$(sed -n 's/^commit=//p' "$P/.claude/pipeline.lock" 2>/dev/null)" ]]; then ok branch "detached at the lock SHA"
  elif [[ "${RESEARCH_CLAUDE_ALLOW_BRANCH:-0}" == "1" ]]; then warn branch "checkout on '$br_rc' — allowed by RESEARCH_CLAUDE_ALLOW_BRANCH=1"
  else bad branch "checkout is on '$br_rc', not main and not the lock SHA"; fi
```

- [ ] **Step 2: Red-test it against a branch checkout, then green against the fleet**

```bash
# red: a scratch project linked to $W (which is on repair/pipeline)
S="$(mktemp -d)"; cp -R "$W/tests/fixture-project/." "$S/"; "$W/apply.sh" --project-dir "$S" --link >/dev/null
"$W/scripts/check_install.sh" --project-dir "$S" | grep -E '\[branch\]'          # expect: FAIL [branch] checkout is on 'repair/pipeline'
RESEARCH_CLAUDE_ALLOW_BRANCH=1 "$W/scripts/check_install.sh" --project-dir "$S" | grep -E '\[branch\]'   # expect: WARN [branch]
rm -rf "$S"
# green: the six repos still link to $RC on main
"$W/scripts/check_install.sh" --all | grep -E '\[branch\]' | sort | uniq -c                          # expect: 6 × PASS [branch] checkout on main
```

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add scripts/check_install.sh && git commit -m "feat(check_install): branch check — shared checkout must be on main or the lock SHA (B5)"
```

### Task 0.9: Stage 0 sign-off

- [ ] **Step 1: Confirm the red record is complete**

`docs/audits/2026-09-08_stage0-red.md` must have four sections: `## run_fixture.sh`, `## check_refs.py`, `## check_paths.py`, `## check_fork.sh`, each with verbatim output and a one-line "why this is red" note. Add a fifth, `## Vacuous reds`, listing `pre-writer-red` (script absent) and `py pipeline.py` (script absent) so Stage 1 knows those greens need their own red.

- [ ] **Step 2: Graph delta check**

```bash
cd "$W" && python3 scripts/audit_graph.py . /tmp/g0.json | head -3
```
Expected: `dangling path refs : 66` — Stage 0 must not have moved it (the fixture is under `tests/`, outside `SHIP`). If it moved, find out why before continuing (stop condition).

- [ ] **Step 3: Commit the record**

```bash
cd "$W" && git add docs/audits/2026-09-08_stage0-red.md && git commit -m "docs(audit): Stage 0 red record complete"
```

---

## Stage 1 — Contracts: registry, lifecycle, quality, governance, `pipeline.py`

**Exit criteria:** `rules/registry.yaml` parses with `registry_lib.py` and (dev env) identically with PyYAML; `rules/permissions.md` is rendered and `registry-rendered` is green; `weights-sum`, `registry-complete` green; `registry-authority` still red (agents.md §1 table and quality.md weights prose are rewritten here, but the rest of the tree still states pairs — Stage 3b/4 clear it); `pipeline.py` passes `tests/test_pipeline.py` with each predicate shown red then green; `rules/lifecycle.md`, `rules/quality.md`, `rules/meta-governance.md`, `rules/agents.md` rewritten; D1 decision record superseded.

Two predicate types are added to spec §5's table because the registry needs them: `any_of` (P-16: strategist requires literature **or** data assessment, as the archived registry declared) and `chunk` (P-17: coder produces `tbl-`/`fig-` chunks, which no `path`/`section` predicate can see). `prose-check` is P-7. All three are listed in `rules/lifecycle.md`.

### Task 1.1: `rules/registry.yaml`

**Files:**
- Create: `rules/registry.yaml`

**Interfaces:**
- Produces: the schema every later task reads. Top-level keys `schema_version`, `limits`, `components`, `agents`. Per agent: `role` (creator|critic|referee|infrastructure), `kind` (agent|skill), `parallel_group`, `requires` (list of predicates), `produces` (list of predicates), `critic` (agent name or `none`), `escalation_target` (`user` or an agent name), `component` (a components key or `none`), `quality_weight` (number), `conditional` (bool), `writes` (list of project-relative path prefixes; `manuscript` means the declared manuscript), optional `scored_under`. Predicate shapes: `{type: path, glob, min?, producer?}`, `{type: section, file, heading}` (`file: manuscript` = declared manuscript), `{type: score, component, min}` (`component: overall` allowed), `{type: fresh}`, `{type: render, file?}` (`file` defaults to the manuscript; a glob for talks), `{type: critic-ran}` (auto-added at post for any agent whose `critic` is not `none`; may also be declared explicitly), `{type: prose-check}`, `{type: chunk, label_glob, min}`, `{type: any_of, of: [predicates]}`.

- [ ] **Step 1: Write the registry**

```yaml
# rules/registry.yaml — the declaration registry (D-2, D-10). AUTHORITATIVE.
# Rendered to rules/permissions.md by scripts/render_registry.py (check_fork: registry-rendered).
# Read by scripts/pipeline.py, scripts/check_fork.sh and skills/pipeline/SKILL.md.
# No other file states a creator→critic pair or a weight (check_fork: registry-authority).
#
# Restricted YAML on purpose (parsed by scripts/registry_lib.py without PyYAML): block
# mappings, block lists, single-line scalars, `[]` for an empty list, `#` comments.
# No anchors, no flow collections, no multi-line strings.
schema_version: 1

limits:
  rounds_per_pair: 3
  rounds_overall: 5
  verification_retries: 2

# Quality components (rules/quality.md mirrors these weights; check_fork: weights-sum).
components:
  literature:
    weight: 10
    scored_by: lit-critic
  data:
    weight: 10
    scored_by: explorer-critic
  strategy:
    weight: 25
    scored_by: strategist-critic
  theory:
    weight: 20
    scored_by: theorist-critic
    conditional: true
  code:
    weight: 15
    scored_by: coder-critic
  manuscript:
    weight: 10
    scored_by: writer-critic
  referees:
    weight: 25
    scored_by: editor
  replication:
    weight: 5
    scored_by: verifier

agents:

  # ── Discovery ────────────────────────────────────────────────────────────
  lit-position:
    role: creator
    kind: skill
    parallel_group: discovery
    requires: []
    produces:
      - type: path
        glob: quality_reports/literature/*/annotated_bibliography.md
      - type: path
        glob: quality_reports/literature/*/frontier_map.md
      - type: path
        glob: quality_reports/literature/*/positioning.md
    critic: lit-critic
    escalation_target: user
    component: literature
    quality_weight: 10
    conditional: false
    writes:
      - quality_reports/literature/

  lit-critic:
    role: critic
    kind: agent
    parallel_group: discovery
    requires:
      - type: path
        glob: quality_reports/literature/*/positioning.md
        producer: /lit-position
    produces:
      - type: path
        glob: quality_reports/reviews/lit-critic_*.md
    critic: none
    escalation_target: user
    component: literature
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  explorer:
    role: creator
    kind: agent
    parallel_group: discovery
    requires: []
    produces:
      - type: path
        glob: quality_reports/data-assessment/*/data_sources.md
      - type: path
        glob: quality_reports/data-assessment/*/data_dictionary.md
      - type: path
        glob: quality_reports/data-assessment/*/access_instructions.md
    critic: explorer-critic
    escalation_target: user
    component: data
    quality_weight: 10
    conditional: false
    writes:
      - quality_reports/data-assessment/

  explorer-critic:
    role: critic
    kind: agent
    parallel_group: discovery
    requires:
      - type: path
        glob: quality_reports/data-assessment/*/data_sources.md
        producer: /discover data
    produces:
      - type: path
        glob: quality_reports/reviews/explorer-critic_*.md
    critic: none
    escalation_target: user
    component: data
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  # ── Strategy ─────────────────────────────────────────────────────────────
  strategist:
    role: creator
    kind: agent
    parallel_group: strategy
    requires:
      - type: any_of
        of:
          - type: path
            glob: quality_reports/literature/*/positioning.md
            producer: /lit-position
          - type: path
            glob: quality_reports/data-assessment/*/data_sources.md
            producer: /discover data
    produces:
      - type: path
        glob: quality_reports/strategy/*/strategy_memo.md
      - type: section
        file: quality_reports/strategy/*/strategy_memo.md
        heading: Estimand
      - type: section
        file: quality_reports/strategy/*/strategy_memo.md
        heading: Specification
      - type: section
        file: quality_reports/strategy/*/strategy_memo.md
        heading: Assumptions
      - type: section
        file: quality_reports/strategy/*/strategy_memo.md
        heading: Robustness Plan
      - type: section
        file: quality_reports/strategy/*/strategy_memo.md
        heading: Threats
    critic: strategist-critic
    escalation_target: user
    component: strategy
    quality_weight: 25
    conditional: false
    writes:
      - quality_reports/strategy/

  strategist-critic:
    role: critic
    kind: agent
    parallel_group: strategy
    requires:
      - type: path
        glob: quality_reports/strategy/*/strategy_memo.md
        producer: /strategize
    produces:
      - type: path
        glob: quality_reports/reviews/strategist-critic_*.md
    critic: none
    escalation_target: user
    component: strategy
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  theorist:
    role: creator
    kind: agent
    parallel_group: strategy
    requires:
      - type: score
        component: strategy
        min: 80
    produces:
      - type: section
        file: manuscript
        heading: Theory
      - type: path
        glob: quality_reports/theory/*/theory_memo.md
      - type: path
        glob: quality_reports/theory/*/notation_glossary.md
      - type: render
    critic: theorist-critic
    escalation_target: user
    component: theory
    quality_weight: 20
    conditional: true
    writes:
      - manuscript
      - quality_reports/theory/

  theorist-critic:
    role: critic
    kind: agent
    parallel_group: strategy
    requires:
      - type: section
        file: manuscript
        heading: Theory
        producer: /strategize theory
    produces:
      - type: path
        glob: quality_reports/reviews/theorist-critic_*.md
    critic: none
    escalation_target: user
    component: theory
    quality_weight: 0
    conditional: true
    writes:
      - quality_reports/reviews/

  # ── Execution ────────────────────────────────────────────────────────────
  data-engineer:
    role: creator
    kind: agent
    parallel_group: execution
    requires:
      - type: score
        component: strategy
        min: 80
    produces:
      - type: path
        glob: data/raw/data_manifest.md
      - type: render
    critic: coder-critic
    escalation_target: strategist-critic
    component: code
    quality_weight: 0
    scored_under: code
    conditional: false
    writes:
      - manuscript
      - data/raw/data_manifest.md

  coder:
    role: creator
    kind: agent
    parallel_group: execution
    requires:
      - type: score
        component: strategy
        min: 80
    produces:
      - type: chunk
        label_glob: tbl-*
        min: 1
      - type: chunk
        label_glob: fig-*
        min: 1
      - type: render
      - type: prose-check
    critic: coder-critic
    escalation_target: strategist-critic
    component: code
    quality_weight: 15
    conditional: false
    writes:
      - manuscript

  coder-critic:
    role: critic
    kind: agent
    parallel_group: execution
    requires:
      - type: chunk
        label_glob: tbl-*
        min: 1
        producer: /analyze
    produces:
      - type: path
        glob: quality_reports/reviews/coder-critic_*.md
    critic: none
    escalation_target: strategist-critic
    component: code
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  writer:
    role: creator
    kind: agent
    parallel_group: execution
    requires:
      - type: score
        component: code
        min: 80
      - type: chunk
        label_glob: tbl-*
        min: 1
        producer: /analyze
      - type: render
    produces:
      - type: render
      - type: prose-check
    critic: writer-critic
    escalation_target: user
    component: manuscript
    quality_weight: 10
    conditional: false
    writes:
      - manuscript

  writer-critic:
    role: critic
    kind: agent
    parallel_group: execution
    requires:
      - type: render
        producer: /write
    produces:
      - type: path
        glob: quality_reports/reviews/writer-critic_*.md
      - type: path
        glob: quality_reports/reviews/claim_evidence_*.md
    critic: none
    escalation_target: user
    component: manuscript
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  # ── Peer review ──────────────────────────────────────────────────────────
  editor:
    role: infrastructure
    kind: agent
    parallel_group: peer-review
    requires:
      - type: score
        component: manuscript
        min: 80
      - type: score
        component: code
        min: 80
    produces:
      - type: path
        glob: quality_reports/peer_review_*/desk_review.md
      - type: path
        glob: quality_reports/peer_review_*/editorial_decision.md
    critic: none
    escalation_target: user
    component: referees
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/peer_review_

  domain-referee:
    role: referee
    kind: agent
    parallel_group: peer-review
    requires:
      - type: path
        glob: quality_reports/peer_review_*/desk_review.md
        producer: /review --peer
    produces:
      - type: path
        glob: quality_reports/peer_review_*/referee_domain.md
    critic: none
    escalation_target: editor
    component: referees
    quality_weight: 12.5
    conditional: false
    writes:
      - quality_reports/peer_review_

  methods-referee:
    role: referee
    kind: agent
    parallel_group: peer-review
    requires:
      - type: path
        glob: quality_reports/peer_review_*/desk_review.md
        producer: /review --peer
    produces:
      - type: path
        glob: quality_reports/peer_review_*/referee_methods.md
    critic: none
    escalation_target: editor
    component: referees
    quality_weight: 12.5
    conditional: false
    writes:
      - quality_reports/peer_review_

  # ── Presentation (advisory) ──────────────────────────────────────────────
  storyteller:
    role: creator
    kind: agent
    parallel_group: presentation
    requires:
      - type: score
        component: manuscript
        min: 80
    produces:
      - type: path
        glob: talks/*_talk.qmd
      - type: render
        file: talks/*_talk.qmd
    critic: storyteller-critic
    escalation_target: writer
    component: none
    quality_weight: 0
    conditional: false
    writes:
      - talks/

  storyteller-critic:
    role: critic
    kind: agent
    parallel_group: presentation
    requires:
      - type: path
        glob: talks/*_talk.qmd
        producer: /talk
    produces:
      - type: path
        glob: quality_reports/reviews/storyteller-critic_*.md
    critic: none
    escalation_target: writer
    component: none
    quality_weight: 0
    conditional: false
    writes:
      - quality_reports/reviews/

  # ── Submission ───────────────────────────────────────────────────────────
  verifier:
    role: infrastructure
    kind: agent
    parallel_group: submission
    requires:
      - type: score
        component: overall
        min: 95
    produces:
      - type: path
        glob: quality_reports/verification_report.md
      - type: render
      - type: prose-check
    critic: none
    escalation_target: user
    component: replication
    quality_weight: 5
    conditional: false
    writes:
      - quality_reports/verification_report.md
```

- [ ] **Step 2: Commit (parses in the next task)**

```bash
cd "$W" && git add rules/registry.yaml && git commit -m "feat(registry): rules/registry.yaml — 19 entries, seven fields, predicates, weights set A"
```

### Task 1.2: `scripts/registry_lib.py` — loader and validators (TDD)

**Files:**
- Create: `scripts/registry_lib.py`, `tests/test_registry_lib.py`

**Interfaces:**
- Produces: `load_yaml_subset(text) -> dict`; `load_registry(root: Path) -> dict`; `validate_registry(reg) -> list[str]` (problems; empty = complete); `weights_report(reg, quality_md_text) -> list[str]`; `parse_agree(root) -> str` (`PASS`/`FAIL`/`SKIP`); `component_weights(reg) -> dict`; `creators(reg)`, `critic_of(reg, agent)`.

- [ ] **Step 1: Failing tests first**

`tests/test_registry_lib.py`:
```python
import sys, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_lib as rl

class TestYamlSubset(unittest.TestCase):
    def test_nested_map_list_scalars(self):
        text = "a:\n  b: 1\n  c: [] \n  d:\n    - x\n    - y: 2\n      z: true\n# comment\ne: \"q: r\"\n"
        self.assertEqual(rl.load_yaml_subset(text),
                         {"a": {"b": 1, "c": [], "d": ["x", {"y": 2, "z": True}]}, "e": "q: r"})
    def test_floats_and_null(self):
        self.assertEqual(rl.load_yaml_subset("w: 12.5\nn: null\ns: none\n"), {"w": 12.5, "n": None, "s": "none"})

class TestRegistry(unittest.TestCase):
    def setUp(self): self.reg = rl.load_registry(ROOT)
    def test_roster_matches_agents_dir(self):
        roster = {p.stem for p in (ROOT / "agents").glob("*.md")}
        declared = {a for a, e in self.reg["agents"].items() if e["kind"] == "agent"}
        self.assertEqual(declared - roster, set(), "declared but no agent file")
        self.assertEqual(roster - declared, set(), "agent file but not declared")
    def test_complete(self): self.assertEqual(rl.validate_registry(self.reg), [])
    def test_creator_without_critic_fails(self):
        reg = rl.load_registry(ROOT); reg["agents"]["coder"]["critic"] = "none"
        self.assertTrue(any("coder" in p for p in rl.validate_registry(reg)))
    def test_weights_sum_100(self):
        w = rl.component_weights(self.reg)
        self.assertEqual(sum(v for k, v in w.items() if k != "theory"), 100)
    def test_weights_agree_with_quality_md(self):
        self.assertEqual(rl.weights_report(self.reg, (ROOT / "rules" / "quality.md").read_text()), [])
    def test_parse_agree(self): self.assertIn(rl.parse_agree(ROOT), ("PASS", "SKIP"))

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run to see it fail**

```bash
cd "$W" && python3 -m unittest tests/test_registry_lib.py 2>&1 | tail -3
```
Expected: `ModuleNotFoundError: No module named 'registry_lib'`.

- [ ] **Step 3: Implement**

`scripts/registry_lib.py`:
```python
#!/usr/bin/env python3
"""registry_lib.py — load and validate rules/registry.yaml (stdlib, Python 3.9).

The registry is written in a restricted YAML subset so hooks and gates can read it under
/usr/bin/python3 with no PyYAML: block mappings, block lists, single-line scalars, `[]`,
`#` comments. parse_agree() cross-checks against PyYAML when it is importable.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROLES = {"creator", "critic", "referee", "infrastructure"}
FIELDS = ["role", "kind", "parallel_group", "requires", "produces", "critic",
          "escalation_target", "component", "quality_weight", "conditional", "writes"]
PRED_TYPES = {"path", "section", "score", "fresh", "render", "critic-ran", "prose-check", "chunk", "any_of"}
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*:(\s|$)")

# ── restricted YAML ─────────────────────────────────────────────────────────
def _strip_comment(raw: str) -> str:
    if raw.lstrip().startswith("#"):
        return ""
    out, quote = [], None
    for i, ch in enumerate(raw):
        if quote:
            out.append(ch)
            if ch == quote: quote = None
        elif ch in "\"'":
            quote = ch; out.append(ch)
        elif ch == "#" and (i == 0 or raw[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()

def _scalar(s: str) -> Any:
    s = s.strip()
    if s == "[]": return []
    if s == "{}": return {}
    if s in ("null", "~", ""): return None
    if s == "true": return True
    if s == "false": return False
    if (s[0] == s[-1]) and s[0] in "\"'" and len(s) >= 2: return s[1:-1]
    if re.fullmatch(r"-?\d+", s): return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s): return float(s)
    return s

def load_yaml_subset(text: str) -> Any:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        s = _strip_comment(raw)
        if s.strip() == "": continue
        lines.append((len(s) - len(s.lstrip(" ")), s.strip()))
    if not lines: return {}
    val, i = _block(lines, 0, lines[0][0])
    if i != len(lines):
        raise ValueError(f"registry.yaml: unparsed content at line item {i}: {lines[i][1]!r}")
    return val

def _block(lines, i, indent):
    return _list(lines, i, indent) if lines[i][1].startswith("- ") or lines[i][1] == "-" else _map(lines, i, indent)

def _map(lines, i, indent):
    out: Dict[str, Any] = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        item = lines[i][1]
        if not KEY_RE.match(item):
            raise ValueError(f"registry.yaml: expected 'key:' got {item!r}")
        key, _, rest = item.partition(":")
        key = key.strip(); rest = rest.strip()
        if rest == "":
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                val, i = _block(lines, i + 1, lines[i + 1][0])
            else:
                val, i = None, i + 1
        else:
            val, i = _scalar(rest), i + 1
        out[key] = val
    return out, i

def _list(lines, i, indent):
    out: List[Any] = []
    while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ") or lines[i][1] == "-"):
        item = lines[i][1][1:].strip()
        if item == "":
            val, i = _block(lines, i + 1, lines[i + 1][0]); out.append(val); continue
        if KEY_RE.match(item):
            key, _, rest = item.partition(":")
            first: Dict[str, Any] = {}
            if rest.strip() == "" and i + 1 < len(lines) and lines[i + 1][0] > indent + 2:
                val, i = _block(lines, i + 1, lines[i + 1][0]); first[key.strip()] = val
            else:
                first[key.strip()] = _scalar(rest); i += 1
            if i < len(lines) and lines[i][0] == indent + 2 and not lines[i][1].startswith("- "):
                more, i = _map(lines, i, indent + 2); first.update(more)
            out.append(first); continue
        out.append(_scalar(item)); i += 1
    return out, i

# ── registry ────────────────────────────────────────────────────────────────
def registry_path(root: Path) -> Path:
    return Path(root) / "rules" / "registry.yaml"

def load_registry(root: Path) -> Dict[str, Any]:
    reg = load_yaml_subset(registry_path(root).read_text())
    if reg.get("schema_version") != 1:
        raise ValueError("registry.yaml: schema_version must be 1")
    return reg

def component_weights(reg) -> Dict[str, float]:
    return {k: float(v["weight"]) for k, v in reg["components"].items()}

def creators(reg) -> List[str]:
    return [a for a, e in reg["agents"].items() if e.get("role") == "creator"]

def critic_of(reg, agent: str) -> Optional[str]:
    c = reg["agents"].get(agent, {}).get("critic")
    return None if c in (None, "none") else c

def _check_pred(p, where, problems):
    if not isinstance(p, dict) or "type" not in p:
        problems.append(f"{where}: predicate is not a mapping with a type"); return
    t = p["type"]
    if t not in PRED_TYPES: problems.append(f"{where}: unknown predicate type {t!r}"); return
    need = {"path": ["glob"], "section": ["file", "heading"], "score": ["component", "min"],
            "chunk": ["label_glob", "min"], "any_of": ["of"]}.get(t, [])
    for k in need:
        if k not in p: problems.append(f"{where}: {t} predicate missing {k!r}")
    if t == "any_of":
        for j, q in enumerate(p.get("of") or []): _check_pred(q, f"{where}.of[{j}]", problems)
    if "producer" in p and not str(p["producer"]).startswith("/"):
        problems.append(f"{where}: producer must be a /skill invocation")

def validate_registry(reg) -> List[str]:
    problems: List[str] = []
    comps = set(reg.get("components", {}))
    agents = reg.get("agents", {})
    for name, e in agents.items():
        for f in FIELDS:
            if f not in e: problems.append(f"{name}: missing field {f}")
        if e.get("role") not in ROLES: problems.append(f"{name}: role must be one of {sorted(ROLES)}")
        if e.get("kind") not in ("agent", "skill"): problems.append(f"{name}: kind must be agent|skill")
        comp = e.get("component")
        if comp not in comps and comp != "none": problems.append(f"{name}: component {comp!r} not declared")
        crit = e.get("critic")
        w = float(e.get("quality_weight") or 0)
        if crit in (None, "none"):
            if e.get("role") == "creator" and w > 0:
                problems.append(f"{name}: creator with weight {w} has no critic")
        else:
            if crit not in agents: problems.append(f"{name}: critic {crit!r} is not a registry entry")
            elif agents[crit].get("role") != "critic": problems.append(f"{name}: critic {crit!r} does not have role critic")
        esc = e.get("escalation_target")
        if esc != "user" and esc not in agents: problems.append(f"{name}: escalation_target {esc!r} unknown")
        for j, p in enumerate(e.get("requires") or []): _check_pred(p, f"{name}.requires[{j}]", problems)
        for j, p in enumerate(e.get("produces") or []): _check_pred(p, f"{name}.produces[{j}]", problems)
        if not isinstance(e.get("writes"), list): problems.append(f"{name}: writes must be a list")
    for c, spec in reg.get("components", {}).items():
        sb = spec.get("scored_by")
        if sb not in agents: problems.append(f"components.{c}: scored_by {sb!r} unknown")
    return problems

QUALITY_ROW = re.compile(r"^\|\s*`?([a-z]+)`?\s*\|\s*([0-9.]+)\s*\|", re.M)

def weights_report(reg, quality_md: str) -> List[str]:
    problems: List[str] = []
    cw = component_weights(reg)
    cond = {k for k, v in reg["components"].items() if v.get("conditional")}
    base = sum(v for k, v in cw.items() if k not in cond)
    if abs(base - 100) > 1e-9: problems.append(f"non-conditional component weights sum to {base}, not 100")
    per_comp: Dict[str, float] = {}
    for a, e in reg["agents"].items():
        c = e.get("component")
        if c in cw: per_comp[c] = per_comp.get(c, 0.0) + float(e.get("quality_weight") or 0)
    for c, w in cw.items():
        if abs(per_comp.get(c, 0.0) - w) > 1e-9:
            problems.append(f"component {c}: agents declare {per_comp.get(c, 0.0)}, component says {w}")
    md = {m.group(1): float(m.group(2)) for m in QUALITY_ROW.finditer(quality_md)}
    for c, w in cw.items():
        if c not in md: problems.append(f"quality.md: no weight row for {c}")
        elif abs(md[c] - w) > 1e-9: problems.append(f"quality.md: {c} = {md[c]}, registry = {w}")
    return problems

def parse_agree(root: Path) -> str:
    text = registry_path(root).read_text()
    try:
        import yaml  # type: ignore
    except Exception:
        return "SKIP"
    return "PASS" if yaml.safe_load(text) == load_yaml_subset(text) else "FAIL"
```

- [ ] **Step 4: Run the tests**

```bash
cd "$W" && python3 -m unittest tests/test_registry_lib.py 2>&1 | tail -3
```
Expected: `test_weights_agree_with_quality_md` FAILS (quality.md has no weight table yet — Task 1.5 fixes it; this is the red for `weights-sum`), `test_roster_matches_agents_dir` FAILS (`lit-critic` declared, no file until Task 4.3 — this is the red for `registry-complete`'s roster half). All others pass. Also run with the system interpreter once: `/usr/bin/python3 -m unittest tests/test_registry_lib.py` → same result (proves 3.9 compatibility; `parse_agree` returns SKIP there).

- [ ] **Step 5: Commit**

```bash
cd "$W" && git add scripts/registry_lib.py tests/test_registry_lib.py && git commit -m "feat(registry): registry_lib.py — restricted-YAML loader, completeness and weight validators (two tests red by design)"
```

### Task 1.3: `scripts/render_registry.py` → `rules/permissions.md`

**Files:**
- Create: `scripts/render_registry.py`, `rules/permissions.md` (generated)

- [ ] **Step 1: Write the renderer**

```python
#!/usr/bin/env python3
"""render_registry.py — render rules/permissions.md from rules/registry.yaml.
  python3 scripts/render_registry.py --root .            # write
  python3 scripts/render_registry.py --root . --check    # exit 1 if the file differs
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_lib as rl

def pred(p) -> str:
    t = p["type"]
    if t == "path":    s = f"`{p['glob']}`" + (f" (≥{p['min']})" if p.get("min", 1) != 1 else "")
    elif t == "section": s = f"heading **{p['heading']}** in `{p['file']}`"
    elif t == "score":   s = f"{p['component']} score ≥ {p['min']}"
    elif t == "fresh":   s = "rendered output fresh"
    elif t == "render":  s = "`quarto render` exit 0" + (f" for `{p['file']}`" if p.get("file") else "")
    elif t == "critic-ran": s = "paired critic completed after the creator"
    elif t == "prose-check": s = "`prose_number_check.py` exit 0"
    elif t == "chunk":   s = f"≥{p['min']} chunk(s) labelled `{p['label_glob']}`"
    elif t == "any_of":  s = "any of: " + "; ".join(pred(q) for q in p["of"])
    else: s = t
    if p.get("producer"): s += f" — produced by `{p['producer']}`"
    return s

def render(reg) -> str:
    L = ["# Permission Registry (rendered — do not edit)", "",
         "Rendered from `rules/registry.yaml` by `scripts/render_registry.py`. `check_fork.sh`",
         "fails if this file differs from the render. The YAML is what `pipeline.py`, the gate",
         "and `/pipeline` read; this file exists so the registry is readable in a linked project.", "",
         f"**Limits:** {reg['limits']['rounds_per_pair']} rounds per pair, {reg['limits']['rounds_overall']} overall, "
         f"{reg['limits']['verification_retries']} verification retries.", "", "## Components", "",
         "| Component | Weight | Scored by | Conditional |", "|---|---|---|---|"]
    for c, s in reg["components"].items():
        L.append(f"| {c} | {s['weight']} | {s['scored_by']} | {'yes' if s.get('conditional') else 'no'} |")
    L += ["", "## Agents", ""]
    for a, e in reg["agents"].items():
        L += [f"### {a}", "",
              f"- **ROLE:** {e['role']} ({e['kind']}) · **PARALLEL_GROUP:** {e['parallel_group']}",
              "- **REQUIRES:** " + ("nothing beyond the research idea" if not e["requires"] else ""),]
        for p in e["requires"]: L.append(f"  - {pred(p)}")
        L.append("- **PRODUCES:**")
        for p in e["produces"]: L.append(f"  - {pred(p)}")
        L += [f"- **CRITIC:** {e['critic']}", f"- **ESCALATION_TARGET:** {e['escalation_target']}",
              f"- **QUALITY_WEIGHT:** {e['quality_weight']} ({e['component']})" + (f" — scored under {e['scored_under']}" if e.get("scored_under") else ""),
              f"- **CONDITIONAL:** {'yes' if e['conditional'] else 'no'}",
              "- **WRITES:** " + ", ".join(f"`{w}`" for w in e["writes"]), ""]
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(); root = Path(a.root)
    out = render(rl.load_registry(root)); dest = root / "rules" / "permissions.md"
    if a.check:
        same = dest.exists() and dest.read_text() == out
        print("PASS [registry-rendered]" if same else "FAIL [registry-rendered] rules/permissions.md differs from the render of registry.yaml")
        sys.exit(0 if same else 1)
    dest.write_text(out); print(f"wrote {dest}")

if __name__ == "__main__": main()
```

- [ ] **Step 2: Red, render, green**

```bash
cd "$W" && python3 scripts/render_registry.py --root . --check; echo "exit=$?"     # expect FAIL, exit=1 (file absent)
python3 scripts/render_registry.py --root . && python3 scripts/render_registry.py --root . --check; echo "exit=$?"   # expect PASS, exit=0
sed -n 1,30p rules/permissions.md
```

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add scripts/render_registry.py rules/permissions.md && git commit -m "feat(registry): render rules/permissions.md from registry.yaml; registry-rendered red then green"
```

### Task 1.4: `rules/lifecycle.md` — what `pipeline.py` does, in prose

**Files:**
- Create: `rules/lifecycle.md`

- [ ] **Step 1: Write it** (rewrite of the archived file against the executable; every claim names the subcommand)

```markdown
# Lifecycle: Handoff Validation

Validation between agents is **executable**, not prose. `python3 .claude/scripts/pipeline.py`
reads `.claude/rules/registry.yaml` and evaluates it; the `/pipeline` skill calls the script and
never evaluates a predicate itself. This file says what the script does so a reader of a linked
project can understand a refusal.

## PRE-dispatch — `pipeline.py pre <agent>`

Evaluates every `REQUIRES` predicate of the agent. On the first failure it prints the missing
artifact **and the skill that produces it** (the predicate's `producer`) and exits 1. The driver
does not dispatch. Standalone skills skip this step (spec §4, two modes) but nothing else.

## POST-completion — `pipeline.py post <agent>`

Evaluates every `PRODUCES` predicate, then `critic-ran` for any agent whose `CRITIC` is not
`none`. On failure it exits 1 and the driver does not advance or mark the agent complete.
**A creator cannot be marked complete without its critic's completion in the dispatch log and
its critic's score in the state file.** That is the structural fix for the defect that opened
this work.

## Predicate types

| Type | Passes when |
|---|---|
| `path` | the glob (relative to the project root) matches at least `min` files (default 1) |
| `section` | a Markdown heading with that text exists in the file (`file: manuscript` = the declared manuscript) |
| `score` | the latest score for the component in `quality_reports/pipeline_state.json` is ≥ `min`; `component: overall` uses the weighted aggregate |
| `fresh` | the rendered output is newer than the manuscript and every file under `data/raw/`; **render only when stale** |
| `render` | `quarto render <file>` exits 0 (the declared manuscript unless `file` is given) |
| `critic-ran` | `quality_reports/agent_dispatch.jsonl` shows the paired critic completing after the creator's last completion |
| `prose-check` | `python3 .claude/scripts/prose_number_check.py <manuscript>` exits 0 |
| `chunk` | at least `min` chunks in the declared manuscript have a `#| label:` matching `label_glob` |
| `any_of` | at least one of the listed predicates passes |

## State — `pipeline.py state <op>`

`init` creates `quality_reports/pipeline_state.json` (schema in `.claude/templates/pipeline-state.json`);
`validate` checks it; `record-score <component> <score> --critic <name> --report <path> [--scope section:<name>]`
records a critic score (latest per component counts; a section-scoped `writer-critic` score is
recorded under `sections`, never as the manuscript component); `strike <pair>` increments a pair's
strike count and prints the escalation target at three; `show` prints it. The state file is
committed — it is replication provenance. The dispatch log is gitignored — it is session mechanics.

## Score — `pipeline.py score [--gate commit|pr|submission]`

Weighted aggregate over scored components per `.claude/rules/quality.md`. Unscored components
are excluded and the remaining weights renormalised; `theory` counts only when scored
(`CONDITIONAL`). `--gate submission` exits 1 unless overall ≥ 95 and every scored component ≥ 80.

## Concurrency — `pipeline.py conflicts <agent> <agent> ...`

Exits 1 when two named agents' `WRITES` intersect. `coder`, `data-engineer`, `theorist` and
`writer` all write the manuscript, so they are never dispatched concurrently.

## Fail-fast

A refusal is a report, not a suggestion: the missing artifact, the producing skill, the exit code.
Never dispatch with missing inputs and hope; never advance past missing outputs.
```

- [ ] **Step 2: Commit**

```bash
cd "$W" && git add rules/lifecycle.md && git commit -m "feat(rules): lifecycle.md — handoff validation as a description of pipeline.py"
```

### Task 1.5: `rules/quality.md` — weights table, severity gradient retired (D-16)

**Files:**
- Modify: `rules/quality.md` (full rewrite)

- [ ] **Step 1: Replace the file**

```markdown
# Quality: Scoring and Thresholds

## 1. Weights

The overall score that gates submission is a weighted aggregate of critic scores. The weights
live here and in `.claude/rules/registry.yaml`; `check_fork.sh` (`weights-sum`) fails if the two
disagree or if the non-conditional weights do not sum to 100. `python3 .claude/scripts/pipeline.py score`
computes it; nothing else does.

| Component | Weight | Scored by |
|---|---|---|
| literature | 10 | lit-critic |
| data | 10 | explorer-critic |
| strategy | 25 | strategist-critic |
| theory | 20 | theorist-critic — `CONDITIONAL`: counted only when a theory section exists and was scored; the total renormalises from 120 |
| code | 15 | coder-critic (latest score over coder and data-engineer work) |
| manuscript | 10 | writer-critic (latest **whole-manuscript** score; section scores from `/write` are recorded separately) |
| referees | 25 | mean of domain-referee and methods-referee (12.5 each) |
| replication | 5 | verifier (PASS = 100, FAIL = 0) |

**Renormalisation.** A component with no score is excluded and the remaining weights are scaled
to sum to 100. An applied paper with no theory section therefore scores over exactly 100.

**Score sources.** Each critic starts at 100 and deducts per its rubric in
`.claude/skills/review/config/scoring-rubrics.md`. Latest score per component counts.
`quality_reports/pipeline_state.json` is authoritative; the research journal entry is written
from it, never the other way round.

## 2. Thresholds

| Gate | Overall | Per component | Enforced by |
|---|---|---|---|
| Commit | ≥ 80 | — | `pipeline.py score --gate commit` |
| PR | ≥ 90 | — | `pipeline.py score --gate pr` |
| Submission | ≥ 95 | every scored component ≥ 80 | `pipeline.py score --gate submission`, called by `/submit final` |

No component below 80 at submission. A perfect literature review cannot compensate for broken
identification.

## 3. Severity

Retired 2026-09-08 (R-2). Critics carry their own rubrics; no caller supplies a phase severity.
Reversible if the driver ever supplies one. <!-- residue:historical -->
```

- [ ] **Step 2: Run the weight test (was red in Task 1.2)**

```bash
cd "$W" && python3 -m unittest tests.test_registry_lib -k weights 2>&1 | tail -2
```
Expected: `test_weights_sum_100` and `test_weights_agree_with_quality_md` both `ok`.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add rules/quality.md && git commit -m "feat(rules): quality.md — weights set A, renormalisation, thresholds; severity gradient retired (R-2)"
```

### Task 1.6: `rules/meta-governance.md` (restored, de-Emoried), `rules/agents.md` (§1–§4), D1 decision superseded

**Files:**
- Create: `rules/meta-governance.md`, `docs/decisions/2026-09-08_d1-superseded.md`
- Modify: `rules/agents.md` (full rewrite), `docs/decisions/2026-09-08_cut-the-orchestration-graph.md` (status line only)

- [ ] **Step 1: `rules/meta-governance.md`**

```markdown
# Meta-Governance: Learning Promotion and Self-Modification

research-claude is one researcher's pipeline linked into every paper project. Anything in
`agents/`, `skills/`, `rules/`, `hooks/`, `templates/` or `seeds/` reaches every project, so a
change there is a decision, not a side effect.

## The one rule

Before committing to the shared tree, ask: **would every project linked to this pipeline be
better off with this?** Yes → commit through `/promote`. No → keep it in the project as a real
file override (a non-symlink under `.claude/`, with a negation line in `.gitignore`) or in
`.claude/state/`.

## Learning promotion

When a pattern has been validated across 3+ projects and the user confirms it:

| Pattern | Promotion target | Requires |
|---|---|---|
| PATTERN (replicable success) | best-practice line in the relevant agent's protocol | user approval |
| FRICTION (recurring three-strikes) | agent prompt revision or rubric adjustment | user approval |
| HIGH-PERF (consistent first-pass ≥ 90) | new content invariant or rule line | user approval |

**Protocol.** `/pipeline` surfaces "Suggested Learnings" at the end of a run from the dispatch log
and state file (recurring strikes, escalations to the user, first-pass ≥ 90). The user approves or
rejects each. An approved learning is landed upstream with `/promote`, which is the **only**
promotion mechanism.

**Constraint.** Promotion always requires user approval. The system suggests; the user decides.
No autonomous modification of rules, invariants, agent prompts or the registry.
```

- [ ] **Step 2: `rules/agents.md` (full rewrite)**

```markdown
# Agents: Pairs, Separation of Powers, Escalation, Dispatch Ownership

## 1. Adversarial pairing

**Every creator has a paired critic, declared in `.claude/rules/registry.yaml` and nowhere else.**
The dispatching skill dispatches the critic after the creator, every time, in every mode
(orchestrated or standalone). `python3 .claude/scripts/pipeline.py post <creator>` refuses to
mark a creator complete until the dispatch log shows its critic completing afterwards and the
state file carries the critic's score.

**Enforcement.**
- `pipeline.py post` — `critic-ran` predicate (structural).
- `.claude/hooks/critic-pairing.py` (Stop) — reads `quality_reports/agent_dispatch.jsonl` and
  surfaces a creator that ran without its critic in the current session.
- `check_fork.sh registry-complete` — no creator with a non-zero weight lacks a critic.

**Peer review** is the one asymmetric structure: the editor dispatches two blind referees and
synthesises a decision. Referees are already reviewers and have no critic (registry `role: referee`).

## 2. Separation of powers

**Critics never create. Creators never self-score.**

A critic scores against a rubric, lists issues with deductions, and recommends fixes as
recommendations. A critic that writes code, rewrites a section, or produces an alternative
implementation has failed its role. A creator's own assessment of its work is discarded; the
score always comes from the paired critic, recorded by the dispatching skill with
`pipeline.py state record-score`.

**Enforcement.** The dispatching skill flags: a critic dispatch that leaves a file under a
creator's `WRITES` prefix; a creator that reports a score.

## 3. Three-strikes escalation

Round 1: critic reviews → creator fixes. Round 2. Round 3. Still below threshold → escalate to
the `ESCALATION_TARGET` declared for the creator in the registry. `pipeline.py state strike
<creator>` counts rounds and prints the target at three.

- Max 3 rounds per pair per invocation; 5 rounds overall; never loop indefinitely.
- Escalation is logged in the research journal with the strike count.
- Escalating to the user requires a specific question: "strategist-critic requires X, which
  contradicts Y — which takes priority?", never "they disagree".
- After escalation the creator starts from the target's decision, not from its last attempt.

## 4. Dispatch ownership

The dependency graph lives in the registry (`REQUIRES` / `PRODUCES`), the loop lives in
`/pipeline`, and every stage skill owns its pair. Phases activate by `REQUIRES`, never by
sequence; re-entry is permitted everywhere except Submission. The coder↔writer cycle is normal
research, and the registry supports it: a referee comment routes to `coder → coder-critic →
writer → writer-critic` without restarting the pipeline.

| Skill | Dispatches | Then |
|---|---|---|
| `/lit-position` | (skill is the creator) | lit-critic |
| `/discover data` | explorer | explorer-critic |
| `/strategize` | strategist | strategist-critic |
| `/strategize theory` | theorist | theorist-critic |
| `/analyze` | data-engineer, coder | coder-critic (after each) |
| `/write` | writer | writer-critic (every mode that touches prose; `style-guide` exempt) |
| `/review` | critics only, by route | — |
| `/review --peer` | editor → domain-referee ∥ methods-referee → editor | — |
| `/revise` | writer or coder per comment | its critic |
| `/submit package` | coder | coder-critic |
| `/submit audit`, `/submit final` | verifier | — |
| `/talk` | storyteller | storyteller-critic |
| `/pipeline` | the skills above, in `REQUIRES` order, with `pipeline.py pre`/`post` around each | — |

Pairs, weights and escalation targets are **not** restated here. Read
`.claude/rules/permissions.md` (rendered from the registry).
```

- [ ] **Step 3: Supersede the D1 record**

Append to `docs/decisions/2026-09-08_cut-the-orchestration-graph.md`, directly under the `**Status:**` line:
```markdown
**Superseded in part 2026-09-08** by `2026-09-08_d1-superseded.md`: D1 stands for the *agent*; the registry, lifecycle and governance rules return. D3 stands for the *collector*; its critic returns as `lit-critic` (see `2026-09-08_d3-addendum-lit-critic.md`).
```

Create `docs/decisions/2026-09-08_d1-superseded.md`:
```markdown
# D1 superseded in part: the registry, lifecycle and governance return; the agent does not

**Date:** 2026-09-08 · **Status:** Decided (spec v2 §3, D-1, D-2, D-6, D-9, D-10)

**What changes.** `rules/permissions.md` (now rendered from `rules/registry.yaml`), `rules/lifecycle.md`
and `rules/meta-governance.md` are restored as rewrites against the archived clo-author files
(`~/Research/NAR_settlement_legacy_archive/.claude/rules/`, upstream `hugosantanna/clo-author@d36c408`).
`rules/workflow.md` is not restored: its loop is `skills/pipeline/SKILL.md`, its graph is the registry.
`agents/orchestrator.md` is not restored: a subagent cannot hold an approval gate, so the driver is a skill.

**Why D1 was wrong about the files.** Audit corrections C1–C2 (`docs/audits/2026-09-08_pipeline-audit-findings.md`):
`workflow.md` §3 explicitly supports the coder↔writer re-entry D1 cut it for; `lifecycle.md` is a
handoff-validation protocol, not a graph; the weight set sums to 100 once `CONDITIONAL` is honoured.
Losing `permissions.md` left `quality.md` gating submission on weights that existed nowhere.

**What would invalidate this.** A driver that can hold an approval gate inside a subagent — then
the orchestrator could return as an agent. Nothing in the harness today allows it.
```

- [ ] **Step 4: Verify the pair-table removal and commit**

```bash
cd "$W" && grep -nE '^\|\s*(explorer|strategist|theorist|coder|writer|storyteller|data-engineer|librarian)\s*\|\s*[a-z-]+-critic' rules/agents.md; echo "pair rows in agents.md: $(grep -cE '^\|\s*(explorer|strategist|theorist|coder|writer|storyteller|data-engineer|librarian)\s*\|\s*[a-z-]+-critic' rules/agents.md)"
grep -n -i 'orchestrator\|librarian\|beamer' rules/agents.md   # expect no output
git add rules/meta-governance.md rules/agents.md docs/decisions/
git commit -m "feat(rules): agents.md §1–§4 rewritten (dispatch-ownership table, registry pointer); meta-governance.md restored; D1 superseded in part"
```
Expected: `pair rows in agents.md: 0`; no orchestrator/librarian/Beamer lines.

### Task 1.7: `scripts/pipeline.py` with fixture tests (TDD)

**Files:**
- Create: `scripts/pipeline.py`, `tests/test_pipeline.py`
- Modify: `tests/run_fixture.sh` (Task 0.4's checks now become meaningful; add the red/green sequence below)

**Interfaces:**
- Produces: CLI `python3 pipeline.py [--root DIR] <cmd>`:
  - `manuscript` → prints the declared manuscript path; exit 1 if absent/ambiguous/missing file
  - `pre <agent>` / `post <agent>` → per-predicate lines `ok  <desc>` / `MISSING <desc> — run <producer>`; exit 1 on failure
  - `score [--gate commit|pr|submission]` → table + `overall=<x>`; exit 1 when gate not met
  - `state init|validate|show|record-score <component> <score> --critic X --report P [--scope S]|strike <creator>|set-blocked <text>|clear-blocked`
  - `conflicts <agent>...` → exit 1 if any two `WRITES` intersect
  - `registry check` → PASS/FAIL lines for `registry-complete`, `registry-authority`, `registry-rendered`, `weights-sum`, `registry-parse-agree`; exit 1 on any FAIL
  - `log <agent>` → appends a dispatch-log line (used by skills in standalone mode and by tests; the hook is the normal writer)
- State file v2 (`quality_reports/pipeline_state.json`):
  ```json
  {"schema_version": 2, "project": "<basename>", "manuscript": "<path>", "updated": "<iso>",
   "components": {"<component>": {"score": 0, "critic": "", "report": "", "rounds": 1, "at": "<iso>"}},
   "sections": {"<section>": {"score": 0, "critic": "writer-critic", "report": "", "at": "<iso>"}},
   "strikes": {"<creator>": 0}, "blocked_by": null, "overall": null}
  ```

- [ ] **Step 1: Failing tests**

`tests/test_pipeline.py`:
```python
import json, os, shutil, subprocess, sys, tempfile, time, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"

def run(*args, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "tests" / "fixture-project", self.t, dirs_exist_ok=True)
        (self.t / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        os.symlink(ROOT / "scripts" / "prose_number_check.py", self.t / ".claude" / "scripts" / "prose_number_check.py")
        (self.t / ".claude" / "rules").mkdir(exist_ok=True)
        os.symlink(ROOT / "rules" / "registry.yaml", self.t / ".claude" / "rules" / "registry.yaml")
    def tearDown(self): shutil.rmtree(self.t)
    def log(self, agent): self.assertEqual(run("log", agent, root=self.t)[0], 0)

class TestManuscript(FixtureCase):
    def test_declared(self):
        rc, out = run("manuscript", root=self.t); self.assertEqual(rc, 0); self.assertIn("manuscript_fixture.qmd", out)
    def test_missing_declaration(self):
        (self.t / "CLAUDE.md").write_text("# no declaration\n")
        rc, out = run("manuscript", root=self.t); self.assertEqual(rc, 1); self.assertIn("manuscript:", out)
    def test_ambiguous(self):
        (self.t / "CLAUDE.md").write_text("manuscript: a.qmd\nmanuscript: b.qmd\n")
        self.assertEqual(run("manuscript", root=self.t)[0], 1)

class TestState(FixtureCase):
    def test_init_validate_roundtrip(self):
        self.assertEqual(run("state", "init", root=self.t)[0], 0)
        self.assertEqual(run("state", "validate", root=self.t)[0], 0)
    def test_legacy_shape_rejected(self):
        run("state", "init", root=self.t)
        (self.t / "quality_reports" / "pipeline_state.json").write_text(json.dumps({"project": "x", "current_phase": "Execution", "phases": {}}))
        rc, out = run("state", "validate", root=self.t); self.assertEqual(rc, 1); self.assertIn("schema_version", out)
    def test_score_range(self):
        run("state", "init", root=self.t)
        self.assertEqual(run("state", "record-score", "code", "101", "--critic", "coder-critic", "--report", "r.md", root=self.t)[0], 1)

class TestPredicates(FixtureCase):
    def test_pre_explorer_green_no_requires(self):
        self.assertEqual(run("pre", "explorer", root=self.t)[0], 0)
    def test_pre_writer_red_then_green(self):
        run("state", "init", root=self.t)
        rc, out = run("pre", "writer", root=self.t); self.assertEqual(rc, 1); self.assertIn("code score", out)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        rc, out = run("pre", "writer", root=self.t); self.assertEqual(rc, 0, out)   # render runs here (fixture renders)
    def test_post_coder_needs_critic(self):
        run("state", "init", root=self.t)
        self.log("coder")
        rc, out = run("post", "coder", root=self.t); self.assertEqual(rc, 1); self.assertIn("critic-ran", out)
        time.sleep(0.01); self.log("coder-critic")
        rc, out = run("post", "coder", root=self.t); self.assertEqual(rc, 0, out)
    def test_post_strategist_sections(self):
        d = self.t / "quality_reports" / "strategy" / "fixture"; d.mkdir(parents=True)
        (d / "strategy_memo.md").write_text("# Memo\n## Estimand\n## Specification\n## Assumptions\n")
        rc, out = run("post", "strategist", root=self.t); self.assertEqual(rc, 1); self.assertIn("Robustness Plan", out)
    def test_fresh_stale_after_data_touch(self):
        subprocess.run(["quarto", "render", "manuscript_fixture.qmd"], cwd=self.t, capture_output=True)
        self.assertEqual(run("fresh", root=self.t)[0], 0)
        time.sleep(1.1); (self.t / "data" / "raw" / "panel.csv").touch()
        self.assertEqual(run("fresh", root=self.t)[0], 1)

class TestScore(FixtureCase):
    def test_weighted_and_renormalised(self):
        run("state", "init", root=self.t)
        for c, s in [("literature", 90), ("data", 80), ("strategy", 90), ("code", 85), ("manuscript", 88), ("referees", 85), ("replication", 100)]:
            run("state", "record-score", c, str(s), "--critic", "x", "--report", "r.md", root=self.t)
        rc, out = run("score", root=self.t); self.assertIn("overall=87.3", out)
        run("state", "record-score", "theory", "92", "--critic", "theorist-critic", "--report", "r.md", root=self.t)
        rc, out = run("score", root=self.t); self.assertIn("overall=88.08", out)
        self.assertEqual(run("score", "--gate", "submission", root=self.t)[0], 1)
    def test_conflicts(self):
        self.assertEqual(run("conflicts", "coder", "writer", root=self.t)[0], 1)
        self.assertEqual(run("conflicts", "explorer", "coder", root=self.t)[0], 0)

class TestRegistryCheck(unittest.TestCase):
    def test_runs(self):
        rc, out = run("registry", "check", root=ROOT)
        for c in ["registry-complete", "registry-authority", "registry-rendered", "weights-sum", "registry-parse-agree"]:
            self.assertIn(f"[{c}]", out)

if __name__ == "__main__": unittest.main()
```

- [ ] **Step 2: Run to see it fail**

```bash
cd "$W" && python3 -m unittest tests/test_pipeline.py 2>&1 | tail -3
```
Expected: every test errors with `can't open file .../scripts/pipeline.py`.

- [ ] **Step 3: Implement `scripts/pipeline.py`**

```python
#!/usr/bin/env python3
"""pipeline.py — executable lifecycle for the research pipeline (stdlib, Python 3.9).

Reads .claude/rules/registry.yaml (or rules/registry.yaml when --root is the research-claude
checkout), the project's CLAUDE.md `manuscript:` declaration, quality_reports/pipeline_state.json
and quality_reports/agent_dispatch.jsonl. See rules/lifecycle.md for the contract.
"""
from __future__ import annotations
import argparse, datetime as dt, fnmatch, glob, json, os, re, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_lib as rl

STATE_REL = Path("quality_reports") / "pipeline_state.json"
LOG_REL = Path("quality_reports") / "agent_dispatch.jsonl"
GATES = {"commit": (80, None), "pr": (90, None), "submission": (95, 80)}

def now() -> str: return dt.datetime.now().isoformat(timespec="seconds")

# ── registry & manuscript ───────────────────────────────────────────────────
def find_registry(root: Path) -> Path:
    for c in (root / ".claude" / "rules" / "registry.yaml", root / "rules" / "registry.yaml"):
        if c.exists(): return c
    sys.exit("pipeline.py: no registry.yaml under .claude/rules/ or rules/")

def load_reg(root: Path) -> Dict[str, Any]:
    p = find_registry(root); return rl.load_yaml_subset(p.read_text())

def declared_manuscript(root: Path) -> Path:
    claude = root / "CLAUDE.md"
    if not claude.exists(): sys.exit("pipeline.py: CLAUDE.md not found — declare `manuscript: <file>.qmd` in it (D-8)")
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", claude.read_text(), re.M)
    if len(hits) != 1:
        sys.exit(f"pipeline.py: CLAUDE.md must declare exactly one `manuscript: <file>.qmd` line (found {len(hits)})")
    m = root / hits[0]
    if not m.exists(): sys.exit(f"pipeline.py: declared manuscript {hits[0]} does not exist")
    return m

def rendered_output(ms: Path) -> Optional[Path]:
    cands = [ms.with_suffix(".pdf"), ms.with_suffix(".docx"), ms.with_suffix(".html")]
    ex = [c for c in cands if c.exists()]
    return max(ex, key=lambda p: p.stat().st_mtime) if ex else None

# ── state ───────────────────────────────────────────────────────────────────
def state_path(root: Path) -> Path: return root / STATE_REL

def empty_state(root: Path, ms: Path) -> Dict[str, Any]:
    return {"schema_version": 2, "project": root.name, "manuscript": str(ms.relative_to(root)), "updated": now(),
            "components": {}, "sections": {}, "strikes": {}, "blocked_by": None, "overall": None}

def load_state(root: Path) -> Dict[str, Any]:
    p = state_path(root)
    if not p.exists(): sys.exit("pipeline.py: no pipeline_state.json — run `pipeline.py state init`")
    return json.loads(p.read_text())

def save_state(root: Path, st: Dict[str, Any]) -> None:
    st["updated"] = now(); state_path(root).parent.mkdir(parents=True, exist_ok=True)
    state_path(root).write_text(json.dumps(st, indent=2) + "\n")

def validate_state(st: Dict[str, Any], reg: Dict[str, Any]) -> List[str]:
    p: List[str] = []
    if st.get("schema_version") != 2: p.append("schema_version must be 2 (legacy clo-author shape is not accepted)")
    for k, t in [("project", str), ("manuscript", str), ("updated", str), ("components", dict), ("sections", dict), ("strikes", dict)]:
        if not isinstance(st.get(k), t): p.append(f"{k} must be {t.__name__}")
    comps = set(reg["components"])
    for c, e in (st.get("components") or {}).items():
        if c not in comps: p.append(f"components.{c}: not a registry component")
        if not isinstance(e, dict) or not isinstance(e.get("score"), (int, float)) or not 0 <= e["score"] <= 100:
            p.append(f"components.{c}: score must be a number in 0..100")
        for k in ("critic", "report", "at"):
            if not isinstance((e or {}).get(k), str): p.append(f"components.{c}: {k} must be a string")
    for a in (st.get("strikes") or {}):
        if a not in reg["agents"]: p.append(f"strikes.{a}: not a registry agent")
    return p

# ── score ───────────────────────────────────────────────────────────────────
def compute_overall(st, reg) -> Tuple[Optional[float], Dict[str, float]]:
    w = rl.component_weights(reg); scored = {c: e["score"] for c, e in st.get("components", {}).items()}
    used = {c: w[c] for c in scored if c in w}
    if not used: return None, {}
    tot = sum(used.values()); return round(sum(scored[c] * used[c] for c in used) / tot, 2), used

# ── dispatch log ────────────────────────────────────────────────────────────
def read_log(root: Path) -> List[Dict[str, Any]]:
    p = root / LOG_REL
    if not p.exists(): return []
    out = []
    for ln in p.read_text().splitlines():
        try: out.append(json.loads(ln))
        except json.JSONDecodeError: continue
    return out

def append_log(root: Path, agent: str, source: str = "pipeline.py") -> None:
    p = root / LOG_REL; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f: f.write(json.dumps({"at": now(), "agent": agent, "source": source}) + "\n")

def last_completion(log, agent) -> Optional[str]:
    ats = [e["at"] for e in log if e.get("agent") == agent]
    return max(ats) if ats else None

# ── predicates ──────────────────────────────────────────────────────────────
class Ctx:
    def __init__(self, root: Path, reg, agent: Optional[str]):
        self.root, self.reg, self.agent = root, reg, agent
        self._ms: Optional[Path] = None
    @property
    def ms(self) -> Path:
        if self._ms is None: self._ms = declared_manuscript(self.root)
        return self._ms

def chunk_labels(ms: Path) -> List[str]:
    return re.findall(r"^#\|\s*label:\s*([A-Za-z0-9_-]+)", ms.read_text(), re.M)

def headings(path: Path) -> List[str]:
    return [h.strip() for h in re.findall(r"^#{1,6}\s+(.+?)\s*(?:\{[^}]*\})?\s*$", path.read_text(), re.M)]

def is_fresh(root: Path, ms: Path) -> Tuple[bool, str]:
    out = rendered_output(ms)
    if not out: return False, "no rendered output"
    newest = ms.stat().st_mtime
    for f in (root / "data" / "raw").rglob("*"):
        if f.is_file(): newest = max(newest, f.stat().st_mtime)
    return (out.stat().st_mtime >= newest), f"{out.name} vs newest input"

def do_render(root: Path, target: Path) -> Tuple[bool, str]:
    p = subprocess.run(["quarto", "render", str(target.relative_to(root))], cwd=root, capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or p.stdout).strip().splitlines()[-1:] and (p.stderr or p.stdout).strip().splitlines()[-1] or ""

def evaluate(pred: Dict[str, Any], ctx: Ctx, post: bool = False) -> Tuple[bool, str]:
    t = pred["type"]; root = ctx.root
    if t == "path":
        n = len(glob.glob(str(root / pred["glob"]), recursive=True)); need = int(pred.get("min", 1))
        return n >= need, f"path {pred['glob']} ({n} found, need {need})"
    if t == "section":
        files = [ctx.ms] if pred["file"] == "manuscript" else [Path(p) for p in glob.glob(str(root / pred["file"]))]
        ok = any(pred["heading"] in headings(f) for f in files if f.exists())
        return ok, f"heading '{pred['heading']}' in {pred['file']}"
    if t == "score":
        st = json.loads(state_path(root).read_text()) if state_path(root).exists() else {"components": {}}
        if pred["component"] == "overall":
            ov, _ = compute_overall(st, ctx.reg); val = ov
        else:
            val = st.get("components", {}).get(pred["component"], {}).get("score")
        ok = val is not None and val >= float(pred["min"])
        return ok, f"{pred['component']} score ≥ {pred['min']} (have {val})"
    if t == "fresh":
        ok, why = is_fresh(root, ctx.ms); return ok, f"fresh: {why}"
    if t == "render":
        targets = [ctx.ms] if not pred.get("file") else [Path(p) for p in glob.glob(str(root / pred["file"]))]
        if not targets: return False, f"render: nothing matches {pred.get('file')}"
        for tg in targets:
            if tg == ctx.ms and is_fresh(root, ctx.ms)[0]: continue          # render only when stale
            ok, why = do_render(root, tg)
            if not ok: return False, f"render {tg.name} failed: {why}"
        return True, "render exit 0"
    if t == "critic-ran":
        crit = rl.critic_of(ctx.reg, ctx.agent or "")
        if not crit: return True, "no critic declared"
        log = read_log(root); a, c = last_completion(log, ctx.agent), last_completion(log, crit)
        ok = a is not None and c is not None and c > a
        return ok, f"critic-ran: {crit} after {ctx.agent} (creator {a}, critic {c})"
    if t == "prose-check":
        script = root / ".claude" / "scripts" / "prose_number_check.py"
        if not script.exists(): return False, "prose-check: .claude/scripts/prose_number_check.py not linked"
        p = subprocess.run([sys.executable, str(script), str(ctx.ms.relative_to(root))], cwd=root, capture_output=True, text=True)
        return p.returncode == 0, "prose_number_check.py exit " + str(p.returncode)
    if t == "chunk":
        n = sum(1 for l in chunk_labels(ctx.ms) if fnmatch.fnmatch(l, pred["label_glob"]))
        return n >= int(pred["min"]), f"chunks {pred['label_glob']} ({n} found, need {pred['min']})"
    if t == "any_of":
        results = [evaluate(q, ctx, post) for q in pred["of"]]
        return any(r[0] for r in results), "any of: " + " | ".join(r[1] for r in results)
    return False, f"unknown predicate {t}"

def run_preds(kind: str, agent: str, root: Path, reg) -> int:
    if agent not in reg["agents"]: sys.exit(f"pipeline.py: {agent!r} is not in the registry")
    e = reg["agents"][agent]; ctx = Ctx(root, reg, agent)
    preds = list(e["requires"] if kind == "pre" else e["produces"])
    if kind == "post" and rl.critic_of(reg, agent) and not any(p["type"] == "critic-ran" for p in preds):
        preds.append({"type": "critic-ran"})
    rc = 0
    for p in preds:
        ok, desc = evaluate(p, ctx, post=(kind == "post"))
        hint = f" — run `{p['producer']}`" if (not ok and p.get("producer")) else ""
        print(("ok      " if ok else "MISSING ") + desc + hint)
        rc |= 0 if ok else 1
    print(f"{kind} {agent}: " + ("PASS" if rc == 0 else "FAIL"))
    return rc

# ── registry check (check_fork criteria) ────────────────────────────────────
AUTH_PAIR = re.compile(r"^\|\s*(lit-position|explorer|strategist|theorist|coder|data-engineer|writer|storyteller)\s*\|\s*[a-z-]+-critic\s*\|", re.M)
AUTH_ARROW = re.compile(r"\b(lit-position|explorer|strategist|theorist|coder|data-engineer|writer|storyteller)\s*(→|->|↔)\s*[a-z-]+-critic\b")
AUTH_WEIGHT = re.compile(r"(QUALITY_WEIGHT|\bweight)\s*[:=|]\s*\d|\b\d+(\.\d+)?%\s*(of\s+)?(weight|\((literature|data|strategy|theory|code|manuscript|replication))", re.I)
AUTH_ALLOW = {"rules/registry.yaml", "rules/permissions.md", "rules/quality.md"}

def registry_check(root: Path) -> int:
    rc = 0; reg = rl.load_registry(root)
    probs = rl.validate_registry(reg)
    roster = {p.stem for p in (root / "agents").glob("*.md")}
    for a, e in reg["agents"].items():
        if e.get("kind") == "agent" and a not in roster: probs.append(f"{a}: declared but agents/{a}.md missing")
    for a in roster:
        if a not in reg["agents"]: probs.append(f"agents/{a}.md exists but is not declared")
    print("PASS [registry-complete]" if not probs else "FAIL [registry-complete]"); [print(f"    {p}") for p in probs]; rc |= bool(probs)
    hits = []
    for d in ["agents", "skills", "rules", "references", "hooks", "templates", "seeds"]:
        for f in sorted((root / d).rglob("*.md")) if (root / d).is_dir() else []:
            rel = str(f.relative_to(root))
            if rel in AUTH_ALLOW: continue
            for i, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if "residue:historical" in ln: continue
                if AUTH_PAIR.search(ln) or AUTH_ARROW.search(ln) or AUTH_WEIGHT.search(ln):
                    hits.append(f"{rel}:{i}: {ln.strip()[:100]}")
    print("PASS [registry-authority]" if not hits else "FAIL [registry-authority]"); [print(f"    {h}") for h in hits]; rc |= bool(hits)
    p = subprocess.run([sys.executable, str(root / "scripts" / "render_registry.py"), "--root", str(root), "--check"], capture_output=True, text=True)
    print(p.stdout.strip()); rc |= p.returncode != 0
    wp = rl.weights_report(reg, (root / "rules" / "quality.md").read_text() if (root / "rules" / "quality.md").exists() else "")
    print("PASS [weights-sum]" if not wp else "FAIL [weights-sum]"); [print(f"    {w}") for w in wp]; rc |= bool(wp)
    pa = rl.parse_agree(root); print(f"{pa} [registry-parse-agree]" + (" (PyYAML not importable)" if pa == "SKIP" else "")); rc |= pa == "FAIL"
    return int(rc)

# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manuscript"); sub.add_parser("fresh")
    for k in ("pre", "post"): sub.add_parser(k).add_argument("agent")
    sc = sub.add_parser("score"); sc.add_argument("--gate", choices=sorted(GATES))
    st = sub.add_parser("state"); st.add_argument("op", choices=["init", "validate", "show", "record-score", "strike", "set-blocked", "clear-blocked"])
    st.add_argument("args", nargs="*"); st.add_argument("--critic"); st.add_argument("--report"); st.add_argument("--scope")
    sub.add_parser("conflicts").add_argument("agents", nargs="+")
    sub.add_parser("registry").add_argument("op", choices=["check"])
    lg = sub.add_parser("log"); lg.add_argument("agent"); lg.add_argument("--source", default="skill")
    a = ap.parse_args(); root = Path(a.root).resolve()
    if a.cmd == "registry": return registry_check(root)
    reg = load_reg(root)
    if a.cmd == "manuscript": print(declared_manuscript(root).relative_to(root)); return 0
    if a.cmd == "fresh":
        ok, why = is_fresh(root, declared_manuscript(root)); print(("fresh: " if ok else "STALE: ") + why); return 0 if ok else 1
    if a.cmd in ("pre", "post"): return run_preds(a.cmd, a.agent, root, reg)
    if a.cmd == "log": append_log(root, a.agent, a.source); return 0
    if a.cmd == "conflicts":
        ws = {}
        for ag in a.agents:
            if ag not in reg["agents"]: sys.exit(f"unknown agent {ag}")
            ws[ag] = set(reg["agents"][ag]["writes"])
        clashes = [(x, y, ws[x] & ws[y]) for i, x in enumerate(a.agents) for y in a.agents[i + 1:] if ws[x] & ws[y]]
        for x, y, s in clashes: print(f"CONFLICT {x} ∩ {y}: {sorted(s)}")
        print("conflicts: " + ("none" if not clashes else f"{len(clashes)}")); return 1 if clashes else 0
    if a.cmd == "score":
        stt = load_state(root); ov, used = compute_overall(stt, reg)
        for c, w in used.items(): print(f"{c:12s} {stt['components'][c]['score']:6.1f}  weight {w:5.1f}")
        print(f"overall={ov if ov is not None else 'n/a'}")
        if a.gate:
            need, per = GATES[a.gate]; ok = ov is not None and ov >= need and (per is None or all(e["score"] >= per for e in stt["components"].values()))
            print(f"gate {a.gate}: " + ("PASS" if ok else "FAIL")); return 0 if ok else 1
        return 0
    if a.cmd == "state":
        if a.op == "init":
            ms = declared_manuscript(root)
            if state_path(root).exists(): print("pipeline_state.json already exists — left untouched"); return 0
            save_state(root, empty_state(root, ms)); print(f"wrote {STATE_REL}"); return 0
        stt = load_state(root)
        if a.op == "validate":
            probs = validate_state(stt, reg); [print(f"    {p}") for p in probs]
            print("state: " + ("valid" if not probs else "INVALID")); return 1 if probs else 0
        if a.op == "show": print(json.dumps(stt, indent=2)); return 0
        if a.op == "record-score":
            if len(a.args) != 2 or not a.critic or not a.report: sys.exit("usage: state record-score <component> <score> --critic X --report P [--scope section:NAME]")
            comp, score = a.args[0], float(a.args[1])
            if comp not in reg["components"] or not 0 <= score <= 100: print("record-score: bad component or score"); return 1
            entry = {"score": score, "critic": a.critic, "report": a.report, "at": now()}
            if a.scope and a.scope.startswith("section:"):
                stt["sections"][a.scope.split(":", 1)[1]] = entry
            else:
                entry["rounds"] = stt["components"].get(comp, {}).get("rounds", 0) + 1; stt["components"][comp] = entry
            stt["overall"], _ = compute_overall(stt, reg); save_state(root, stt); print(f"recorded {comp}={score}"); return 0
        if a.op == "strike":
            cr = a.args[0]; n = stt["strikes"].get(cr, 0) + 1; stt["strikes"][cr] = n; save_state(root, stt)
            lim = int(reg["limits"]["rounds_per_pair"])
            print(f"{cr}: strike {n} of {lim}" + (f" — ESCALATE to {reg['agents'][cr]['escalation_target']}" if n >= lim else "")); return 0
        if a.op == "set-blocked": stt["blocked_by"] = " ".join(a.args); save_state(root, stt); return 0
        if a.op == "clear-blocked": stt["blocked_by"] = None; save_state(root, stt); return 0
    return 2

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests until green; run with both interpreters**

```bash
cd "$W" && python3 -m unittest tests/test_pipeline.py 2>&1 | tail -4
/usr/bin/python3 -m unittest tests/test_pipeline.py 2>&1 | tail -2
```
Expected: all pass under both (the fresh test renders the fixture, ~20 s). `TestRegistryCheck.test_runs` passes because it only asserts the five criterion labels print; the criteria themselves are still red at this point — confirm with `python3 scripts/pipeline.py --root . registry check`: `registry-complete` FAIL (lit-critic.md missing until Task 4.3), `registry-authority` FAIL (pairs stated across the tree; the hit list is Stage 3b/4's worklist — save it to `docs/audits/2026-09-08_stage0-red.md` under `## registry-authority (Stage 1)`), `registry-rendered` PASS, `weights-sum` PASS, `registry-parse-agree` PASS.

- [ ] **Step 5: Update `run_fixture.sh` so `pre-writer-red` is no longer vacuous**

Replace the single `expect_fail pre-writer-red` line with the red→green sequence:
```bash
expect_fail pre-writer-red   python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
run         record-code      python3 "$RC/scripts/pipeline.py" --root "$T" state record-score code 85 --critic coder-critic --report quality_reports/reviews/coder-critic_fixture.md
run         pre-writer-green python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
run         log-coder        python3 "$RC/scripts/pipeline.py" --root "$T" log coder
expect_fail post-coder-red   python3 "$RC/scripts/pipeline.py" --root "$T" post coder
run         log-coder-critic bash -c "sleep 1; python3 '$RC/scripts/pipeline.py' --root '$T' log coder-critic"
run         post-coder-green python3 "$RC/scripts/pipeline.py" --root "$T" post coder
expect_fail conflicts-red    python3 "$RC/scripts/pipeline.py" --root "$T" conflicts coder writer
run         score            python3 "$RC/scripts/pipeline.py" --root "$T" score
```
Run `tests/run_fixture.sh`; expected: every line above PASS; `registry-check` still FAIL (lit-critic file); `link` PASS. Read the whole output.

- [ ] **Step 6: Commit**

```bash
cd "$W" && git add scripts/pipeline.py tests/test_pipeline.py tests/run_fixture.sh docs/audits/2026-09-08_stage0-red.md
git commit -m "feat(pipeline): pipeline.py — manuscript, pre/post predicates, state v2, score, conflicts, registry check; fixture tests red then green"
```

### Task 1.8: `rules/logging.md` Pipeline State section, `rules/revision.md` actors

**Files:**
- Modify: `rules/logging.md` (lines 46–87), `rules/revision.md` (lines 9–12, 28, 40)

- [ ] **Step 1: Replace `## Pipeline State` through end of file in `rules/logging.md`**

```markdown
## Pipeline State

`quality_reports/pipeline_state.json` is the machine-readable record of scores and progress.
Schema: `.claude/templates/pipeline-state.json` (v2). Written only by
`python3 .claude/scripts/pipeline.py state ...`; read by `pipeline.py score`, `/pipeline`,
`/checkpoint` (staleness sweep) and `.claude/hooks/post-compact-restore.py`. **Committed** — it is
replication provenance. The research journal entry is derived from it, never the reverse.

## Dispatch Log

`quality_reports/agent_dispatch.jsonl` — one JSON line per subagent completion, written by
`.claude/hooks/dispatch-log.py` (SubagentStop) or by `pipeline.py log <agent>` from a standalone
skill. `pipeline.py post` reads it to prove the critic ran. **Gitignored** — session mechanics.

## Learning Loop

Owned by `.claude/rules/meta-governance.md`: `/pipeline` surfaces suggested learnings from the
state file and dispatch log; the user approves; `/promote` lands them.
```
(The `## 4. Project Dashboard` section is deleted — D-18.)

- [ ] **Step 2: `rules/revision.md`** — in the table replace `| **MINOR** | Typos, formatting | Writer |` with `| **MINOR** | Typos, formatting | Writer → writer-critic |`; line 28 `Revised paper → writer-critic → Orchestrator re-checks` → `Revised paper → writer-critic → pipeline.py post writer`; line 40 `The Orchestrator tracks which comments are resolved and which are pending` → `` `/revise` tracks which comments are resolved in `quality_reports/referee_response_tracker.md` ``. Add FATAL row from `/revise` Step 2 so rule and skill agree: `| **FATAL** | Invalidates a headline claim if correct | Stop; escalate to User before any drafting |`.

- [ ] **Step 3: Verify and commit**

```bash
cd "$W" && grep -n -i 'orchestrator\|dashboard\|traces/' rules/logging.md rules/revision.md   # expect no output
git add rules/logging.md rules/revision.md && git commit -m "fix(rules): logging.md pipeline-state and dispatch-log sections for the real files; revision.md actors reassigned"
```

### Task 1.9: Stage 1 sign-off

- [ ] `python3 -m unittest discover -s tests -p 'test_*.py'` → all pass except the two red-by-design (`test_roster_matches_agents_dir` until Task 4.3). Record.
- [ ] `./scripts/check_fork.sh | grep -E '^(PASS|FAIL) \[(registry|weights|d1-restored)'` → `registry-rendered`, `weights-sum`, `registry-parse-agree` PASS; `registry-complete`, `registry-authority` FAIL (expected until Stage 4 / 3b); `d1-restored` PASS for `registry.yaml`, `permissions.md`, `lifecycle.md`, `meta-governance.md`, `pipeline.py`, `registry_lib.py`, `run_fixture.sh`; FAIL for the rest.
- [ ] `python3 scripts/audit_graph.py . /tmp/g1.json | head -3` → dangling count unchanged or lower (new rules add no dangling refs). Commit nothing new; note the counts in the next commit message.

---

## Stage 1b — Manuscript declaration (D-8)

### Task 1b.1: `manuscript-declared` in `check_install.sh`; `quarto-empirical.md` documents the declaration; POGM4 declares

**Files:**
- Modify: `scripts/check_install.sh` (append a check 7), `rules/quarto-empirical.md` (lines 9–12 block), `~/Research/POGM4/CLAUDE.md`

- [ ] **Step 1: `check_install.sh` check 7 (before the `bootstrap` line)**

```bash
  # ── 7. Manuscript declared (D-8) ──────────────────────────────────────────
  # Every predicate, hook and skill resolves the manuscript through CLAUDE.md.
  local decl; decl="$(grep -cE '^manuscript:\s*\S+\.qmd\s*$' "$P/CLAUDE.md" 2>/dev/null || echo 0)"
  if [[ "$decl" -eq 1 ]]; then
    local mf; mf="$(sed -nE 's/^manuscript:\s*(\S+\.qmd)\s*$/\1/p' "$P/CLAUDE.md")"
    [[ -f "$P/$mf" ]] && ok manuscript-declared "$mf" || bad manuscript-declared "CLAUDE.md declares $mf but it does not exist"
  elif [[ "$decl" -eq 0 ]]; then
    if [[ -n "$(find "$P" -maxdepth 2 -name '*.qmd' -not -path '*/talks/*' -not -path '*/explorations/*' -print -quit)" ]]; then
      bad manuscript-declared "no 'manuscript: <file>.qmd' line in CLAUDE.md"
    else warn manuscript-declared "no manuscript yet — /pipeline refuses until one is declared"; fi
  else bad manuscript-declared "CLAUDE.md declares $decl manuscripts; exactly one is required"; fi
```

- [ ] **Step 2: Red across the fleet, then green on POGM4**

```bash
"$W/scripts/check_install.sh" --all | grep -E '\[manuscript-declared\]'
```
Expected: FAIL for POGM4, zoning2026, affordable_housing_2026, ESG, NAR_settlement; WARN for BRI. Then edit `~/Research/POGM4/CLAUDE.md`: insert the line `manuscript: manuscript_quarto_word.qmd` as its own paragraph directly after the `**Pipeline:**` line (line 6). Re-run for POGM4 → PASS. Commit in POGM4: `git -C ~/Research/POGM4 commit -am "chore: declare manuscript for the research-claude pipeline (D-8)"`. The other four are declared in Stage 8 (their residue must be migrated first).

- [ ] **Step 3: `rules/quarto-empirical.md`** — replace the blockquote at lines 9–12 with:

```markdown
> **File name and declaration.** A new project is scaffolded with `manuscript_<project>.qmd`
> (`<project>` = the directory basename). Whatever the file is called, the project's `CLAUDE.md`
> declares it on a line of its own: `manuscript: manuscript_<project>.qmd`. Every predicate in
> `.claude/scripts/pipeline.py`, every hook and every skill resolves "the manuscript" through
> that line, and `check_install.sh` fails when it is absent or names more than one file. Examples
> below write `manuscript_<project>.qmd` and mean the declared manuscript.
```
Also fix line 12's dangling sentence ("See\nThis file is the canonical statement") — it is replaced by the block above.

- [ ] **Step 4: Commit**

```bash
cd "$W" && git add scripts/check_install.sh rules/quarto-empirical.md && git commit -m "feat(check_install): manuscript-declared (D-8); quarto-empirical.md documents the declaration"
```

---

## Stage 2 — Missing and mis-homed files: `templates/` vs `seeds/`, installer, install gate, embed test, canary

**Exit criteria:** `seeds/` holds every copied-once file; `templates/` holds only files agents read by a `.claude/templates/` path; `apply.sh` links `templates/` and the `scripts/SHIPPED` set; the gitignore seed and all six repos ignore `.claude/{templates,scripts}/*`; `check_install.sh` has `scripts-linked`, `templates-linked`, `gitignore-covers`, `state-valid`; `docs/audits/2026-09-08_embed-test.md` records R-5; POGM4 is linked to `$W`.

### Task 2.1: Split `templates/` into `templates/` and `seeds/`

**Files:**
- Move (`git mv`): `templates/gitignore → seeds/gitignore`, `templates/settings.json → seeds/settings.json`, `templates/bootstrap-pipeline.sh → seeds/bootstrap-pipeline.sh`, `templates/ai-use-log.md → seeds/ai-use-log.md`, `templates/data_manifest.md → seeds/data_manifest.md`
- Keep: `templates/handoff.md`
- Create: `seeds/quarto-preamble.tex` (copy of `tests/fixture-project/templates/quarto-preamble.tex`), `templates/pipeline-state.json`, `templates/journal-profile-template.md`, `scripts/SHIPPED`

- [ ] **Step 1: Move and create**

```bash
cd "$W" && mkdir -p seeds && for f in gitignore settings.json bootstrap-pipeline.sh ai-use-log.md data_manifest.md; do git mv "templates/$f" "seeds/$f"; done
cp tests/fixture-project/templates/quarto-preamble.tex seeds/quarto-preamble.tex
printf 'prose_number_check.py\npipeline.py\nregistry_lib.py\nqmd_chunks.py\n' > scripts/SHIPPED
python3 - <<'PY'
import json, pathlib
pathlib.Path("templates/pipeline-state.json").write_text(json.dumps({
  "schema_version": 2, "project": "", "manuscript": "", "updated": "",
  "components": {}, "sections": {}, "strikes": {}, "blocked_by": None, "overall": None}, indent=2) + "\n")
PY
```
(`qmd_chunks.py` is created in Task 7.3; `scripts-manifest` stays red until then — intended.)

- [ ] **Step 2: `templates/journal-profile-template.md`** — copy `~/Research/POGM4/templates/journal-profile-template.md` (read it in full; it is the clo-author template) and make exactly these edits: line 3 `.claude/references/journal-profiles.md` (already prefixed — keep); line 67 `.claude/agents/methods-referee.md` (keep); line 77 `.claude/skills/review-paper/SKILL.md` → `` `.claude/skills/review/SKILL.md` — entry point for `--peer [SHORT]` ``. Add after the template block: "**Short-name uniqueness.** A short name is used as the `--peer` argument and must be unique across the file; `JHE` is Journal of Health Economics, the housing journal is `JHousE`."

- [ ] **Step 3: Gitignore seed** — in `seeds/gitignore`: delete the `data/cleaned/` line and its comment (P-15); after `.claude/scripts/prose_number_check.py` replace that line with:
```
.claude/scripts/*
.claude/templates/*
# Session mechanics, never provenance
quality_reports/agent_dispatch.jsonl
```
and add under the "Project overrides" comment: `# !.claude/templates/my-project-template.md`.

- [ ] **Step 4: Commit**

```bash
cd "$W" && git add -A templates seeds scripts/SHIPPED && git commit -m "refactor(templates): split templates/ (linked) from seeds/ (copied once); preamble seed; state schema; journal-profile template; scripts/SHIPPED"
```

### Task 2.2: `apply.sh` links `templates/` and shipped scripts, seeds from `seeds/`

**Files:**
- Modify: `apply.sh` (lines 55–90 `--list` text; 104 mkdir; 150–185 link block; 187–218 seeds block)

- [ ] **Step 1: Edits**

In `--list`: add rows `.claude/templates/  -> $SCRIPT_DIR/templates/` and `.claude/scripts/    -> scripts listed in scripts/SHIPPED`; change the seeds list to read from `seeds/` and add `templates/quarto-preamble.tex   PDF preamble the manuscript YAML requires`. Line 104: `mkdir -p "$PROJECT_DIR/.claude"/{agents,skills,rules,hooks,templates,scripts} "$PROJECT_DIR/explorations" "$PROJECT_DIR/templates"`. Replace lines 171–184 (the prose_number_check block) with:

```bash
  # templates/: files agents read by a .claude/templates/ path. Linked like the rest.
  echo "  templates/"
  prune_dead_links "$PROJECT_DIR/.claude/templates"
  link_items "$SCRIPT_DIR/templates" "$PROJECT_DIR/.claude/templates"

  # scripts/: only the shipped set (scripts/SHIPPED), one link each. Repo-maintenance
  # scripts (check_fork.sh, check_install.sh, audit_graph.py, ...) stay here.
  echo "  scripts/"
  prune_dead_links "$PROJECT_DIR/.claude/scripts"
  while IFS= read -r s; do
    [[ -z "$s" || ! -f "$SCRIPT_DIR/scripts/$s" ]] && continue
    t="$PROJECT_DIR/.claude/scripts/$s"
    if [[ -e "$t" && ! -L "$t" ]]; then echo "    ⤷ $s is a real file here — project override, left alone"; continue; fi
    ln -sfn "$(relpath "$SCRIPT_DIR/scripts/$s" "$PROJECT_DIR/.claude/scripts")" "$t"
  done < "$SCRIPT_DIR/scripts/SHIPPED"
```
Replace every `$SCRIPT_DIR/templates/<seed>` in the seeds block with `$SCRIPT_DIR/seeds/<seed>` and add:
```bash
[[ -f "$SCRIPT_DIR/seeds/quarto-preamble.tex" ]] && \
  copy_seed "$SCRIPT_DIR/seeds/quarto-preamble.tex" "$PROJECT_DIR/templates/quarto-preamble.tex"
```
Update the header comment (lines 10–24) to name `templates/` and `scripts/SHIPPED` as linked and `seeds/` as copied.

- [ ] **Step 2: Test on a fixture copy**

```bash
S="$(mktemp -d)"; cp -R "$FX/." "$S/"; rm -rf "$S/.claude" "$S/templates"; "$W/apply.sh" --project-dir "$S" --link | tail -12
ls -la "$S/.claude/templates" "$S/.claude/scripts"; ls "$S/templates"; rm -rf "$S"
```
Expected: `.claude/templates/{handoff.md,pipeline-state.json,journal-profile-template.md}` as links; `.claude/scripts/{prose_number_check.py,pipeline.py,registry_lib.py}` as links (no `qmd_chunks.py` yet); `templates/quarto-preamble.tex` a real copied file; `.gitignore` copied from `seeds/`.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add apply.sh && git commit -m "feat(apply): link templates/ and scripts/SHIPPED into .claude/; seeds from seeds/; preamble seeded to templates/"
```

### Task 2.3: `check_install.sh` — `LINKED`/`want` extended, `templates-linked`, `scripts-linked`, `gitignore-covers`, `state-valid`

**Files:**
- Modify: `scripts/check_install.sh` (line 36 `LINKED`; lines 121–127 `want`; append checks 8–10)

- [ ] **Step 1: Edits**

Line 36: `LINKED=(skills agents rules hooks scripts templates)`. Replace lines 121–127 with:
```bash
  local d; for d in skills agents rules hooks templates; do want "$RC/$d" "$d"; done
  want "$RC/submodules/ai-audit/skills" skills
  want "$RC/submodules/ai-audit/agents" agents
  want "$RC/submodules/ai-audit/rules"  rules
  want "$RC/zotpilot-skills" skills true
  if [[ -f "$RC/scripts/SHIPPED" ]]; then
    while IFS= read -r s; do [[ -z "$s" || ! -f "$RC/scripts/$s" ]] && continue
      [[ -e "$P/.claude/scripts/$s" || -L "$P/.claude/scripts/$s" ]] || missing+=("scripts/$s"); done < "$RC/scripts/SHIPPED"
  fi
```
Append before `bootstrap`:
```bash
  # ── 8. gitignore covers the linked dirs ───────────────────────────────────
  local gi_missing=() pat
  for pat in '.claude/skills/*' '.claude/agents/*' '.claude/rules/*' '.claude/hooks/*' '.claude/scripts/*' '.claude/templates/*' 'quality_reports/agent_dispatch.jsonl'; do
    grep -qxF "$pat" "$P/.gitignore" 2>/dev/null || gi_missing+=("$pat")
  done
  [[ ${#gi_missing[@]} -eq 0 ]] && ok gitignore-covers || bad gitignore-covers "missing lines: ${gi_missing[*]}"

  # ── 9. State file is schema-valid when present ────────────────────────────
  if [[ -f "$P/quality_reports/pipeline_state.json" ]]; then
    if python3 "$RC/scripts/pipeline.py" --root "$P" state validate >/dev/null 2>&1; then ok state-valid
    else bad state-valid "quality_reports/pipeline_state.json fails pipeline.py state validate"; fi
  else warn state-valid "no pipeline_state.json yet"; fi
```
(`templates-linked` and `scripts-linked` are the membership check over the two new dirs; name them in the `membership` output by prefixing the missing items, which `want` already does.)

- [ ] **Step 2: Red across the fleet**

```bash
"$W/scripts/check_install.sh" --all | grep -E '\[(membership|gitignore-covers|state-valid)\]'
```
Expected: `membership` FAIL ×6 (templates/* and scripts/pipeline.py never linked); `gitignore-covers` FAIL ×6; `state-valid` FAIL for affordable_housing_2026 (legacy shape), WARN ×5. Save the output into `docs/audits/2026-09-08_stage0-red.md` under `## check_install (Stage 2)`.

- [ ] **Step 3: Edit the six repos' `.gitignore` by hand** (seeds never overwrite): in each, replace the `.claude/scripts/prose_number_check.py` line with the three lines from Task 2.1 Step 3 plus the `agent_dispatch.jsonl` line; commit in each repo: `chore: gitignore linked .claude/{scripts,templates} and the dispatch log`. Re-run → `gitignore-covers` PASS ×6.

- [ ] **Step 4: Commit**

```bash
cd "$W" && git add scripts/check_install.sh docs/audits/2026-09-08_stage0-red.md && git commit -m "feat(check_install): templates/scripts membership, gitignore-covers, state-valid — red across six repos, gitignores fixed"
```

### Task 2.4: R-5 — test Quarto `embed` from a `.qmd` source on the fixture

**Files:**
- Create: `docs/audits/2026-09-08_embed-test.md`, `tests/fixture-project/talks/seminar_talk.qmd` (the test artefact, kept as the fixture talk)

- [ ] **Step 1: Write the talk with an embed of the manuscript's figure chunk**

```markdown
---
title: "Fixture talk"
format:
  revealjs:
    slide-number: true
bibliography: ../references.bib
---

## Trends

{{< embed ../manuscript_fixture.qmd#fig-trends >}}

## Estimate

{{< embed ../manuscript_fixture.qmd#tbl-main >}}
```

- [ ] **Step 2: Render and record**

```bash
cd "$FX" && quarto render manuscript_fixture.qmd >/dev/null 2>&1; quarto render talks/seminar_talk.qmd 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"; ls talks/*.html 2>/dev/null
```
Read the whole output. Write `docs/audits/2026-09-08_embed-test.md` with: Quarto version (`1.9.37`), the exact command, exit code, whether the figure and table appear in the HTML (`grep -c 'fig-trends\|tbl-main' talks/seminar_talk.html`), and the ruling: **if exit 0 and both present → D-20 preferred path (embed) is confirmed; the storyteller rewrite (Task 3b.4) uses `{{< embed <manuscript>#<label> >}}`.** If not → fallback: the manuscript keeps `manuscript_<project>_files/` and the talk uses `![](../manuscript_<project>_files/figure-pdf/fig-trends-1.pdf)`; record the failure text verbatim. Clean render artifacts before committing.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add docs/audits/2026-09-08_embed-test.md tests/fixture-project/talks && git commit -m "test(fixture): R-5 embed test — <result> (see docs/audits/2026-09-08_embed-test.md)"
```

### Task 2.5: Re-link the canary (POGM4) to the worktree

- [ ] **Step 1: Link from `$W` directly (not `bootstrap-pipeline.sh --tip`, which would `git checkout main` in `$RC`)**

```bash
"$W/apply.sh" --project-dir ~/Research/POGM4 --link | tail -6
readlink ~/Research/POGM4/.claude/agents/coder.md      # expect a path ending in research-claude-repair/agents/coder.md
RESEARCH_CLAUDE_ALLOW_BRANCH=1 "$W/scripts/check_install.sh" --project-dir ~/Research/POGM4
```
Expected: `WARN [branch] ... allowed`, `PASS [membership]`, `PASS [gitignore-covers]`, `PASS [manuscript-declared]`, `PASS [dangling]`. POGM4's own `templates/` already has real files (`ai-use-log.md`, `journal-profile-template.md`, …) — those are project content and untouched; the seed `quarto-preamble.tex` is copied in because POGM4 lacks it (it is Word-only; harmless).

- [ ] **Step 2: Record** in `docs/audits/2026-09-08_stage0-red.md` under `## Canary`: the readlink output and the check_install result. From here until Stage 8, every `check_install.sh --all` run sets `RESEARCH_CLAUDE_ALLOW_BRANCH=1`.

### Task 2.6: Stage 2 sign-off

- [ ] `./scripts/check_fork.sh | grep -E '\[(seeds-complete|scripts-manifest|d1-restored)\]'` → `seeds-complete` PASS; `scripts-manifest` FAIL (`qmd_chunks.py` until 7.3); `d1-restored` PASS for `templates/pipeline-state.json`, `templates/journal-profile-template.md`, `seeds/quarto-preamble.tex`, `scripts/SHIPPED`.
- [ ] `tests/run_fixture.sh` → `link` PASS with templates and scripts linked (add `run templates-linked test -L "$T/.claude/templates/pipeline-state.json"` and `run scripts-linked test -L "$T/.claude/scripts/pipeline.py"` to the harness; both PASS).
- [ ] Commit the harness change: `test(fixture): assert templates and shipped scripts are linked`.

---

## Stage 3 — Path layer: the gate, the table, the inventory

Per P-12 the rewrites themselves happen in Stage 3b, one file group at a time, paths and content together. Stage 3 delivers the inventory the groups work from.

### Task 3.1: Path inventory

- [ ] **Step 1: Produce the worklist**

```bash
cd "$W" && python3 scripts/check_paths.py --root . --list > docs/audits/2026-09-08_path-inventory.txt; tail -1 docs/audits/2026-09-08_path-inventory.txt
```
Expected: `total≈150 unresolved≈66 unprefixed≈44` (±10). Read the whole file. Classify every non-`ok` row into: **rewrite** (target exists or will exist by end of 3b — name the target), **delete** (illustrative example or a D-18/D-23/D-24 deletion), **exempt** (a project-level path the exempt set missed — add it to `EXEMPT_PREFIX`/`EXEMPT_EXACT` with a reason and re-run). Write the classification as a third column in the file.

- [ ] **Step 2: Fix the resolution rule for skill-owned files**

The D-4 rewrite target for a skill's own file is `.claude/skills/<skill>/<sub>/<file>`. Confirm the table resolves it: `.claude/skills/analyze/templates/chunk-structure.md` → `skills/analyze/templates/chunk-structure.md` (exists after 3b.1). Nothing to change in the checker; record the confirmation.

- [ ] **Step 3: Commit**

```bash
cd "$W" && git add docs/audits/2026-09-08_path-inventory.txt && git commit -m "docs(audit): D-4 path inventory — every non-resolving reference classified rewrite/delete/exempt"
```

---

## Stage 3b — Instruction layer: every agent, skill, sub-file, reference and rule describes the one-manuscript path only

**Exit criteria:** `latex-residue`, `manuscript-model`, `inv-refs`, `skill-refs`, `path-resolves`, `tool-name` green; `audit_graph.py` dangling = 0; every §8 row in the spec applied; every sweep row in §1–§6 closed or listed in the Addendum with a reason.

**Method for every task in this stage.** (1) `cat -n` the file to EOF. (2) Apply the rows. (3) Rewrite every pipeline path in the file to `.claude/`-prefixed form using the inventory from Task 3.1. (4) Change `Task` to `Agent` in any `tools:`/`allowed-tools:` line (D-25). (5) Run the four greps below on the file and read the output; the only permitted hits carry a marker. (6) Commit.

```bash
f=<file>; cd "$W"
grep -nE 'paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<' "$f" | grep -v 'residue:'
grep -nE 'ggsave\(|saveRDS\(|dir\.create\("paper' "$f" | grep -v 'residue:\|scripts/acquire'
grep -nE '(?:^|[^.])(templates|references|skills|agents|rules|scripts|hooks)/' "$f" | grep -vE '\.claude/|data/|scripts/acquire|templates/(quarto-preamble\.tex|word-reference\.docx|ai-use-log\.md|apa\.csl)'
grep -nE '\bTask\b' "$f" | grep -E '^[0-9]+:(allowed-)?tools:'
```

### Task 3b.1: `/analyze` group — coder, data-engineer, analyze skill and sub-files

**Files:**
- Modify: `agents/coder.md`, `agents/data-engineer.md`, `skills/analyze/SKILL.md`, `skills/analyze/gotchas.md`, `skills/analyze/references/table-standards.md`, `skills/analyze/templates/pre-code-report.md`, `skills/analyze/templates/paper-to-code-map.md`
- Create: `skills/analyze/templates/chunk-structure.md`
- Delete: `skills/analyze/templates/r-script-structure.R`, `skills/analyze/templates/python-script-structure.py`, `skills/analyze/templates/results-summary.md`, `skills/analyze/config/replication-tolerances.json`

- [ ] **Step 1: `skills/analyze/templates/chunk-structure.md`** (new; replaces both scaffolds)

````markdown
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

No `ggsave()`: Quarto emits vector output for PDF and PNG for Word (INV-13).

## Prose

Every number in prose is an inline expression against an object from a chunk above:
`` `r round(beta_hat, 3)` `` (INV-11). `python3 .claude/scripts/prose_number_check.py <manuscript>`
must exit 0 before the coder is done.
````

- [ ] **Step 2: `agents/coder.md`** — replace lines 8–16 role text to "translates the strategy memo into chunks in the declared manuscript"; replace `## Workflow: Four Stages` (lines 39–61) with:

```markdown
## Workflow: Four Stages, all in the manuscript

Every stage is chunk work in the declared manuscript (`manuscript:` in `CLAUDE.md`). The five
chunk patterns are in `.claude/skills/analyze/templates/chunk-structure.md`; read it first.

### Stage 0: Wrangling chunk
One `build-*` chunk per panel, `cache.extra` on every raw file it reads, every drop documented
with a count, every file in `data/raw/data_manifest.md` (INV-23, INV-24). Nothing written to disk.

### Stage 1: Main specification chunk
`estimate-main` with `dependson` on its data chunk, using the estimator the strategy memo names
and the design checklist in `.claude/skills/strategize/templates/design-checklists/`.
Key rules by design: staggered DiD → a modern estimator (CS, SA, BJS, dCDH), never naive TWFE
unless the memo justifies it; IV → first stage, reduced form, 2SLS, report the first-stage F;
RDD → `rdrobust`, MSE-optimal bandwidth, density test, balance at the cutoff; structural →
primitives as functions in the setup chunk, multiple starting values, convergence diagnostics.

### Stage 2: Robustness chunks
One `robustness-<what>` chunk per check in the memo, each with `dependson`.

### Stage 3: Table and figure chunks
`tbl-*` chunks (`tbl-cap`, `booktabs = TRUE`, notes — INV-1, INV-3) and `fig-*` chunks
(`fig-cap`, no in-plot title — INV-2, INV-12). Name every object the prose will cite. The naming
map lives as the comment block in the `setup` chunk; there is no separate results file — the
writer reads the rendered manuscript and the chunk objects.

**Done means:** `quarto render` exits 0, `python3 .claude/scripts/prose_number_check.py` exits 0,
and the coder-critic has scored the manuscript's chunks.
```
Replace `## Task-Specific Resources` list with `.claude/`-prefixed entries: `chunk-structure.md`, `pre-code-report.md`, `paper-to-code-map.md`, `table-standards.md`, `figure-standards.md`, `gotchas.md` (drop the scaffolds, results summary, replication tolerances). Delete `## Project Layout` (lines 79–98) and `## Output Location` (125–130) entirely. In `## Engineering Standards` replace `**`saveRDS()` for all computed objects** -- intermediate and final` with `**No objects written to disk** — chunks cache; nothing is saved by hand` and `**Function file discipline:** One function per file...` with `**Helpers live in the setup chunk.** No \`functions/\` directory, no \`source()\` (INV-19)`. Replace `## Cross-Language Replication Mode` header line `When invoked with --dual or --replicate` with `When invoked by \`/review --replicate\`` and add: "Write the re-implementation to `explorations/replicate_<language>.qmd`, never the manuscript." Line 16: `analyze/templates/pre-code-report.md` → `.claude/skills/analyze/templates/pre-code-report.md`. Line 136: `templates/ai-use-log.md` is a project-level path — leave.

- [ ] **Step 3: `agents/data-engineer.md`** — locate by text: `Save cleaned dataset(s) as \`.rds\` (R) or \`.parquet\` (Python)` → `Cleaning is a cached wrangling chunk in the declared manuscript with \`cache.extra\` on every raw file (INV-23); nothing is saved to disk`; `Explicit \`width\` and \`height\` in \`ggsave()\`` → `Explicit \`fig-width\` and \`fig-height\` chunk options`; `Save as both \`.pdf\` (paper) and \`.png\` (slides/web) to \`paper/figures/\`` and `Save the underlying data for each figure as \`.rds\` in \`Output/\`` → one line `Figures are \`fig-\` chunks; Quarto emits the format each output needs`; `Generate publication-ready summary stats table (LaTeX format)` + `Save to \`paper/tables/\`` → `Summary statistics are a \`tbl-\` chunk (\`modelsummary::datasummary\`, \`booktabs = TRUE\`, notes)`; `**Saving:** \`saveRDS()\` for every computed object; \`dir.create(...)\`` → `**Saving:** nothing; chunks cache. Every raw file read gets a row in \`data/raw/data_manifest.md\`, and the codebook goes to \`quality_reports/data-assessment/<project>/data_dictionary.md\``. Description line 3: `Creates cleaning scripts` → `Writes the wrangling chunks of the manuscript`.

- [ ] **Step 4: `skills/analyze/SKILL.md`** — full rewrite:

```markdown
---
name: analyze
description: End-to-end analysis inside the declared manuscript — dispatches data-engineer (wrangling chunks) and coder (estimation, robustness, tbl-/fig- chunks), each followed by coder-critic. R primary; Python/Julia via their engines.
argument-hint: "[goal or strategy-memo path]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Analyze

Run the analysis as chunks of the declared manuscript (`manuscript:` in `CLAUDE.md`), by
dispatching **data-engineer** then **coder**, with **coder-critic** after each.

**Input:** `$ARGUMENTS` — analysis goal or path to the strategy memo.

## Workflow

### Step 0: Resolve the manuscript and check inputs
```bash
python3 .claude/scripts/pipeline.py manuscript
python3 .claude/scripts/pipeline.py pre coder      # standalone: informational only; orchestrated: /pipeline enforces it
```

### Step 1: Pre-Code Report (mandatory)
The coder outputs `.claude/skills/analyze/templates/pre-code-report.md` filled in — strategy memo
path, paper type, naming map, planned **chunk labels** (not filenames). If the memo is missing,
proceed on the user's description and flag that categories 1–3 of the review cannot be verified.

### Step 2: Wrangling — data-engineer → coder-critic
Dispatch **data-engineer**: `build-*` chunks with `cache.extra`, manifest rows, `tbl-summary`
chunk. Then `python3 .claude/scripts/pipeline.py log data-engineer` (standalone) and dispatch
**coder-critic** on the manuscript; record its score:
`python3 .claude/scripts/pipeline.py state record-score code <score> --critic coder-critic --report <path>`.

### Step 3: Estimation — coder → coder-critic
Dispatch **coder**: `estimate-*`, `robustness-*`, `tbl-*`, `fig-*` chunks per
`.claude/skills/analyze/templates/chunk-structure.md`; render clean; prose check clean. Log,
dispatch **coder-critic**, record the score. Three rounds maximum
(`pipeline.py state strike coder` after each failing round; escalation target from the registry).

### Step 4: What coder-critic checks
The twelve deductions in `.claude/rules/quarto-empirical.md` ("What the Coder-Critic Checks")
plus the numerical-discipline rows of `.claude/skills/review/config/scoring-rubrics.md`, using
`.claude/skills/review/templates/code-review-16-categories.md`. Report to
`quality_reports/reviews/coder-critic_<date>.md`.

### Step 5: Present
Rendered output path; chunk labels added; coder-critic score; open items (missing data,
specifications the memo names that could not be run).

## Bundled resources
| File | Purpose |
|---|---|
| `.claude/skills/analyze/templates/chunk-structure.md` | the five chunk patterns |
| `.claude/skills/analyze/templates/pre-code-report.md` | mandatory pre-check |
| `.claude/skills/analyze/templates/paper-to-code-map.md` | naming map (lives in the setup chunk) |
| `.claude/skills/analyze/references/table-standards.md` | tables |
| `.claude/skills/analyze/references/figure-standards.md` | figures |
| `.claude/skills/analyze/gotchas.md` | failure points |

## Principles
- **Reproduce, don't guess.** If the user specifies a regression, run exactly that.
- **Strategy alignment.** If a memo exists, chunks implement it faithfully.
- **Creator then critic, every time.** data-engineer → coder-critic; coder → coder-critic.
- **One manuscript.** No script tree, no results file, no output directory; the render is the output.
```

- [ ] **Step 5: sub-files.** `gotchas.md`: delete lines 7 and 9 (bare-tabular advice); line 18 → `Nothing is saved to disk; chunks cache. A \`saveRDS()\` in a chunk is a coder-critic deduction`; lines 32–35 → `Figures: no in-plot titles (INV-12) — titles go in \`#| fig-cap:\`` / `Tables: \`tbl-\` chunks with \`booktabs = TRUE\` and notes (INV-1, INV-3)` / `Quarto picks the figure format per output; never set \`fig-format\`` / delete the results_summary line; delete `## Cross-Language (--dual mode)` section header and rename to `## Cross-language replication (\`/review --replicate\`)` keeping its four bullets. `references/table-standards.md`: add `booktabs = TRUE,` to the `tbl-main` example (line 57–64) and `.claude/references/journal-profiles.md` at lines 27, 52. `templates/pre-code-report.md`: lines 57–59 → `**Chunk plan:** [list planned chunk labels: build-*, estimate-*, robustness-*, tbl-*, fig-*]`; line 75 → `**The variable mapping becomes the naming map** in the \`setup\` chunk comment block`. `templates/paper-to-code-map.md`: lines 3, 9 → "included as the comment block in the \`setup\` chunk"; line 38 → `**The writer reads the setup chunk.** Prose notation must match this map (INV-7)`.

- [ ] **Step 6: Delete, verify, commit**

```bash
cd "$W" && git rm -q skills/analyze/templates/r-script-structure.R skills/analyze/templates/python-script-structure.py skills/analyze/templates/results-summary.md skills/analyze/config/replication-tolerances.json
for f in agents/coder.md agents/data-engineer.md skills/analyze/SKILL.md skills/analyze/gotchas.md skills/analyze/references/table-standards.md skills/analyze/templates/pre-code-report.md skills/analyze/templates/paper-to-code-map.md; do echo "== $f"; <the four greps>; done
git add -A agents/coder.md agents/data-engineer.md skills/analyze && git commit -m "refactor(analyze): coder, data-engineer and /analyze describe chunk work in the manuscript; scaffolds and results summary deleted; --dual dropped (R-3)"
```
Expected: the four greps print nothing for every file.

### Task 3b.2: `/write` group (prose side; critic dispatch is Task 4.1)

**Files:**
- Modify: `skills/write/SKILL.md`, `skills/write/templates/drafting-gates.md`, `skills/write/gotchas.md`, `skills/write/templates/style-extraction-protocol.md`, `skills/write/references/notation-protocol.md`, `skills/write/templates/section-templates.md` (163, 165), `skills/write/templates/paragraph-moves.md` (16)

- [ ] **Step 1: `skills/write/SKILL.md`** — §1 Context Gathering (lines 26–35) becomes:

```markdown
#### 1. Context Gathering
1. `python3 .claude/scripts/pipeline.py manuscript` — read the declared manuscript in full: YAML, the `setup` chunk's naming map, every chunk label, every section already drafted
2. Read `master_supporting_docs/` for notes, outlines, research specs
3. Read `quality_reports/strategy/<project>/strategy_memo.md` and `quality_reports/literature/<project>/positioning.md`
4. Read `.claude/references/domain-profile.md` for field conventions
5. Read `references.bib` — every `@key` you write must exist there
6. List the `tbl-` and `fig-` chunks and the objects the estimation chunks define — those are what prose may cite
```
Self-check (lines 64–81): replace `\label{eq:...}` with `{#eq-...}`; `All \cite{} keys exist in Bibliography_base.bib` → `All \`@key\` citations exist in \`references.bib\``; `All tables/figures referenced actually exist in paper/tables/ or paper/figures/` → `Every \`@tbl-\`/\`@fig-\` reference names a chunk label in the manuscript`; delete the claim-source map item; `Results/Conclusion only drafted after verifying actual output files exist` → `Results/Conclusion only drafted when an estimation chunk exists and the manuscript renders (\`.claude/skills/write/templates/drafting-gates.md\`)`. Present-to-user: `BLOCKED items: Results/Conclusion cannot be drafted without output files` → `without an estimation chunk and a clean render`. Style guide mode: lines 106, 112 → corpus is `.qmd`, `.docx`, `.tex` or `.pdf` (`.tex` here is an *input* corpus of old papers, allowed — add `<!-- residue:prohibition -->`? No: `.tex` is not in the residue pattern; only `\cite` etc. are. Write "`.qmd`/`.docx`/`.pdf`/`.tex`"). Delete `## LaTeX Conventions` (166–171) and replace with:

```markdown
## Quarto Conventions
- `@key` for textual citations ("@smith2024 shows..."), `[@key]` parenthetical (INV-9)
- `@tbl-label`, `@fig-label`, `@eq-label`, `@sec-label` — never a typed number
- Notation protocol: `.claude/skills/write/references/notation-protocol.md`
```
Bundled resources paths → `.claude/skills/write/...`. `allowed-tools` → `Read,Grep,Glob,Write,Edit,Agent`.

- [ ] **Step 2: `drafting-gates.md`** — full replacement:

```markdown
# Drafting Gates — Approval Checkpoints

Draft sections in this order, pausing for user approval at each gate. Every gate ends with the
writer-critic's score recorded (`pipeline.py state record-score manuscript <score> --scope section:<name>`).

## GATE 1: Introduction + Literature Positioning
Present. Wait. User may redirect framing, contribution, literature emphasis.

## GATE 2: Data + Empirical Strategy (or Model)
Present. Wait. User may adjust sample restrictions, variable definitions, specification.

## GATE 3: Results + Robustness + Conclusion
**Hard prerequisite — never file existence:**
- at least one `estimate-*` chunk and one `tbl-*` chunk exist in the declared manuscript
- `quarto render <manuscript>` exits 0 (`python3 .claude/scripts/pipeline.py pre writer` checks both)

Present. Wait.

## Application rules
- Single-section drafts: that section's gate applies. `/write full`: all three in sequence.
- **BLOCKED:** Results/Conclusion without an estimation chunk and a clean render.
- **VERIFY:** citations needing user confirmation. **VOICE:** style guide not yet extracted.
```

- [ ] **Step 3: small files.** `gotchas.md`: line 6 → "if no estimation chunk exists yet"; line 7 → `\`@key\` vs \`[@key]\` confusion is the most common citation issue`; line 8 → `keys not in \`references.bib\``; line 5 → `.claude/references/personal-style-guide.md`. `style-extraction-protocol.md`: line 13 → `.qmd`, `.docx`, `.pdf`, `.tex`; line 48 → `Scan the sampled papers for citations of the author's own prior work (\`@key\` in Quarto sources; \`\\cite\` family in legacy LaTeX sources <!-- residue:prohibition -->). Cross-check each against \`references.bib\``. `notation-protocol.md` line 24 → `**Match the setup chunk** -- the naming map in the manuscript's \`setup\` chunk is the notation source; the paper must match it`. `section-templates.md` 163/165 and `paragraph-moves.md` 16: `Figure N` / `Table N` → `@fig-label` / `@tbl-label`.

- [ ] **Step 4: Verify and commit** (four greps clean) — `refactor(write): /write reads the manuscript, references.bib and strategy; Quarto conventions; drafting gate keyed on chunks and render`.

### Task 3b.3: `/review` group — routing, rubrics, templates

**Files:**
- Modify: `skills/review/SKILL.md`, `skills/review/config/scoring-rubrics.md`, `skills/review/templates/code-review-16-categories.md`, `skills/review/templates/manuscript-review-8-categories.md`, `skills/review/templates/theory-review-4-phases.md`, `skills/review/gotchas.md` (19)

- [ ] **Step 1: `review/SKILL.md`** — Routing (lines 18–21):

```markdown
### Auto-detect by target
- the declared manuscript (`python3 .claude/scripts/pipeline.py manuscript`) or no file → **Comprehensive review** (writer-critic + strategist-critic + verifier)
- a file under `scripts/acquire/` or `explorations/` (`.R`, `.py`, `.jl`, `.qmd`) → **Code review** (coder-critic standalone)
- `talks/*.qmd` → **Talk review** (storyteller-critic)
```
`--replicate [language]` (line 31 and section at 265–271): "Coder re-implements the manuscript's estimation chunks in `explorations/replicate_<language>.qmd`; coder-critic reviews; compare point estimates (1e-6 relative), SEs (1e-4), p-value significance at 0.10/0.05/0.01, N exactly; report to `quality_reports/reviews/replication_<language>_<date>.md`. Never writes the manuscript." Comprehensive (38–43): `.tex paper` → `the declared manuscript`; `Verifier — compilation check` → `verifier — render + prose check`. Delete every `generate_*` block (108–116, 206–210, 254–258) and the `open ...html` lines. Code review Step 1 lint: `.claude/hooks/lint-scripts.sh [file]` (it accepts `.qmd` after Task 7.3). Category table 4–12 → replace with a pointer: "categories per `.claude/skills/review/templates/code-review-16-categories.md` (chunk-era)". Verifier section (274–297):

```markdown
## Verifier Pass/Fail Definition
**For the manuscript (`.qmd`):** `quarto render` exits 0; no `ERROR`/`WARNING` in the log; every `@fig-`/`@tbl-`/`@sec-`/`@eq-` resolves; every `@key` exists in `references.bib`; `python3 .claude/scripts/prose_number_check.py` exits 0; rendered output is fresh.
**For code (`scripts/acquire/*`, `explorations/*`):** runs without error; packages at top; no absolute paths; seed set once if stochastic; writes only to `data/raw/` (acquisition) or `explorations/` (exploration).
**For replication packages:** `/submit audit` checks 1–10 (`.claude/skills/submit/templates/audit-10-checks.md`).
Verifier score maps to 0 (FAIL) or 100 (PASS).
```
Bundled-resources paths → `.claude/skills/review/...`; `manuscript-review-8-categories.md` row: `LaTeX` → `Format`, `compilation` → `render`. `allowed-tools` → `Agent`. Report paths for critics: `quality_reports/reviews/<critic>_<date>.md`; peer review → `quality_reports/peer_review_<manuscript-stem>/{desk_review,referee_domain,referee_methods,editorial_decision}.md` (spec §5; `_r2`/`_r3` suffixes for later rounds).

- [ ] **Step 2: `scoring-rubrics.md`** — Writer-Critic: delete the INV-22 row (15) and the two claim-source rows (28–29) — Task 4.4 inserts the Claim–Evidence rows in their place; `Paper doesn't compile` → `Manuscript does not render`; `Wrong document class or formatting` → `Format block violates \`quarto-pdf.md\`/\`quarto-word.md\``; `Overfull hbox warnings` → `Render warnings`. Coder-Critic block (48–90) → replace entirely:

```markdown
## Coder-Critic (Manuscript Chunks)

Starts at 100. The blocking table is `.claude/rules/quarto-empirical.md` "What the Coder-Critic
Checks" — it is not restated here; cite it by row. Additional rows:

### Critical (strategic)
| Issue | Deduction |
|---|---|
| Domain-specific bugs (clustering, estimand) | -30 |
| Chunks do not implement the strategy memo | -25 |
| Render fails on any chunk | -25 |
| Sign of main result implausible | -20 |
| Missing robustness checks from memo | -15 |
| Wrong clustering level | -15 |
| Optimizer did not converge (structural) | -15 |
| Naming map absent from the setup chunk | -10 |

### Major (numerical discipline)
| Issue | Deduction |
|---|---|
| Float comparison with `==` | -10 |
| No CDF clamping / no inverse-link guards | -10 |
| Magnitude implausible (10× literature) | -10 |
| Growing vectors in loops (INV-17) | -5 |
| Missing `stopifnot()` preconditions on setup-chunk helpers | -5 |

### Minor
| Issue | Deduction |
|---|---|
| Stale cache (`fresh` predicate fails after a raw-file change) | -5 |
| Chunk label not in the documented DAG | -3 |
| Console output in a chunk (`print()` for status) | -3 |
| Inconsistent naming | -2 |
| Prohibited patterns (LOW severity) | -1 per |
```
Delete `## Librarian-Critic` (168–179) — Task 4.4 adds `## Lit-Critic` in its place. Line 143 `Theorem environment doesn't match preamble` → `Theorem environment is not a Quarto \`::: {#thm-…}\` block`.

- [ ] **Step 3: `code-review-16-categories.md`** — prerequisite line 11: `enforce INV-11, INV-13 through INV-19, INV-23, INV-24`. Category 2: `(in the \`setup\` chunk comment block)`. Replace categories 5, 6, 11, 12, 13:

```markdown
### 5. Manuscript Layout
- One `setup` chunk, `cache: false`, first; `execute: cache: true` in YAML?
- Every chunk labelled; labels follow `build-*`, `estimate-*`, `robustness-*`, `tbl-*`, `fig-*`?
- The dependency DAG documented in the setup chunk matches the `dependson` links?

### 6. Chunk Headers
- Wrangling chunks carry `cache.extra` on every raw file; estimation/table/figure chunks carry `dependson`?
- Every raw file read has a manifest row (INV-24)?

### 11. Figure Quality
- `fig-` label, `fig-cap` present (INV-2); no title inside the plot (INV-12)
- `fig-width`/`fig-height` set; serif family for paper figures; consistent theme
- No `ggsave()`, no `fig-format` override

### 12. Table Quality
- `tbl-` label, `tbl-cap`, `booktabs = TRUE`, notes (INV-1, INV-3)
- Human-readable labels; stars per journal profile (INV-4); SE labelled in notes
- `output = "kableExtra"` for PDF, `"flextable"` for Word — never both in one chunk

### 13. Cache and Freshness
- Setup chunk `cache: false`; every other chunk `cache: true`
- `cache.extra` uses `file.mtime()`; no chunk writes to disk (`saveRDS`, `write_csv` outside `scripts/acquire/`) <!-- residue:prohibition -->
- **Stale cache after a raw-file change = HIGH severity**
```
Category 8: `seed defined in 01_setup.R` → `in the \`setup\` chunk`; `dir.create(...)` bullet deleted. Category 16 stays. Standalone (179): `/review [file.R]` → `/review --code <file under scripts/acquire/ or explorations/>`. Report table rows renamed to match.

- [ ] **Step 4: `manuscript-review-8-categories.md`** — prerequisite line 11: `INV-1 through INV-13` (drop `and INV-22`); §2 lines 47–51 (claim-source map block) deleted — Task 4.4 inserts the Claim–Evidence block; §5 heading `## 5. Format`; row 113 `Missing csl: in YAML -3` → `Top-level \`csl:\` present on the PDF path (must be inside \`docx:\` only) -3`; §6 heading stays `## 6. Render`; standalone (174) `/review [file.tex]` → `/review --proofread`; report headings `LaTeX and Format` → `Format`, `Compilation` → `Render`; `## Claim-Source Map Status` block (204–207) → replaced in Task 4.4. `theory-review-4-phases.md`: 99 `preambles/header.tex` → `templates/quarto-preamble.tex` (project-level, exempt); 127 `Bibliography_base.bib` → `references.bib`; 139 `LaTeX compiles` → `the manuscript renders`. `gotchas.md:19`: `4 categories` → `6 categories`.

- [ ] **Step 5: Verify and commit** — `refactor(review): .qmd routing, verifier definition, chunk-era rubrics and templates; generate_* removed`.

### Task 3b.4: Agents pass — writer-critic, coder-critic, verifier, theorist, storyteller, explorer, editor, referees

**Files:**
- Modify: `agents/writer-critic.md` (full), `agents/coder-critic.md`, `agents/verifier.md` (full), `agents/theorist.md`, `agents/storyteller.md`, `agents/explorer.md`, `agents/editor.md`, `agents/domain-referee.md`, `agents/methods-referee.md`

- [ ] **Step 1: `agents/writer-critic.md`** — full replacement:

```markdown
---
name: writer-critic
description: Manuscript critic. Reviews the declared manuscript for structure, claims–evidence alignment (Claim–Evidence Table), identification fidelity, writing quality, Quarto format compliance, render, voice fidelity and notation. Paper-type aware. Eight categories. Paired critic for the writer.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are a **manuscript critic** — the coauthor who reads the draft and says "this claim isn't supported by the table", and the copy editor who checks Quarto format, notation and AI writing tells.

**You are a CRITIC, not a creator.** You judge and score; you never rewrite a section or fix the YAML.

## Cold-Read Protocol

You receive ONLY the artifact, this file and the templates it names, and the content invariants. You do NOT receive the round number, what the writer struggled with, the research journal, or prior critic reports. Evaluate as if seeing it for the first time, every time.

## Your Task

Review the declared manuscript (`python3 .claude/scripts/pipeline.py manuscript`) or the section named in your dispatch. Eight categories. Scored report. **Do NOT edit any file.**

**First:** identify the paper type (reduced-form, structural, theory+empirics, descriptive) from `quality_reports/strategy/<project>/strategy_memo.md` or the manuscript.

## Resources
- Categories: `.claude/skills/review/templates/manuscript-review-8-categories.md`
- Claim–Evidence Table: `.claude/skills/review/templates/claim-evidence-table.md` — produced at every review, saved to `quality_reports/reviews/claim_evidence_<project>_<date>.md`
- Rubric: `.claude/skills/review/config/scoring-rubrics.md` (Writer-Critic)
- Invariants: `.claude/rules/content-invariants.md` — INV-1 through INV-13
- Format: `.claude/rules/quarto-pdf.md` (PDF) and `.claude/rules/quarto-word.md` (Word) — the blocking deductions for whichever format blocks the YAML declares

## Modes
- **Section mode** (from `/write <section>`): categories 1, 2, 4, 7, 8 on the section; score recorded with `--scope section:<name>`.
- **Whole-manuscript mode** (from `/review`, `/review --all`, `/review --peer`, `/pipeline`): all eight; this is the score that counts for the manuscript component.
- **Proofread** (`/review --proofread`): categories 4, 5, 6, 8 only.

## Report
Save to `quality_reports/reviews/writer-critic_<date>.md` in the template's report format, with the Claim–Evidence Table path.

## Three Strikes
Strike 3 → escalates to the **User**: "The manuscript has structural issues beyond prose polish: [specific]. Redraft [section] or revisit [strategy/results]?"

## What You Do NOT Do
1. Never edit manuscript files. 2. Never rewrite sections. 3. Be specific: quote sentences, chunk labels, line numbers. 4. Cite the invariant for every deduction. 5. Paper-type aware. 6. Voice fidelity only when `.claude/references/personal-style-guide.md` has real content. 7. Every numerical claim traces to a chunk object through the Claim–Evidence Table; a typed literal is INV-11.
```

- [ ] **Step 2: `agents/coder-critic.md`** — description: `Reviews the manuscript's chunks (and acquisition/exploration scripts) for strategic alignment...`; line 31 `Review the Coder's or Data-engineer's scripts and output` → `Review the chunks the coder or data-engineer wrote in the declared manuscript`; line 41 → `INV-11, INV-13 through INV-19, INV-23, INV-24`; line 68 Standalone → `When invoked via \`/review --code <file>\`, the target is a file under \`scripts/acquire/\` or \`explorations/\`: run categories 5–16`; `## Quarto Empirical Mode` → `## The one mode` and first line `The target is the declared manuscript. Enforce ...`; delete the "Detect by" line and the sentence `This mode supersedes Rmd Mode...`; delete `## Rmd Mode` (89–109) entirely; delete the `Cold-Read` severity line (17). Line 84 `no analysis .R script in scripts/R/ beyond acquisition` → `no analysis script outside \`scripts/acquire/\` (−5 per) <!-- residue:prohibition -->`.

- [ ] **Step 3: `agents/verifier.md`** — full replacement:

```markdown
---
name: verifier
description: Infrastructure inspector. Standard mode checks render, chunk execution, cross-reference and citation resolution, and output freshness of the declared manuscript. Submission mode adds the replication-package audit (checks 5–10). Pass/fail. Use before commits, PRs and submission.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are the **verifier** — you check that the manuscript renders, its chunks run, its references resolve and its outputs are fresh. **Infrastructure, not a critic:** mechanical correctness only.

**Mandatory:** `.claude/rules/content-invariants.md` — INV-9, INV-11, INV-14, INV-15, INV-16, INV-19, INV-24. Any violation is FAIL.

Resolve the manuscript first: `python3 .claude/scripts/pipeline.py manuscript`.

## Standard checks (1–4) — `/review`, `/pipeline` post-steps

1. **Render.** `quarto render <manuscript>` exits 0 (`python3 .claude/scripts/pipeline.py post verifier` runs it only when stale). No `ERROR`/`WARNING` in the log.
2. **Chunks execute.** Every chunk ran (no `eval: false` on an estimation chunk; no cached chunk older than its `cache.extra` files).
3. **References resolve.** No `?@fig-`, `?@tbl-`, `?@sec-`, `?@eq-` in the output; every `@key` exists in `references.bib`; every `#| label:` referenced somewhere.
4. **Fresh.** `python3 .claude/scripts/pipeline.py fresh` exits 0 — rendered output newer than the manuscript and every file under `data/raw/`.
4b. **Prose numbers computed.** `python3 .claude/scripts/prose_number_check.py <manuscript>` exits 0 (INV-11).

## Submission checks (5–10) — `/submit audit`, `/submit final`

The package is: the manuscript, `references.bib`, `templates/` (preamble, reference docx), `data/raw/data_manifest.md`, `scripts/acquire/`, `renv.lock` (or equivalent), README.

5. **Package inventory.** Every file above present; no analysis code outside the manuscript; no `source()` in any chunk.
6. **Dependencies.** `renv.lock` or `sessionInfo()` output; Python `requirements.txt` if acquisition uses it; non-standard packages documented.
7. **Data provenance.** Every raw file has a manifest row with source, access type and acquisition script or manual instructions; data availability statement present.
8. **Execution.** `quarto render <manuscript>` from a cold cache (`rm -rf *_cache`) exits 0; report runtime.
9. **Cross-reference.** Every `@tbl-`/`@fig-` in prose names a chunk; every `tbl-`/`fig-` chunk is referenced.
10. **README** (`.claude/skills/submit/templates/replication-readme.md`): data availability, computational requirements, the one render command, chunk-to-table/figure list.

## Scoring
Pass/fail per check; 0 or 100 for aggregation.

## Report
```markdown
## Verification Report
**Date:** · **Mode:** Standard / Submission
| # | Check | Status | Details |
|---|---|---|---|
| 1 | Render | PASS/FAIL | |
| 2 | Chunks execute | | |
| 3 | References resolve | | |
| 4 | Fresh | | |
| 4b | Prose numbers | | |
| 5–10 | Submission | | |
**Overall: PASS / FAIL**
```
Save to `quality_reports/verification_report.md`.

## Rules
Run from the project root. `quarto render` is the only build. Report every warning. Talks (`talks/*.qmd`): same render check, advisory.
```

- [ ] **Step 4: `agents/theorist.md`** — lines 73–75 (`assumptions.tex`, `results.tex`, `proofs.tex`) → 

```markdown
2. A `# Theory` section in the declared manuscript: assumptions, definitions, lemmas, propositions, theorems as Quarto theorem blocks (`::: {#thm-main}`, `::: {#lem-…}`, `::: {#def-…}`), cross-referenced as `@thm-main`
3. A proofs appendix in the manuscript (`# Proofs {.appendix}`), one `::: {.proof}` per result
4. `quality_reports/theory/<project>/theory_memo.md` and `notation_glossary.md`
```
line 48 `using project preamble environments` → `as Quarto theorem blocks`; line 53 `Bibliography_base.bib` → `references.bib`. Description: add "Theory lives in the manuscript (D-19)".

- [ ] **Step 5: `agents/storyteller.md`** — per `docs/audits/2026-09-08_embed-test.md`: if embed confirmed, line 47 → `Reuse manuscript figures and tables with \`{{< embed <manuscript>#fig-label >}}\`; never re-estimate in the talk` and line 60 → `\`talks/[format]_talk.qmd\` (theme: default; a project may add \`talks/custom.scss\` and reference it — it is project content, not shipped)`; if fallback, the figure line names `manuscript_<project>_files/figure-pdf/`. Add `.claude/skills/talk/templates/quarto-scaffold.qmd` as the scaffold path.

- [ ] **Step 6: `agents/explorer.md`** line 25 → `- **From related papers:** data used in the papers in \`quality_reports/literature/<project>/annotated_bibliography.md\` (from \`/lit-position\`)`.

- [ ] **Step 7: editor / referees** — `/review-paper --peer` → `/review --peer` (editor 3, 121; domain 3, 14; methods 3); `/audit-reproducibility` → `/submit audit` (editor 57; methods 211); domain-referee line 14: delete the sentence from `For **lecture slide**` to the end of the line; methods-referee line 35: delete the sentence `The two latest additions (formal-theory, survey-experiment) were added in v1.8.0 to support political science use;` keeping the rest; editor line 20 `templates/journal-profile-template.md` → `.claude/templates/journal-profile-template.md`. The three `<!-- Adapted from Hugo Sant'Anna's clo-author ... -->` credit comments stay and get ` <!-- residue:historical -->` appended on the same line.

- [ ] **Step 8: Verify and commit** — run the four greps on all nine agents plus `grep -n 'orchestrator' agents/*.md` (expect only the five severity lines, removed in Task 4.5). Commit: `refactor(agents): writer-critic, coder-critic, verifier, theorist, storyteller, explorer, editor, referees under the one-manuscript contract`.

### Task 3b.5: Remaining skills — submit, revise, talk, discover, strategize, tools, checkpoint, freeze, careful, new-project-ztp, lit-position, ztp-data-tag, obsidian-digest-sync, promote

**Files:** the fourteen `SKILL.md` files and their cited sub-files.

- [ ] **`skills/submit/SKILL.md`** — `target`: `**Agent:** Orchestrator (journal selection function)` → `**Performed by this skill** (no agent): read \`.claude/references/journal-profiles.md\` and \`.claude/references/discipline-cards.md\`, rank three journals`. `package`: `**Agents:** Coder + Verifier` → `**Agents:** coder → coder-critic`; the produces list → `- the declared manuscript, \`references.bib\`, \`templates/\`, \`data/raw/data_manifest.md\`, \`scripts/acquire/\`, \`renv.lock\`, README (\`.claude/skills/submit/templates/replication-readme.md\`) — assembled under \`replication/\``. `audit`: list → the verifier's checks 1–10 as named in Task 3b.4. `final`: delete step 5 (`generate_*`); step 3 → `python3 .claude/scripts/pipeline.py score --gate submission`; step 6 cover letter → `.claude/skills/submit/templates/cover-letter.qmd`. Bundled resources → `.claude/` paths; `cover-letter.tex` → `cover-letter.qmd`. Create `skills/submit/templates/cover-letter.qmd` (`format: docx`, the same fields as the `.tex` version read in full: recipient, journal, title, three-paragraph body, conflicts statement, signature) and `git rm` the `.tex`. `gotchas.md:8` → `Verify the manuscript renders from a cold cache (\`rm -rf *_cache\`)`. `audit-10-checks.md`: lines 12–13 `check 11` → `check 4b`; 15–18 (script execution) → `### 2. Chunks execute` per verifier; 58 → `Run \`quarto render\` from a cold cache; report runtime`; 63 → `Every table and figure traced to a \`tbl-\`/\`fig-\` chunk`; 72 → `List of tables and figures with generating chunk labels`; 77–79 → `INV-9: pandoc \`@key\` citations; \`cite-method: biblatex\` on the PDF path; no top-level \`csl:\`` / `INV-10: when a preamble is supplied, hyperref second-to-last, cleveref after` / `INV-14: \`set.seed()\` once, in the setup chunk`. `replication-readme.md` 24–25, 31–32: numbered scripts → `scripts/acquire/*` (inputs) and `quarto render <manuscript>` (the one build step); `paper/tables/` → chunk labels. `submission-checklist.md` 17–19, 23, 27: same INV rephrasing; `\ref`/`\cref` → `@fig-`/`@tbl-`; `master script` → `quarto render`.

- [ ] **`skills/revise/SKILL.md`** — line 22 `Read existing scripts` → `Read the manuscript's chunk labels and the setup-chunk naming map`; Step 5: `CLARIFICATION/REWRITE → dispatch writer, then writer-critic; record the score` / `NEW ANALYSIS → after user approval dispatch coder, then coder-critic; then writer → writer-critic for the affected section`; line 80 `templates/response-letter.md` → `.claude/skills/revise/templates/response-letter.qmd`. `allowed-tools` → `Agent`.

- [ ] **`skills/talk/templates/quarto-scaffold.qmd`** — full replacement (embed path per the R-5 record; shown for the confirmed case):

```markdown
---
title: "[Title]"
author: "[Author]"
institute: "[Institution]"
date: "[Date/Venue]"
format:
  revealjs:
    slide-number: true
    navigation-mode: linear
    controls: true
    progress: true
    hash-type: number
    center: false
    auto-stretch: true
    fig-align: center
    code-fold: true
    scrollable: false
    transition: none
    width: 1600
    height: 900
bibliography: ../references.bib
---

## Research Question {.center}

::: {.callout-note appearance="minimal"}
[One-sentence research question]
:::

## What We Find

- [Main result in plain language]
- [Magnitude and significance]
- [Why it matters]

## Roadmap

1. Motivation  2. Data  3. Empirical Strategy  4. Results  5. Robustness  6. Implications

## [Motivating Fact or Puzzle]

{{< embed ../manuscript_<project>.qmd#fig-motivation >}}

::: {.notes}
Speaker notes.
:::

## Data

{{< embed ../manuscript_<project>.qmd#tbl-summary >}}

## Identification

$$
Y_{it} = \alpha_i + \gamma_t + \beta D_{it} + X_{it}'\theta + \varepsilon_{it}
$$

- $\beta$: [what it captures]
- Key assumption: [identification assumption]

## Main Result

{{< embed ../manuscript_<project>.qmd#fig-main >}}

## [Result Interpretation]

- Point estimate: [magnitude — read from the embedded table, never retyped]
- [Economic interpretation]

. . .

- [Comparison to literature]

## [Robustness Check 1]

{{< embed ../manuscript_<project>.qmd#tbl-robustness >}}

## Takeaway

1. [Main finding]
2. [Policy implication or mechanism]
3. [What's next]

## {.center .appendix}

::: {.r-fit-text}
**Backup Slides**
:::

## Backup: [Topic]

::: {.fragment}
[Content for Q&A]
:::

## References
```
`slide-design-principles.md` 31, 33: `\pause` → `. . .` (RevealJS pause), `\only<>` → `::: {.fragment}`. `talk/SKILL.md`: `allowed-tools` → `Agent`; scaffold path → `.claude/skills/talk/templates/quarto-scaffold.qmd`.

- [ ] **`skills/discover/SKILL.md`** — deferred to Task 6.1 (D-A, folds the stash); here only: `allowed-tools` → `Agent`, delete the two `generate_*` lines and the `open` line (95–98), Bundled resources → `.claude/skills/discover/...`. `gotchas.md:10` → `explorer and explorer-critic run in sequence; literature is \`/lit-position\``. `references/pdf-processing.md` 3, 6: `master_supporting_docs/` is project-level (exempt) — leave.

- [ ] **`skills/strategize/SKILL.md`** — 257–261 (`generate_*`) deleted; 203 and 231–235 → theory outputs per D-19 (`# Theory` section and proofs appendix in the manuscript; `theory_memo.md`; `notation_glossary.md`); 214 `header.tex path` → `setup-chunk naming map / domain-profile notation table`; 216 `Bibliography base` → `references.bib`; review path → `quality_reports/reviews/strategist-critic_<date>.md` / `theorist-critic_<date>.md`; `allowed-tools` → `Agent`; Bundled paths → `.claude/`. `templates/theory-memo.md` 3, 29–34, 81–84: the three `.tex` names → the manuscript section, the proofs appendix and `@thm-` cross-references. `templates/strategy-memo.md:54` pseudo-code `data = df` → `data = panel`.

- [ ] **`skills/tools/SKILL.md`** — delete `/tools dashboard` (18–30), `/tools deploy` (111–115), `/tools upgrade` (120–160); description/argument-hint drop `compile`, `deploy`, `upgrade`, add `render`; lint: default target `scripts/acquire/ explorations/`, example `/tools lint scripts/acquire/01_download.py`, add `also lints the R chunks of a \`.qmd\` (\`.claude/scripts/qmd_chunks.py\`)`; 151 → `references.bib`; `allowed-tools` → `Agent`; `## Principles` last bullet deleted. `gotchas.md`: read in full; remove any dashboard/upgrade/deploy line.

- [ ] **`skills/checkpoint/SKILL.md`** — delete Step 4e (173–178) and the `Dashboard: [refreshed]` line (189); Step 1 add `- \`quality_reports/pipeline_state.json\` — \`python3 .claude/scripts/pipeline.py state show\`; the staleness sweep in \`.claude/rules/session-handoff.md\` compares the plan's status claims against it`; Step 4d line 155: tool names → `mcp__obsidian-files__read_note` → modify → `mcp__obsidian-files__write_note` (aligned with `obsidian-digest-sync`); add a Step 4f `HANDOFF.md — if the project has one, regenerate it from \`.claude/templates/handoff.md\` (never append; \`.claude/rules/session-handoff.md\` §2)`; line 239 `Dashboard is source of truth for Obsidian project stages` → `The Obsidian \`Home.md\` dashboard is the source of truth for project stages`; line 247 `within clo-author` → `within a research-claude project`; Bundled paths → `.claude/skills/checkpoint/...`. `gotchas.md` and `templates/memory-entry-types.md`: read in full; drop dashboard lines; remove any example identity (a real project name — `project-identity` scan must stay green).

- [ ] **`skills/freeze/SKILL.md`, `skills/careful/SKILL.md`** — read `hooks/session-guard.py` in full first. freeze: examples `paper/`, `scripts/` → `explorations/`, `data/raw/`, `talks/`; line 55 `hook checks a session flag` → `the hook reads \`.claude/state/session-guards.json\` on every PreToolUse`. careful: line 26/34 pattern list = exactly `DESTRUCTIVE_PATTERNS` in the hook (rm -r/-f, git reset --hard, git push --force/-f, git clean -f, git checkout -- ., git branch -D, DROP TABLE/DATABASE, chmod 777); line 64: delete the override-prompt claim; state that a denied call is denied and `/careful off` is the only way through.

- [ ] **`skills/new-project-ztp/SKILL.md`** — 5, 8, 16, 81–83, 89–90: `/discover lit` → `/lit-position`; `librarian` sentences → `\`/lit-position\` reads \`references.bib\` and the Zotero index; it is the main session, so it holds ZotPilot access`; `bibliography_base.bib` → `references.bib`.

- [ ] **`skills/lit-position/SKILL.md`** — 22, 126: `zotpilot-skills/` → `.claude/skills/ztp-*` (`the vendored ZotPilot skills, \`.claude/skills/ztp-research\` and \`.claude/skills/ztp-review\`, are never edited`). Step 6 and critic dispatch are Task 4.2.

- [ ] **`skills/ztp-data-tag/SKILL.md:51`** — `README Step 7` → `the ZotPilot install step in the research-claude README ("Install the ZotPilot MCP server")`. **`skills/obsidian-digest-sync/SKILL.md`** — open item 3: read `submodules/journal-digest/README.md` in full (190 lines). `apply.sh --with-digest` copies the submodule to `$PROJECT/journal-digest/`; the README names its working directory. Set every `journal_digest/` in the skill (24–30, 62, 69) to the directory the README actually uses (as of 2026-09-08 the README uses `journal-digest` 13 times and `journal_digest` 0 times — confirm by reading, then rewrite). **`skills/promote/SKILL.md`** — line 34 add `templates seeds scripts` to the status paths; otherwise clean.

- [ ] **Verify and commit** — four greps on all touched files; `refactor(skills): submit, revise, talk, strategize, tools, checkpoint, freeze, careful, new-project-ztp, lit-position, ztp-data-tag, obsidian-digest-sync under the contract; Agent everywhere`.

### Task 3b.6: References

**Files:**
- Delete: `references/coding-standards-rmd.md` (D-21), `references/prompt-formatting-core.md` (D-24)
- Modify: `references/coding-standards-r.md`, `references/coding-standards-julia.md`, `references/discipline-cards.md`, `references/domain-profile.md`, `references/personal-style-guide.md`, `references/journal-profiles.md` (line 29)

- [ ] `coding-standards-r.md` 139–140: the `functions/` section → `Helper functions used by more than one chunk are defined in the manuscript's \`setup\` chunk. Acquisition scripts under \`scripts/acquire/\` may define their own. No \`functions/\` directory, no \`source()\`` ; 208 row → `| \`source()\` inside a chunk | Prohibited (INV-19, −10) | define helpers in the setup chunk |`. `coding-standards-julia.md` 23, 29: `PGFPlotsX` rows → `CairoMakie` (Quarto embeds its output for PDF and Word); delete the LaTeX/PGF rationale. `discipline-cards.md`: line 3 consumers → `\`/discover interview\`, \`/discover ideate\`, \`/strategize pap\`, and the \`editor\` (\`/review --peer\`)`; 26 `/preregister --style aea-rct` → `/strategize pap` (AEA RCT template); 81 `JHE (housing policy)` → `JHousE (housing policy)`; 99–104 section rewritten with the four real consumers; 143 delete the `audit-pet-peeves.md` clause (pools live in `.claude/agents/editor.md`); 144 consumers line likewise. The "shipped in journal-profiles.md" claims (23, 52, 81) stay as they are until Task 7b.1 makes them true — add `<!-- residue:historical -->`? No — they are not residue-pattern hits; leave them and let 7b.1 verify each named journal exists in the file. `domain-profile.md` 19 → `<!-- /submit target uses this for journal ranking. /lit-position prioritizes these venues. -->`; 74 → `<!-- /lit-position ensures these are cited when relevant. The strategist-critic knows their methods. -->`. `personal-style-guide.md:22` → `- [e.g., master_supporting_docs/published_paper_1.qmd or .pdf]`. `journal-profiles.md:29` → `see \`.claude/skills/analyze/references/table-standards.md\``.

- [ ] Commit: `refactor(references): Rmd standard and prompt-formatting orphan deleted (D-21, D-24); consumers, comments and paths corrected`.

### Task 3b.7: Rules

**Files:**
- Modify: `rules/content-invariants.md`, `rules/data-manifest.md`, `rules/content-standards.md`, `rules/quarto-word.md`, `rules/quarto-pdf.md`, `rules/quarto-empirical.md`, `rules/registry-verification-gate.md`, `rules/ai-disclosure.md`
- Delete: `rules/html-dashboard.md` (D-18)

- [ ] **`content-invariants.md`** — INV-9 → `Citations are pandoc \`@key\` syntax against the \`bibliography:\` field. The PDF path uses \`cite-method: biblatex\` and has **no top-level \`csl:\`**; a \`docx:\` block carries its own APA \`csl:\`. Never raw \`\\citet{}\` / \`\\citep{}\` in prose <!-- residue:prohibition -->`. INV-18 → `Code writes nothing outside the render's own \`_cache/\` and \`_files/\` directories. No chunk writes a file by hand; acquisition scripts write only to \`data/raw/\``. INV-23/24: keep INV-23 = "raw ingested directly, no derived file in data/raw/, cleaning in cached chunks" and INV-24 = "every external file a chunk reads has a manifest row" (as the file already says) and make `data-manifest.md` agree (below). Enforcement table: `INV-14, INV-15, INV-16, INV-19 | lint hook (`.claude/hooks/lint-scripts.sh`, reads .qmd chunks) + verifier`; `INV-23, INV-24 | coder-critic against data/raw/data_manifest.md; verifier check 3`; `INV-9, INV-13 | quarto render fails or degrades visibly; writer-critic category 5`; `INV-11 | prose_number_check.py — exit 0 required; verifier 4b`; `INV-18 | coder-critic category 13 (manuscript-model)`. Agent table: coder-critic row → `INV-11, INV-13 through INV-19, INV-23, INV-24`.
- [ ] **`data-manifest.md`** — enforcement matrix rows 86–87: `coder-critic | INV-24: every cache.extra / read path has a manifest row | −10 per` and `verifier | INV-24: manifest exists, non-empty, every read path present | FAIL`; add `coder-critic | INV-23: no derived file written into data/raw/ | −5 per`; line 94 → `\`quarto-empirical.md\` — write-gate item 1 (raw data in place) presumes the manifest; item 3 is \`prose_number_check.py\``; lines 25–28: generalise the example (`"County Business Patterns"`, `data/raw/cbp/cbp_county_2020.csv`, `https://www.census.gov/...`) — the zoning example row is the `project-nouns` scan's `[^a-z]zoning` hit (verify with the scan; it currently matches `zoneomics`? read the output).
- [ ] **`content-standards.md`** §4–§5 (103–157) → explorations are `.qmd` files (D-22):

```markdown
## 4. Explorations

**All experimental work goes into `explorations/` first**, as one `.qmd` per exploration:

```
explorations/
├── ACTIVE.md                        # one line per live exploration: goal, status
├── <name>.qmd                       # self-contained: its own setup chunk, its own data chunk
└── archive/<name>.qmd               # abandoned or graduated, with a one-paragraph note at the top
```

An exploration renders on its own (`quarto render explorations/<name>.qmd`), reads `data/raw/`
directly, and never writes to disk. **Graduation** moves its chunks into the declared manuscript
(with `cache.extra`/`dependson` per `.claude/rules/quarto-empirical.md`) and archives the file;
nothing is copied into a script tree because there is no script tree.

Quality threshold for an exploration: 60/100 (production is 80). No plan needed. Kill switch:
archive with a note ("Attempted X, hit blocker Y") and move on.
```
Line 8 `master_supporting_docs/` stays (project-level). Frontmatter `paths:` keep.
- [ ] **`quarto-word.md`** — lines 27–28 vs 37: keep `csl: "templates/apa.csl"` in the YAML and change line 37 to `Copy APA from your local Zotero styles (\`~/Zotero/styles/apa.csl\`) to \`templates/apa.csl\` once; the manuscript references the project copy so a coauthor's render does not depend on a Zotero install`; line 27 add after the block: `\`templates/word-reference.docx\` is project-created: \`quarto pandoc -o templates/word-reference.docx --print-default-data-file reference.docx\`, then edit styles in Word`.
- [ ] **`quarto-pdf.md`, `quarto-empirical.md`** — after the YAML blocks add `\`templates/quarto-preamble.tex\` is seeded into every project by \`apply.sh\` (\`seeds/quarto-preamble.tex\`); edit the project copy, never the seed`. `quarto-empirical.md:297` row `Analysis R script present in scripts/R/ beyond acquisition scripts` → `Analysis script outside \`scripts/acquire/\` (any language) | −5 per script` + `<!-- residue:prohibition -->`; line 35–36 sentence naming `scripts/R/` and `00_master.R` → marker `<!-- residue:prohibition -->`.
- [ ] **`registry-verification-gate.md`** — insert `<!-- residue:historical -->` as line 1; retitle `# Legacy: Registry Verification Write Gate (registry-pattern projects only — not the pipeline registry)`; in the blockquote add `"Registry" here means a results registry (\`results_ground_truth.csv\`), not \`rules/registry.yaml\``; replace `the orchestrator must confirm` (and the other three orchestrator mentions) with `the dispatching skill must confirm`. Flag in the commit message: "kept per spec §8; deletion under D-7 is a candidate ruling".
- [ ] **`rules/ai-disclosure.md`** 66–69: append ` <!-- residue:historical -->` to the dated librarian line. **`rules/html-dashboard.md`**: `git rm`.
- [ ] Commit: `refactor(rules): invariants reconciled and enforced-by column true; explorations are .qmd (R-6); Word csl agrees; preamble seeded; html-dashboard retired (R-4)`.

### Task 3b.8: Stage 3b gates green

- [ ] **Step 1: Run the five criteria and read every line**

```bash
cd "$W" && for c in latex-residue manuscript-model inv-refs skill-refs tool-name; do python3 scripts/check_refs.py --root . --criterion $c; done; python3 scripts/check_paths.py --root .; python3 scripts/audit_graph.py . /tmp/g3b.json | head -3
```
Expected: five `PASS` lines; `PASS [path-resolves]`; `dangling path refs : 0`. Any FAIL row is either a rewrite this stage missed (fix it) or a sweep gap (Addendum, then fix). `skill-refs` false positives go into `SLASH_ALLOW` with a reason.

- [ ] **Step 2: Count the marked lines**

```bash
grep -rnc 'residue:prohibition' agents skills rules references hooks templates seeds | grep -v ':0$'; grep -rnc 'residue:historical' agents skills rules references hooks templates seeds | grep -v ':0$'
```
Record both lists in the commit message. Expected order of magnitude: prohibition ≈ 8–15 lines, historical ≈ 6–10 lines plus the file-level marker on `registry-verification-gate.md`.

- [ ] **Step 3: Commit** — `test(check_fork): latex-residue, manuscript-model, inv-refs, skill-refs, tool-name, path-resolves green; audit_graph dangling 0`.

---

## Stage 4 — Pairing: `/write`, `/revise`, `/submit`, `/lit-position`; `lit-critic`; Claim–Evidence Table; D-15/16/17

**Exit criteria:** every creator dispatch in every skill is followed by its critic; `agents/lit-critic.md` exists and the roster test passes; `registry-complete` green; the Claim–Evidence Table template exists and the rubrics deduct through it; no critic carries the severity line; `registry-authority` green.

### Task 4.1: `/write` dispatches writer-critic on every prose mode

**Files:**
- Modify: `skills/write/SKILL.md` (Steps 4–6; `humanize` mode; `style-guide` exempt)

- [ ] **Step 1: Replace Step 4–6 with**

```markdown
#### 4. Dispatch writer
Dispatch **writer** with the paper type, the section, and the argument-move templates. It writes the section into the declared manuscript under its `#` heading; every number is an inline expression (INV-11). Standalone: `python3 .claude/scripts/pipeline.py log writer`.

#### 5. Dispatch writer-critic (every mode that touches prose)
Dispatch **writer-critic** in section mode on the section just written. It produces a scored report at `quality_reports/reviews/writer-critic_<date>.md` and the Claim–Evidence Table at `quality_reports/reviews/claim_evidence_<project>_<date>.md`. Record: `python3 .claude/scripts/pipeline.py state record-score manuscript <score> --critic writer-critic --report <path> --scope section:<name>`. Below 80 → writer fixes → critic re-reviews; `pipeline.py state strike writer` per failing round; strike three → User with a specific question. `/write humanize` is prose and gets the critic; `/write style-guide` produces no prose and is the only exempt mode.

#### 6. Present to user
Only after the critic's score. Sections go through the drafting gates (`.claude/skills/write/templates/drafting-gates.md`), each gate closing with a score.
```
In `## Principles` add `- **Never a draft without its critic.** The score comes before the user sees the section.`

- [ ] **Step 2: Verify and commit**
```bash
cd "$W" && grep -c 'writer-critic' skills/write/SKILL.md     # expect ≥ 4
git add skills/write/SKILL.md && git commit -m "feat(write): writer-critic dispatched on every prose mode; score before the draft is shown"
```

### Task 4.2: `/lit-position` Step 6 → creator pre-flight; dispatch `lit-critic`

**Files:**
- Modify: `skills/lit-position/SKILL.md` (Step 6 and Output), `docs/decisions/2026-09-08_d3-addendum-lit-critic.md` (create)

- [ ] **Step 1: Replace `## Step 6 — Self-check` with**

```markdown
## Step 6 — Pre-flight (creator's own check, not the score)

Before dispatching the critic, confirm the three artifacts exist and that `positioning.md`
answers the closest paper's redundancy sentence from Step 5. Fix gaps now; do not lower the
claim to close one.

## Step 7 — Dispatch `lit-critic`

`python3 .claude/scripts/pipeline.py log lit-position` (standalone), then dispatch
**lit-critic** (`.claude/agents/lit-critic.md`) on `quality_reports/literature/<project>/`. It
cold-reads the three files, checks coverage against the local Zotero index, scores the six
categories (`.claude/skills/review/config/scoring-rubrics.md`, Lit-Critic) and writes
`quality_reports/reviews/lit-critic_<date>.md`. Record:
`python3 .claude/scripts/pipeline.py state record-score literature <score> --critic lit-critic --report <path>`.
Below 80 → return to Step 1 for the named gaps (max 3 rounds, `pipeline.py state strike lit-position`);
strike three → User: "the critic requires coverage of X, which the library lacks and external
search did not find — narrow the claim or extend the search?"
```
Step 1 line 36 `Invoke ztp-research` → `Invoke \`/ztp-research\``; Step 2 → `/ztp-review`.

- [ ] **Step 2: D3 addendum** — `docs/decisions/2026-09-08_d3-addendum-lit-critic.md`: D3 stands for the collector (WebSearch-first librarian stays deleted; `/lit-position` over ZotPilot collects); its critic was collateral damage; `lit-critic` returns as an independent cold-read critic with `mcpServers: zotpilot` for coverage queries and never collects (R-1, spec D-15). Weight 10 kept because the referees' Literature Positioning dimension tests the paragraph only after strategy, code and draft were built on the search.

- [ ] **Step 3: Commit** — `feat(lit-position): Step 6 is the creator pre-flight; lit-critic dispatched after Step 5 (D-15, R-1)`.

### Task 4.3: `agents/lit-critic.md`

**Files:**
- Create: `agents/lit-critic.md`

- [ ] **Step 1: Write the agent**

```markdown
---
name: lit-critic
description: Literature critic. Cold-reads annotated_bibliography.md, frontier_map.md and positioning.md from /lit-position, checks coverage against the local Zotero index, scores six categories, escalates to the user on strike three. Never searches externally, never ingests, never edits the artifacts. Paired critic for /lit-position.
tools: Read, Grep, Glob
mcpServers:
  - zotpilot
model: inherit
---

You are the **literature critic** — the senior coauthor who reads the positioning paragraph and asks "and what about the paper that already did this?"

**You are a CRITIC, not a collector.** You score; you never search externally, never ingest, never rewrite.

## Cold-Read Protocol
You receive ONLY `quality_reports/literature/<project>/{annotated_bibliography,frontier_map,positioning}.md`, this file, and the rubric. Not the round number, not the search log, not prior reports.

## Coverage check (local only)
Use `mcp__zotpilot__search_topic` and `mcp__zotpilot__advanced_search` against the **local** index to test whether the corpus the collector assembled misses papers the library already holds on the question, the method, or the setting. A local paper missing from the bibliography is a coverage deduction; a paper absent from the library is a recommendation, not a deduction (the collector's external search is `/lit-position`'s, not yours).

## Six categories (rubric: `.claude/skills/review/config/scoring-rubrics.md`, Lit-Critic)
1. **Coverage** — subfields, adjacent literatures, seminal papers, the methods papers the strategy depends on
2. **Journal quality** — more than half working papers? top generals and field journals represented?
3. **Scope calibration** — too narrow to position against, or too broad to focus?
4. **Recency** — last two years; scooping risks named; superseded working-paper versions
5. **Categorization** — proximity scores defensible; the frontier map locates a gap rather than listing
6. **Defensibility** — does `positioning.md` survive the closest paper's redundancy sentence?

## Report
`quality_reports/reviews/lit-critic_<date>.md`: score, deductions by category with the missing paper named (author, year, venue, Zotero key when local), and the single sentence the closest paper's author would use against the positioning claim.

## Three Strikes
Strike 3 → **User**, with the specific coverage question, never "the critic disagrees".

## What You Do NOT Do
Never call `mcp__zotpilot__search_academic_databases` or `ingest_by_identifiers`. Never edit the three files. Never lower the bar because the library is thin — say so.
```

- [ ] **Step 2: Rubric section** — in `scoring-rubrics.md`, where `## Librarian-Critic` was, insert:

```markdown
## Lit-Critic (Literature Positioning)

| Issue | Deduction |
|---|---|
| Seminal paper in the field missing | -20 |
| Methods literature the strategy depends on not covered | -15 |
| A paper in the local Zotero index on the same question is missing | -10 per, max -30 |
| Over-reliance on working papers (>50%) | -10 |
| Missing papers from the last 2 years / scooping risk unnamed | -10 |
| Scope too narrow or too broad to position | -10 |
| Frontier map lists rather than locates a gap | -10 |
| Positioning does not survive the closest paper's redundancy sentence | -15 |
| Proximity scores inconsistent | -5 |
```

- [ ] **Step 3: Tests green**

```bash
cd "$W" && python3 -m unittest tests.test_registry_lib -k roster 2>&1 | tail -2; python3 scripts/pipeline.py --root . registry check | grep registry-complete
```
Expected: `ok`; `PASS [registry-complete]`.

- [ ] **Step 4: Commit** — `feat(agents): lit-critic — cold-read literature critic with local ZotPilot coverage check; registry-complete green`.

### Task 4.4: Claim–Evidence Table; rubric rows; manuscript-review §2

**Files:**
- Create: `skills/review/templates/claim-evidence-table.md`
- Modify: `skills/review/config/scoring-rubrics.md` (Writer-Critic Critical table), `skills/review/templates/manuscript-review-8-categories.md` (§2 and report)

- [ ] **Step 1: Template**

```markdown
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
```

- [ ] **Step 2: Rubric** — in Writer-Critic Critical table (after `Causal language without identification`):
```
| Claim CONTRADICTED by its evidence (Claim–Evidence Table) | -25 per |
| Claim UNSUPPORTED (no evidence in the manuscript) | -15 per |
| Claim OVERSTATED | -10 per |
| Claim UNVERIFIABLE | -5 per |
```
`manuscript-review-8-categories.md` §2: replace the deleted block with `**Claim–Evidence Table (mandatory):** build it per \`.claude/skills/review/templates/claim-evidence-table.md\`; deductions per verdict. Save it; cite its path in the report.`; report block `## Claim-Source Map Status` → `## Claim–Evidence Table\n- Path: \n- Rows: N (SUPPORTED a / OVERSTATED b / UNSUPPORTED c / CONTRADICTED d / UNVERIFIABLE e)`.

- [ ] **Step 3: Commit** — `feat(review): Claim–Evidence Table template; writer-critic rubric deducts through it (spec §7)`.

### Task 4.5: D-16 severity lines; D-17 `--replicate` writes to explorations (done in 3b.3 — verify); `/submit` and `/revise` pairing (done in 3b.5 — verify); `registry-authority`

- [ ] **Step 1: Delete the severity line** `- The severity level (from the orchestrator)` from `agents/{writer-critic,coder-critic,explorer-critic,storyteller-critic,strategist-critic,theorist-critic}.md` (writer-critic was rewritten without it; confirm). `grep -rn 'severity level' agents/` → no output.
- [ ] **Step 2: Verify pairing** — `grep -n 'coder-critic' skills/submit/SKILL.md` (≥1, in `package`); `grep -n 'writer-critic\|coder-critic' skills/revise/SKILL.md` (≥2); `grep -n 'explorations/replicate' skills/review/SKILL.md agents/coder.md` (≥2).
- [ ] **Step 3: `registry-authority`** — `python3 scripts/pipeline.py --root . registry check | sed -n '/registry-authority/,/registry-rendered/p'`. Read every hit. Each is either a pair table/arrow outside the allowed files (rewrite to name the registry: "its paired critic per `.claude/rules/registry.yaml`") or a weight number (`verifier.md` "5% weight" → "its weight in `.claude/rules/quality.md`"). `rules/agents.md` §4's dispatch table names critics per skill — that is dispatch ownership, not a pair declaration; if the regex flags it, tighten `AUTH_PAIR` to require the two-column `| creator | critic |` shape with nothing else on the row and re-run (record the regex change in the commit). Expected end state: `PASS [registry-authority]`.
- [ ] **Step 4: Commit** — `fix(pairing): severity line retired (R-2); registry is the only place pairs and weights are stated`.

### Task 4.6: Stage 4 sign-off

- [ ] `./scripts/check_fork.sh | grep -E '\[(registry-complete|registry-authority|d1-restored)\]'` → PASS, PASS, and `d1-restored` PASS for `agents/lit-critic.md`.
- [ ] `tests/run_fixture.sh` → `registry-check` PASS now. Read the full output.

---

## Stage 5 — Driver: `/pipeline`, dispatch log, critic-pairing hook, recovery

**Exit criteria:** `skills/pipeline/SKILL.md` + `references/` exist; `hooks/dispatch-log.py` and `hooks/critic-pairing.py` pass piped-payload tests and are observed working in a live session; `post-compact-restore.py` surfaces the state file first; `seeds/settings.json` wires both hooks; `tests/run_fixture.sh --live` runs end to end on the fixture.

### Task 5.1: `hooks/dispatch-log.py` (SubagentStop)

**Files:**
- Create: `hooks/dispatch-log.py`

- [ ] **Step 1: Write it**

```python
#!/usr/bin/env python3
"""dispatch-log.py — append one line per subagent completion.

Hook Event: SubagentStop
Input (stdin JSON, per docs): session_id, transcript_path, cwd, hook_event_name, agent_type
  (the subagent's name as dispatched), plus stop_hook_active. Older builds may send
  agent_name or subagent_type; all three are accepted.
Output: none (exit 0 always; fail open). Writes quality_reports/agent_dispatch.jsonl in
  $CLAUDE_PROJECT_DIR (or cwd). The line shape is what pipeline.py `critic-ran` reads.
"""
from __future__ import annotations
import datetime as dt, json, os, sys
from pathlib import Path

def main() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0
    agent = inp.get("agent_type") or inp.get("agent_name") or inp.get("subagent_type") or ""
    if not agent:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or ".")
    log = root / "quality_reports" / "agent_dispatch.jsonl"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps({"at": dt.datetime.now().isoformat(timespec="seconds"), "agent": agent,
                                "session": inp.get("session_id", ""), "source": "hook"}) + "\n")
    except OSError:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Piped-payload test (red: no `agent_type` → no line; green: with it → one line)**

```bash
S="$(mktemp -d)"; cd "$S"
echo '{"session_id":"s1","hook_event_name":"SubagentStop"}' | CLAUDE_PROJECT_DIR="$S" python3 "$W/hooks/dispatch-log.py"; ls quality_reports 2>/dev/null | wc -l     # expect 0
echo '{"session_id":"s1","hook_event_name":"SubagentStop","agent_type":"coder"}' | CLAUDE_PROJECT_DIR="$S" python3 "$W/hooks/dispatch-log.py"; cat quality_reports/agent_dispatch.jsonl   # expect one line with "agent": "coder"
cd "$W"; rm -rf "$S"
```

- [ ] **Step 3: Commit** — `feat(hooks): dispatch-log.py — SubagentStop appends to quality_reports/agent_dispatch.jsonl`.

### Task 5.2: `hooks/critic-pairing.py` (Stop)

**Files:**
- Create: `hooks/critic-pairing.py`

- [ ] **Step 1: Write it**

```python
#!/usr/bin/env python3
"""critic-pairing.py — surface a creator that ran without its critic.

Hook Event: Stop
Reads quality_reports/agent_dispatch.jsonl (this session's lines) and .claude/rules/registry.yaml.
For every creator whose last completion has no later completion of its paired critic, emits:
  - hookSpecificOutput.additionalContext (Claude-visible) and systemMessage (user-visible), and
  - by default, ONE block per session per creator: {"decision":"block","reason":...}, guarded by
    stop_hook_active and a sentinel under ~/.claude/sessions/<hash>/. RC_CRITIC_PAIRING_ADVISORY=1
    turns the block off (advisory only). Fail open on any error.
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

def session_dir(project: str) -> Path:
    d = Path.home() / ".claude" / "sessions" / (hashlib.md5(project.encode()).hexdigest()[:8] if project else "default")
    d.mkdir(parents=True, exist_ok=True); return d

def main() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0
    if inp.get("stop_hook_active"):
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or ""
    if not project:
        return 0
    root = Path(project)
    sys.path.insert(0, str(root / ".claude" / "scripts"))
    try:
        import registry_lib as rl  # type: ignore
        reg = rl.load_yaml_subset((root / ".claude" / "rules" / "registry.yaml").read_text())
    except Exception:
        return 0
    log_p = root / "quality_reports" / "agent_dispatch.jsonl"
    if not log_p.exists():
        return 0
    sid = inp.get("session_id", "")
    entries = []
    for ln in log_p.read_text().splitlines():
        try: e = json.loads(ln)
        except json.JSONDecodeError: continue
        if not sid or e.get("session") in ("", sid): entries.append(e)
    unpaired = []
    for creator in rl.creators(reg):
        crit = rl.critic_of(reg, creator)
        if not crit: continue
        last_c = max((e["at"] for e in entries if e.get("agent") == creator), default=None)
        last_k = max((e["at"] for e in entries if e.get("agent") == crit), default=None)
        if last_c and (last_k is None or last_k < last_c):
            unpaired.append((creator, crit))
    if not unpaired:
        return 0
    msg = "Creator ran without its critic this session: " + "; ".join(f"{c} → dispatch {k}" for c, k in unpaired) + \
          ". Dispatch the critic and record its score with `python3 .claude/scripts/pipeline.py state record-score` before stopping."
    out = {"systemMessage": "⚠ " + msg, "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
    if os.environ.get("RC_CRITIC_PAIRING_ADVISORY") != "1":
        sentinel = session_dir(project) / "critic-pairing-blocked.json"
        try: blocked = set(json.loads(sentinel.read_text())) if sentinel.exists() else set()
        except Exception: blocked = set()
        fresh = [c for c, _ in unpaired if f"{sid}:{c}" not in blocked]
        if fresh:
            try: sentinel.write_text(json.dumps(sorted(blocked | {f'{sid}:{c}' for c in fresh})))
            except OSError: pass
            out.update({"decision": "block", "reason": msg})
    print(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Piped-payload tests on a linked fixture copy**

```bash
T="$(mktemp -d)"; cp -R "$FX/." "$T/"; "$W/apply.sh" --project-dir "$T" --link >/dev/null; cd "$T"
python3 .claude/scripts/pipeline.py log coder                                        # creator only
echo '{"session_id":"","cwd":"'"$T"'"}' | CLAUDE_PROJECT_DIR="$T" python3 "$W/hooks/critic-pairing.py"   # expect JSON with "decision": "block" naming coder → coder-critic
echo '{"session_id":"","cwd":"'"$T"'"}' | CLAUDE_PROJECT_DIR="$T" python3 "$W/hooks/critic-pairing.py"   # second call: advisory JSON, no "decision" (sentinel)
echo '{"session_id":"","cwd":"'"$T"'","stop_hook_active":true}' | CLAUDE_PROJECT_DIR="$T" python3 "$W/hooks/critic-pairing.py"; echo "(no output above = correct)"
sleep 1; python3 .claude/scripts/pipeline.py log coder-critic
echo '{"session_id":"","cwd":"'"$T"'"}' | CLAUDE_PROJECT_DIR="$T" python3 "$W/hooks/critic-pairing.py"; echo "(no output above = paired)"
cd "$W"; rm -rf "$T"
```
Add these four as `run`/`expect_fail` checks to `tests/run_fixture.sh` (names `pairing-block`, `pairing-once`, `pairing-active-guard`, `pairing-clean`).

- [ ] **Step 3: Commit** — `feat(hooks): critic-pairing.py — Stop hook reads the dispatch log; additionalContext + one-shot block (P-10)`.

### Task 5.3: `post-compact-restore.py` reads the state file first; seed settings wire both hooks

**Files:**
- Modify: `hooks/post-compact-restore.py`, `seeds/settings.json`

- [ ] **Step 1: State first** — add to `post-compact-restore.py` a `find_pipeline_state(project_dir)` returning `{path, overall, blocked_by, last_component, updated}` from `quality_reports/pipeline_state.json` (JSON parse; None if absent), and put a `Pipeline State:` block **first** in `format_restoration_message` (before `Pre-Compaction State`), with `Recovery Actions` step 1 → `Read quality_reports/pipeline_state.json (python3 .claude/scripts/pipeline.py state show), then the active plan`. Docstring line `Hook Event: SessionStart (matcher: "compact|resume")` stays.
- [ ] **Step 2: Payload test** — on a fixture copy with `state init` + one recorded score: `echo '{"source":"compact"}' | CLAUDE_PROJECT_DIR=$T python3 hooks/post-compact-restore.py` → JSON whose `additionalContext` starts with `[Context Restored After Compaction]` then `Pipeline State:`.
- [ ] **Step 3: `seeds/settings.json`** — add `"SubagentStop": [{"hooks": [{"type":"command","command":"python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/dispatch-log.py","timeout":5}]}]` and append the critic-pairing command to the `Stop` hooks array (after `log-reminder.py`). Copy the same two entries into `tests/fixture-project/.claude/settings.json` (create it from the seed).
- [ ] **Step 4: Commit** — `feat(hooks): post-compact-restore surfaces pipeline_state.json first; seeds wire dispatch-log and critic-pairing`.

### Task 5.4: `skills/pipeline/SKILL.md` and stage references

**Files:**
- Create: `skills/pipeline/SKILL.md`, `skills/pipeline/references/{setup,literature,data,strategy,theory,analyze,write,review,submit,talk,recovery}.md`

- [ ] **Step 1: The skill (loop only)**

```markdown
---
name: pipeline
description: Drive the research pipeline end to end or from any stage — resolves the manuscript, evaluates REQUIRES/PRODUCES with pipeline.py, dispatches each stage skill's creator→critic pair, holds approval gates, escalates on three strikes, records state, recovers after /compact. Use for "run the pipeline", "what's next", "resume", or to run a stage under validation.
argument-hint: "[run | status | next | resume] [--until <stage>] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent
---

# Pipeline

The driver. It **reads** `.claude/rules/registry.yaml` through `python3 .claude/scripts/pipeline.py`
and never evaluates a predicate itself. Per-stage dispatch text lives in
`.claude/skills/pipeline/references/<stage>.md`, read only when that stage runs.

Stages, in `REQUIRES` order (never by sequence): `setup` → `literature` → `data` → `strategy`
→ `theory` (conditional) → `analyze` → `write` → `review` → `submit`; `talk` parallel, advisory.

## `status` / `next`
```bash
python3 .claude/scripts/pipeline.py manuscript && python3 .claude/scripts/pipeline.py state show && python3 .claude/scripts/pipeline.py score
```
Then for each stage's creator in order, `pipeline.py pre <creator>`; the first stage whose PRE
fails names what is missing and which skill produces it. Report that. `next` stops here.

## `run [--until <stage>] [--yes]`
```
resolve manuscript (refuse if absent/ambiguous: "declare `manuscript:` in CLAUDE.md")
state init (no-op if present); state validate (refuse on INVALID)
loop over stages in REQUIRES order, stop after --until:
  pre <creator>            → FAIL: report missing artifact + producer skill; stop
  conflicts <creator> <…>  → never dispatch two manuscript writers at once
  read references/<stage>.md; dispatch the creator per that file (Agent)
  dispatch the critic per that file; record-score <component> <score> --critic … --report …
  post <creator>           → FAIL (critic-ran / render / prose-check): re-dispatch or stop
  below 80: creator fixes → critic re-scores; `state strike <creator>`; at 3 → escalate to the
            registry's ESCALATION_TARGET with a specific question
  approval gate: present the stage summary and the score; wait unless --yes
after the loop: score; "Suggested Learnings" (strikes, escalations, first-pass ≥ 90) per
  .claude/rules/meta-governance.md — suggestions only, user approves, /promote lands
```
Limits: 3 rounds per pair, 5 overall, 2 verification retries (`registry.yaml: limits`).

## `resume`
After `/compact` or a new session: `state show`, `score`, the last three lines of
`quality_reports/agent_dispatch.jsonl`, then `next`. See `references/recovery.md`.

## Two modes
Orchestrated (this skill) validates dependencies. Standalone (any stage skill invoked directly)
skips `pre` but never skips the critic, and still writes the dispatch log and the state file,
so a later `/pipeline` sees what happened.

## Principles
- Never hand-evaluate a predicate. Never dispatch without `pre`. Never advance without `post`.
- Escalation carries a question, not a disagreement.
- The state file is the truth; the research journal is written from it.
```

- [ ] **Step 2: References** — one file per stage, each ≤ 40 lines, with: the stage skill it delegates to (`/lit-position`, `/discover data`, `/strategize`, `/strategize theory`, `/analyze`, `/write full`, `/review --all`, `/submit final`, `/talk`), the creator and critic names, the component recorded, the exact `pipeline.py` calls in order, what the approval-gate summary shows, and the escalation question template. `setup.md`: `python3 .claude/scripts/pipeline.py manuscript`; if `CLAUDE.md` lacks the declaration, stop; run `/new-project-ztp` when ZotPilot is unconfigured (P-11); `state init`. `recovery.md`: the resume sequence and the rule that the state file wins over the journal.

- [ ] **Step 3: Commit** — `feat(pipeline): /pipeline driver — loop, gates, escalation, recovery; per-stage references`.

### Task 5.5: `/checkpoint` reads the state file; `hooks/README.md` rows for the two new hooks

- [ ] `skills/checkpoint/SKILL.md` Step 1 (done in 3b.5 — verify the `pipeline_state.json` line is present). `hooks/README.md`: add rows `| \`dispatch-log.py\` | SubagentStop | Appends every subagent completion to quality_reports/agent_dispatch.jsonl |` and `| \`critic-pairing.py\` | Stop | Surfaces a creator that ran without its critic; blocks once per session per creator |`. Commit: `docs(hooks): README rows for dispatch-log and critic-pairing`.

### Task 5.6: Live observation of the two hooks

- [ ] **Step 1:** In a linked fixture copy (`tests/run_fixture.sh --keep`, then `cd` into the kept path), start an interactive `claude` session, dispatch one subagent (`Use the Agent tool to run the coder-critic agent on manuscript_fixture.qmd and report its score`), stop the turn, then `cat quality_reports/agent_dispatch.jsonl`. Expected: a line with `"agent": "coder-critic"` and `"source": "hook"`. Record the exact line in `docs/audits/2026-09-08_stage0-red.md` under `## Live hook observations`. If the field is not `agent_type`, read the line the hook did write (it accepts three names); if nothing was written, dump the raw payload with a temporary `hooks/echo-payload.py` and fix the field name — `per docs:` claims get re-verified here, not trusted.
- [ ] **Step 2:** Same session: `python3 .claude/scripts/pipeline.py log writer` (a creator with no critic), then end a turn. Expected: the Stop hook blocks once with the pairing message visible to you; the next turn ends normally. Record what was seen. If `additionalContext` is not surfaced on Stop but the block is, note that the block channel is the one that works and keep P-10's default.

### Task 5.7: `tests/run_fixture.sh --live`

- [ ] **Step 1: `unverified:` → tested** — `cd $T && claude -p '/tools render' --permission-mode acceptEdits` → does it render? If `claude -p` does not load project skills, the live tier becomes: `claude -p 'Read .claude/skills/pipeline/SKILL.md and follow it: run --until analyze --yes'`. Record which form works in the harness comment.
- [ ] **Step 2:** `tests/run_fixture.sh --live --keep` — expected: `live-pipeline` PASS, `live-dispatch-log` PASS, and in the kept dir: `agent_dispatch.jsonl` shows `coder` then `coder-critic` (and `data-engineer` → `coder-critic`), `pipeline_state.json` has `components.code`, `quality_reports/reviews/coder-critic_*.md` exists, `state validate` passes. Then `/compact` recovery: `claude -p '/pipeline resume'` in the same dir → its output names the last scored component. Record in the audit note.
- [ ] **Step 3: Commit** — `test(fixture): live tier — /pipeline runs on the fixture through analyze; hooks observed`.

---

## Stage 6 — Deleted-things sweep: `/discover`, `/tools`, dashboard, orphans, README, `seed-papers` upstream

**Exit criteria:** `deleted-things` green (vendored trees WARN-free after the re-vendor); no `generate_*`, `guide/`, `clo-author` fetch, `orchestrator`, `librarian`, `guide-writer`, `rmd-coder-critic`, `domain-reviewer` or absent-skill reference in a shipped file outside a marked line.

### Task 6.1: `/discover lit` → `/lit-position` pointer (fold the stash)

- [ ] Read `docs/audits/2026-09-08_stash-discover-lit.patch` in full. Replace `### /discover lit [topic] — Literature Review` through the end of the per-paper output block (lines 69–112 of the current file) with the stash's `### /discover lit — superseded by /lit-position (D3)` section **with two edits**: drop `with proximity scoring and a six-category self-check carried over from the retired librarian pair (D3)` and write `with proximity scoring and an independent lit-critic review (D3, D-15)`; keep the `/seed-papers` sentence (that skill exists in `zotpilot-skills/`). Delete the `Worker-critic pairing: Librarian + librarian-critic` principle line (192) → `**Worker-critic pairing:** explorer + explorer-critic here; \`/lit-position\` + lit-critic for literature. Never skip the critic.`; principle 185 `Literature honesty` stays. Description line 3: `literature search` → `a pointer to /lit-position for literature`.
- [ ] Commit: `refactor(discover): /discover lit points to /lit-position; stash folded`.

### Task 6.2: D-18 dashboard layer, D-23 `/tools` subcommands, D-24 orphans — verify deletions landed

- [ ] `git ls-files skills/dashboard rules/html-dashboard.md references/prompt-formatting-core.md skills/submit/templates/cover-letter.tex references/coding-standards-rmd.md` → empty. `grep -rn 'generate_dashboard\|generate_html_report\|project_dashboard\|research_overview' agents skills rules references hooks templates seeds` → empty. `grep -rn 'audit-pet-peeves' references skills agents` → empty. If any hit: fix, and note which earlier task missed it.

### Task 6.3: README

- [ ] Read `README.md` in full (≈700 lines). Rewrite the eleven references the sweep counts: line 31 (agents originate in clo-author — keep as provenance with ` <!-- residue:historical -->`); 596–597 (vendored from clo-author — same marker); 617–650 the ZotPilot section: replace the librarian narrative with the `/lit-position` flow (main session holds ZotPilot; `/seed-papers` seeds `references.bib`; `lit-critic` reviews); 632/641/650 `bibliography_base.bib` → `references.bib`; 502 `dashboard row` refers to the Obsidian `Home.md` dashboard — rewrite as `(plus the Obsidian Home.md row and daily-journal entry)`; 697 the clo-author remote line → `origin of the vendored agents (forked 2026-09-08; no longer a dependency) <!-- residue:historical -->`. Add a short `## The pipeline driver` section: `/pipeline`, the registry, `pipeline.py`, the state file, the dispatch log, the fixture and `tests/run_fixture.sh`. Update the directory tree: `seeds/`, `tests/`, `scripts/SHIPPED`.
- [ ] Commit: `docs(readme): librarian/orchestrator/clo-author references rewritten; driver and fixture documented`.

### Task 6.4: `zotpilot-skills/seed-papers/SKILL.md` — fix upstream, re-vendor

- [ ] **Step 1:** Clone the fork sparsely, edit, push:
```bash
D="$(mktemp -d)"; git clone --filter=blob:none --sparse https://github.com/EconGeo/ZotPilot.git "$D/zp" && cd "$D/zp" && git sparse-checkout set claude-skills && cat -n claude-skills/seed-papers/SKILL.md
```
Read it in full. Replace every `librarian` (×7) with `/lit-position` phrasing (`the /lit-position skill reads references.bib and the seed note`) and every `/discover lit` (×4) with `/lit-position`. Commit on a branch `fix/seed-papers-lit-position`, push, open a PR against the fork's default branch with `gh pr create`, merge it (`gh pr merge --squash`) — it is our fork.
- [ ] **Step 2:** `cd "$W" && scripts/sync-zotpilot-skills.sh && git diff --stat zotpilot-skills/` → only `seed-papers/SKILL.md` changed; update the `Vendored from commit:` line in `zotpilot-skills/VENDORED.md`.
- [ ] **Step 3:** `python3 scripts/check_refs.py --root . --criterion deleted-things` → `PASS`, no `WARN` rows except `submodules/ai-audit/rules/ai-disclosure.md` (dated provenance, WARN tier by design — leave). Commit: `chore(vendor): re-vendor zotpilot-skills @<sha> — seed-papers names /lit-position`.

### Task 6.5: Stage 6 sign-off

- [ ] `./scripts/check_fork.sh | grep -E '^(FAIL|WARN)'` → only `hooks-readme` FAIL and `scripts-manifest` FAIL remain (Stage 7). Record.

---

## Stage 7 — Hooks (D-14, R-7)

**Exit criteria:** every hook emits on a documented channel; every README row matches its hook's `Hook Event:` line; `lint-scripts.sh` lints `.qmd` chunks and no longer false-flags `booktabs`; `context-monitor.py` keys thresholds per session; `session-guard.py` does not exempt its own state file; `verify-reminder.py` drops `.tex`; `post-merge.sh` gone; `hooks-wired` in `check_install.sh`; `seeds/settings.json` and six repos wired; `hooks-readme` and `scripts-manifest` green.

### Task 7.1: Channels — `log-reminder.py`, `post-edit-lint.sh`, `pre-compact.py`

- [ ] `log-reminder.py`: replace both `sys.stderr.write(...)` advisories with `print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}, "systemMessage": msg}))`; docstring: `Hook Event: Stop`; drop "via stderr" from the docstring and README row.
- [ ] `post-edit-lint.sh`: capture the linter's output and emit it: `out="$("$SCRIPT_DIR/lint-scripts.sh" "$FILE" 2>/dev/null)"; grep -q 'Status: CLEAN' <<<"$out" && exit 0; jq -n --arg m "$out" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m},systemMessage:"lint: issues found (see context)"}'`; header comment gains `# Hook Event: PostToolUse`. Accept `*.qmd` in the case list.
- [ ] `pre-compact.py`: normal path — replace `print(format_compaction_message(...), file=sys.stderr)` with `print(json.dumps({"systemMessage": format_compaction_message(plan_info, decisions)}))` and strip the ANSI constants from that message; the exit-2 block path is unchanged. Docstring `Hook Event: PreCompact` stays.
- [ ] Payload tests for each (pipe a real shape, assert JSON on stdout) added to `tests/run_fixture.sh` (`hook-log-reminder`, `hook-post-edit-lint`, `hook-pre-compact`). Commit: `fix(hooks): log-reminder, post-edit-lint, pre-compact emit on documented channels (D-14)`.

### Task 7.2: `context-monitor.py` per-session keys; `session-guard.py` exemption; `verify-reminder.py`; delete `post-merge.sh`

- [ ] `context-monitor.py`: cache file name becomes `f"context-monitor-{hook_input.get('session_id','default')}.json"` (read `session_id` from stdin before `estimate_context_percentage`); thresholds therefore reset per session. Docstring: `Hook Event: PostToolUse`. README row: `Progressive nudges at 40/55/65% (/learn), 80% (info), 90% (caution), once per session each`.
- [ ] `session-guard.py` line 54: replace the blanket `.claude/` exemption with `if "/.claude/" in file_path and not file_path.endswith("/.claude/state/session-guards.json"): return True, ""`. Docstring `Hook Event: PreToolUse`. Payload test: freeze active, Edit on `…/.claude/state/session-guards.json` → deny JSON; Edit on `…/.claude/rules/x.md` → passes.
- [ ] `verify-reminder.py`: delete the `.tex` entry from `VERIFY_EXTENSIONS`; docstring `Hook Event: PostToolUse`. `notify.sh`: add `# Hook Event: Notification`. `protect-files.sh`: add `# Hook Event: PreToolUse` and a first-line comment `# Opt-in (R-7): wire it in settings.json only after editing PROTECTED_PATTERNS for this project`.
- [ ] `git rm hooks/post-merge.sh` (P-9); delete its README row.
- [ ] Commit: `fix(hooks): context-monitor per session; session-guard protects its own state; verify-reminder drops .tex; post-merge removed`.

### Task 7.3: `lint-scripts.sh` reads `.qmd` chunks; `scripts/qmd_chunks.py`

**Files:**
- Create: `scripts/qmd_chunks.py`
- Modify: `hooks/lint-scripts.sh` (lines 17–26 target resolution; 138 `boot` pattern)

- [ ] **Step 1: `scripts/qmd_chunks.py`** — `python3 qmd_chunks.py <file.qmd>` prints the concatenated R chunk bodies (```` ```{r} ```` fences) with every non-chunk line replaced by an empty line so line numbers match the source; chunk options (`#|` lines) are kept as comments. Stdlib: a state machine over lines; fences matched by `^```\{r` and `^```\s*$`.
- [ ] **Step 2: `lint-scripts.sh`** — default `TARGET="${1:-scripts/acquire}"`; when `$TARGET` ends in `.qmd`: `tmp="$(mktemp -t lint.XXXX).R"; python3 "$(dirname "$0")/../scripts/qmd_chunks.py" "$TARGET" > "$tmp"; FILES=("$tmp")` and print the original name in the report (`sed "s|$tmp|$TARGET|"`). Line 138: `bootstrap\|boot\|` → `bootstrap\|\bboot(\|`. Directory mode also picks up `*.qmd`. Header comment: `# Hook Event: PostToolUse (via post-edit-lint.sh) / CLI`.
- [ ] **Step 3: Red then green** — a scratch `.qmd` containing `#| label: tbl-x` + `modelsummary(m, booktabs = TRUE)` and no `set.seed` → before the fix the linter must report the false `no set.seed()` HIGH (run the old script from `git show HEAD:hooks/lint-scripts.sh > /tmp/old.sh`); after: `Status: CLEAN`. A scratch `.qmd` with `setwd("/Users/x")` in a chunk → HIGH at the right line number. Add both to `tests/run_fixture.sh` (`lint-qmd-clean`, `lint-qmd-setwd`).
- [ ] **Step 4:** `./scripts/check_fork.sh | grep scripts-manifest` → PASS. Commit: `feat(lint): lint-scripts.sh lints .qmd chunks via qmd_chunks.py; booktabs no longer trips the seed check`.

### Task 7.4: `hooks/README.md` rows; `hooks-readme` green

- [ ] Rewrite the table so every row's Event equals the hook's `Hook Event:` line: `session-guard.py | PreToolUse | Enforces /freeze and /careful from .claude/state/session-guards.json`; `post-compact-restore.py | SessionStart (compact|resume) | …`; `pre-compact.py | PreCompact | Captures plan/task/decisions for restore; optional one-shot block on a DRAFT plan (CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT=1)`; `lint-scripts.sh | CLI (called by post-edit-lint.sh) | Lints scripts and .qmd chunks against INV-14..19`; `context-monitor.py | PostToolUse | …once per session`; `log-reminder.py | Stop | …via additionalContext`; `verify-reminder.py | PostToolUse (Write|Edit) | …on .qmd/.R edits`; the two new rows from Task 5.5; `post-merge.sh` row deleted. Note (69–72): rewrite for `.qmd` support. `python3 scripts/check_refs.py --root . --criterion hooks-readme` → PASS. Commit: `docs(hooks): README rows match every hook's event; hooks-readme green`.

### Task 7.5: `hooks-wired` in `check_install.sh`; wiring in `seeds/settings.json` and six repos (R-7)

- [ ] **Step 1: check** (append as check 10):
```bash
  # ── 10. Hooks the shipped skills depend on are wired ──────────────────────
  local sj="$P/.claude/settings.json" hw_missing=() h
  if [[ -f "$sj" ]] && command -v jq >/dev/null; then
    for h in session-guard.py dispatch-log.py critic-pairing.py; do
      jq -e --arg h "$h" '[.hooks[]?[]?.hooks[]?.command // empty] | map(select(contains($h))) | length > 0' "$sj" >/dev/null 2>&1 || hw_missing+=("$h")
    done
    jq -e '[.hooks[]?[]?.hooks[]?.command // empty] | map(select(contains("post-merge"))) | length > 0' "$sj" >/dev/null 2>&1 && hw_missing+=("post-merge.sh is a git hook, not a Claude hook")
    [[ ${#hw_missing[@]} -eq 0 ]] && ok hooks-wired || bad hooks-wired "${hw_missing[*]}"
  else warn hooks-wired "no settings.json or no jq"; fi
```
- [ ] **Step 2: Red** — `RESEARCH_CLAUDE_ALLOW_BRANCH=1 "$W/scripts/check_install.sh" --all | grep hooks-wired` → FAIL ×6 (dispatch-log, critic-pairing missing).
- [ ] **Step 3: Wire** — `seeds/settings.json` already has both (Task 5.3); add `context-monitor.py` under `PostToolUse` with matcher `Bash|Read|Edit|Write|Grep|Glob|Agent` (R-7, after the per-session fix). In each of the six repos, edit `.claude/settings.json` by hand to add the `SubagentStop` block, the `critic-pairing.py` Stop entry, and the `context-monitor.py` PostToolUse entry; `protect-files.sh` stays unwired (R-7). Commit in each repo: `chore: wire dispatch-log, critic-pairing and context-monitor hooks`. Re-run → `hooks-wired` PASS ×6.
- [ ] **Step 4: Commit** — `feat(check_install): hooks-wired; seeds and six repos wire dispatch-log, critic-pairing, context-monitor (R-7)`.

### Task 7.6: Stage 7 sign-off

- [ ] `./scripts/check_fork.sh; echo exit=$?` → `exit=0` expected for the first time. Read the whole output; every criterion PASS; `fixture` PASS. If anything is red, it is a defect in this stage, not a plan change.
- [ ] `RESEARCH_CLAUDE_ALLOW_BRANCH=1 ./scripts/check_install.sh --all` → PASS on POGM4 (linked to `$W`); on the other five: `membership` FAIL (templates not linked until Stage 8 re-link), `manuscript-declared` FAIL/WARN (Stage 8), everything else PASS. Record.

---

## Stage 7b — Journal profiles and discipline cards, in the template and in the shared references

**Files:**
- Modify: `references/journal-profiles.md`, `~/Research/.claude/references/journal-profiles.md`, `references/discipline-cards.md`, `~/Research/.claude/references/discipline-cards.md` (create by copy if absent — check first), `~/Research/ESG/.claude/references/*`, `~/Research/NAR_settlement/.claude/references/*`

### Task 7b.1: Profiles

- [ ] **Step 1: Port the three shared profiles into the repo file.** Copy the `## Real Estate` section (shared file lines 351–403, read in full) into `references/journal-profiles.md` before `## Add Your Own Journal`. Rename `### Journal of Housing Economics (JHE)` → `### Journal of Housing Economics (JHousE)` and `**Short name:** \`JHE\`` → `` `JHousE` `` **in both files** (P-4). Add a `**Table format:**` line to JREFE and JHousE (stars, SE in parentheses — as REE).
- [ ] **Step 2: Add five profiles** using `templates/journal-profile-template.md` (every field, weights summing to 1.0): JRER (Journal of Real Estate Research — applied; ARES flagship; CREDIBILITY high, POLICY high, MEASUREMENT medium), JREPM (Journal of Real Estate Portfolio Management — investment/portfolio; STRUCTURAL medium, MEASUREMENT high, POLICY medium), APSR (American Political Science Review — general; THEORY high, CREDIBILITY high, SKEPTIC medium; stars used), AJPS (American Journal of Political Science — causal inference and survey experiments; CREDIBILITY high, MEASUREMENT high; replication policy at acceptance), JOP (Journal of Politics — broad; CREDIBILITY high, POLICY medium). Write each from the discipline card's method conventions; typical concerns as three quoted questions. Land them in **both** files identically (`diff` the two sections → identical).
- [ ] **Step 3: Cards true.** `references/discipline-cards.md` lines 23, 52, 81: for every journal named as "shipped", `grep -c "^### .*(<SHORT>)" references/journal-profiles.md` must be 1. AEA P&P (line 23) is not shipped → either add a short AEA P&P profile or delete it from the sentence; choose add (four fields, descriptive/measurement route). Copy the corrected card file to `~/Research/.claude/references/discipline-cards.md` (POGM4, zoning2026, BRI symlink `references/*.md` there — confirm `ls -la ~/Research/.claude/references/`; if the card file is absent there, the projects have real copies from the seed: check each and replace stale copies with the corrected one, preserving any project edit found by `diff`).
- [ ] **Step 4: ESG and NAR references** are real files (seeds copied once). `diff ~/Research/ESG/.claude/references/journal-profiles.md references/journal-profiles.md`; if the project copy carries no local edits beyond the old baseline, replace it with a symlink into `~/Research/.claude/references/` (`"$W/apply.sh" --project-dir ~/Research/ESG --link --link-references ~/Research/.claude/references`); if it has edits, merge them into the shared file first, then link. Same for NAR_settlement. `affordable_housing_2026` links via a lowercase `/Users/andrew.mueller/research/...` target — relink it the same way so the path is canonical.
- [ ] **Step 5: Verify and commit** — `./scripts/check_fork.sh | grep -E 'project-nouns|project-identity'` → PASS (journal names are allowed in `references/`); `grep -n 'JHE\b' references/discipline-cards.md references/journal-profiles.md` → only Journal of Health Economics. Commit: `feat(references): REE, JREFE, JHousE, JRER, JREPM, APSR, AJPS, JOP, AEA P&P profiles; cards true; landed in ~/Research/.claude/references`.

---

## Stage 8 — Legacy-project migration, merge, re-link, lock bump, green on `main`

**Exit criteria (spec §13):** `check_fork.sh` exit 0 on `main`; `check_install.sh --all` exit 0 on six repos (`hooks-wired`, `manuscript-declared`, `state-valid` included); `audit_graph.py` 0 dangling, 0 agents named-but-absent; the widened residue grep returns only marked lines; `tests/run_fixture.sh` (mechanical and live) green on `main`; `/write abstract` on POGM4 produces a writer-critic score and a Claim–Evidence Table before the draft; six repos declare a manuscript; zoning2026 has one manuscript and no `.tex` fragments; no repo has a `scripts/R/` analysis tree.

Each repo is migrated on its own commit(s) in that repo, then re-linked, then `check_install.sh` must pass for it. POGM4 first (it is already on `$W`).

### Task 8.1: POGM4 (canary)

- [ ] Read `~/Research/POGM4/CLAUDE.md` in full and the `scripts/R/` tree listing. Archive the reference pipeline: `git mv scripts/R archive/scripts_R_reference` (or delete if `CLAUDE.md` line 28's "standalone reference only" has no consumer — grep the manuscript for `source(`/`scripts/R`; expect none). Remove `.claude/WORKFLOW_QUICK_REF.md` and `.claude/commands/` (two files: `zotero-notes.md`, `zotero-review.md` — read both; if they are still used, move them to `.claude/skills/<name>/SKILL.md` as project overrides with a `!.claude/skills/<name>/` gitignore negation). Keep `execute: cache: false` and add to `CLAUDE.md`: `**Declared deviation:** \`execute: cache: false\` — the \`fresh\` predicate renders only when stale, so the pipeline pays for it once per change.` Commit in POGM4.
- [ ] `RESEARCH_CLAUDE_ALLOW_BRANCH=1 "$W/scripts/check_install.sh" --project-dir ~/Research/POGM4` → PASS on everything but `branch` (WARN).
- [ ] **Success criterion 6:** in POGM4, `claude -p '/write abstract'` (or interactive) → expected sequence in the transcript and on disk: writer writes the abstract; `quality_reports/agent_dispatch.jsonl` shows `writer` then `writer-critic`; `quality_reports/reviews/writer-critic_<date>.md` and `claim_evidence_POGM4_<date>.md` exist; `pipeline_state.json` has `sections.abstract`; the draft is shown after the score. Record in `docs/audits/2026-09-08_stage0-red.md` under `## Success criteria`.

### Task 8.2: zoning2026

- [ ] Read `paper/manuscript.qmd` in full, `paper/manuscript_quarto_pdf.qmd` (confirm DEPRECATED per its own `CLAUDE.md`), `paper/tables/{descriptive,estimation,robustness}/*.tex` and the chunks that `\input` them. For each `.tex` fragment: identify the R that produced it (in `scripts/R/` or `scripts/python/`), move that code into a `tbl-*` chunk (`booktabs = TRUE`, notes) with `dependson`, delete the fragment and the `\input`. Delete `paper/manuscript_quarto_pdf.qmd` and its `.pdf`/`.tex`; delete `scripts/R` and `scripts/python` once every consumer is a chunk (`grep -rn 'source(\|read_rds\|readRDS' paper/manuscript.qmd` → none). Declare `manuscript: paper/manuscript.qmd` in `CLAUDE.md`. Run `python3 .claude/scripts/prose_number_check.py paper/manuscript.qmd` → 41 literals: each becomes an expression or an allowlist row with a reason. Render clean. Commit(s) in zoning2026.
- [ ] Re-link: `~/Research/zoning2026/bootstrap-pipeline.sh --tip` **only after the merge in Task 8.7**; until then `"$W/apply.sh" --project-dir ~/Research/zoning2026 --link` and `RESEARCH_CLAUDE_ALLOW_BRANCH=1 check_install.sh` → PASS.

### Task 8.3: affordable_housing_2026

- [ ] Declare `manuscript: manuscript_affordable_housing_2026.qmd` (it matches the convention; the declaration is still required). `git mv quality_reports/pipeline_state.json quality_reports/pipeline_state_legacy_2026-06-18.json` (the hand-written clo-author-era file is history, not state) and `python3 .claude/scripts/pipeline.py state init`; port its two scores into the new file: `state record-score strategy 94 --critic strategist-critic --report "legacy 2026-06-18"` and `state record-score code 92 --critic coder-critic --report "legacy 2026-06-18"` (the file's own numbers; read it first). `state validate` → valid. Commit. Re-link, check_install → PASS.

### Task 8.4: ESG

- [ ] Declare `manuscript: manuscript.qmd`. `scripts/` holds seven numbered analysis scripts and `generate_dashboard.py`: read each; any whose output the manuscript reads becomes a chunk; the rest move to `archive/scripts/` with a README line each; `scripts/acquire/` stays. Delete `scripts/generate_dashboard.py`. 14 literals → expressions or allowlist rows. Render clean. Commit. Re-link, check_install → PASS.

### Task 8.5: NAR_settlement

- [ ] On branch `phase1-event-study` (its working branch; do not switch it). Declare `manuscript: manuscript_NAR_settlement.qmd`. 2 literals → fix. `scripts/compare_golden.sh` is a verification aid, not analysis — leave, note it in `CLAUDE.md`. Commit. Re-link, check_install → PASS.

### Task 8.6: BRI

- [ ] No manuscript yet. `check_install.sh` gives WARN on `manuscript-declared`; `/pipeline` refuses with the declaration message (test it once: `cd ~/Research/BRI && python3 .claude/scripts/pipeline.py manuscript; echo exit=$?` → message + `exit=1`). Nothing to migrate. Re-link, check_install → PASS (WARN allowed).

### Task 8.7: Merge, re-link six to the shared checkout, lock bump, remove the worktree

- [ ] **Step 1: Final gates on the branch** — `cd "$W" && ./scripts/check_fork.sh && tests/run_fixture.sh && python3 -m unittest discover -s tests -p 'test_*.py'` → all exit 0.
- [ ] **Step 2: Merge** —
```bash
cd "$RC" && git status --porcelain | wc -l        # expect 0
git merge --no-ff repair/pipeline -m "merge: pipeline repair — one manuscript, every pair, every gate (spec 2026-09-08 v2)"
./scripts/check_fork.sh; echo exit=$?               # expect 0 on main
```
- [ ] **Step 3: Re-link the six to `$RC`** — for each repo: `./bootstrap-pipeline.sh --tip` (safe now: `$RC` is on `main`); then `"$RC/scripts/check_install.sh" --all; echo exit=$?` → `exit=0`, `branch` PASS ×6, `lock` PASS ×6 (the lock now records the merge SHA — that is the lock bump), `hooks-wired` PASS ×6, `manuscript-declared` PASS ×5 + WARN (BRI).
- [ ] **Step 4: Remove the worktree** — `git worktree remove ../research-claude-repair && git branch -d repair/pipeline && git worktree list` → one row. `readlink ~/Research/POGM4/.claude/agents/coder.md` → points into `$RC`, not the removed path.
- [ ] **Step 5: Success criteria, verbatim** — run and paste into `docs/audits/2026-09-08_repair-signoff.md`:
```bash
cd "$RC"
./scripts/check_fork.sh | tail -1
./scripts/check_install.sh --all | tail -1
python3 scripts/audit_graph.py . /tmp/g8.json | sed -n 2,3p
grep -rnE 'paper/tables|paper/figures|paper/sections|main\.tex|scripts/R/|00_master|\\cite[tp]?\{|\\input\{|\\label\{|\\ref\{|\\cref|latexmk|threeparttable|\\doublespacing|Bibliography_base|results_summary\.md|\.Rmd|bookdown|\\pause|\\only<' agents skills rules references hooks templates seeds scripts | grep -vc 'residue:'
tests/run_fixture.sh --live | tail -1
for r in POGM4 zoning2026 affordable_housing_2026 ESG NAR_settlement BRI; do echo "$r: $(grep -E '^manuscript:' ~/Research/$r/CLAUDE.md || echo '(none — BRI expected)')"; done
ls ~/Research/zoning2026/paper/tables 2>&1; ls -d ~/Research/*/scripts/R 2>&1
```
Expected, line by line: `✓ check_fork: PASS`; `✓ check_install: PASS`; `dangling path refs : 0` and `agents named, not on roster: []`; `0`; `✓ run_fixture: PASS`; five declarations + BRI none; `No such file or directory` twice.
- [ ] **Step 6: Commit the sign-off and push** — `git add docs/audits/2026-09-08_repair-signoff.md && git commit -m "docs(audit): repair sign-off — success criteria recorded" && git push origin main`. Then `/checkpoint`.

---

## Self-review (run by the plan author before handoff)

**Spec coverage.** D-1 → Task 5.4 (driver is a skill). D-2/D-10 → 1.1–1.3, 4.5. D-3 → 1.1, 1.5. D-4 → 0.6, 3.1, 3b.*. D-5 → 4.4. D-6/P-14 → 0.7 (workflow.md stays absent), 1.6. D-7 → 3b.* + gates. D-8 → 1b.1. D-9 → 1.7. D-11 → 5.1, 5.2, 5.6. D-12 → 0.3, 0.4, 5.7. D-13 → 2.1–2.3. D-14 → 7.1–7.4. D-15 → 4.2, 4.3. D-16 → 4.5. D-17 → 3b.1, 3b.3. D-18 → 3b.5, 3b.7, 6.2. D-19 → 3b.4, 3b.5. D-20 → 2.4, 3b.4, 3b.5. D-21 → 3b.4, 3b.6. D-22 → 3b.7. D-23 → 3b.5. D-24 → 3b.6, 3b.7, 6.2. D-25 → 3b.* (tool-name gate). §5 predicate types → 1.7 (+ P-7, P-16, P-17). §6 state and limits → 1.7, 1.4. §7 → 4.4. §8 every row → 3b.1–3b.7 (file by file), 6.1, 6.3, 6.4. §9 seeds/references/legacy → 2.1, 7b.1, 8.1–8.6. §11 every `check_fork` criterion → 0.5–0.7, 1.7, 2.1, 7.3; every `check_install` check → 0.8, 1b.1, 2.3, 7.5. §12 stages and stop conditions → the stage headers and §0.2. §13 → 8.7 Step 5. §14 open items → P-11, 2.4, 3b.5 (journal-digest), 2.2 (F13).

**Placeholder scan.** No "TBD"/"TODO"/"similar to Task N"; every code step carries its code; the two `unverified:` items (`claude -p` loading project skills; SubagentStop field name) are tested in 5.6/5.7 before anything depends on them.

**Type consistency.** Predicate field names (`glob`, `min`, `producer`, `file`, `heading`, `component`, `label_glob`, `of`) are identical in 1.1, 1.2, 1.3, 1.4 and 1.7. `pipeline.py` subcommands used by skills (3b, 4, 5) are the ones 1.7 defines: `manuscript`, `pre`, `post`, `fresh`, `score [--gate]`, `state {init,validate,show,record-score,strike,set-blocked,clear-blocked}`, `conflicts`, `registry check`, `log`. Report paths agree everywhere: `quality_reports/reviews/<critic>_<date>.md`, `quality_reports/reviews/claim_evidence_<project>_<date>.md`, `quality_reports/peer_review_<stem>/…`. Dispatch-log line shape (`at`, `agent`, `session`, `source`) is the same in 1.7, 5.1, 5.2. Markers are `residue:prohibition` / `residue:historical` everywhere (the cherry-picked `agent-refs:historical` is replaced in 0.7).
