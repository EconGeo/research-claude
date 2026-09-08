# Design: Quarto-Native Research Pipeline

**Date:** 2026-09-08
**Status:** APPROVED (design); implementation plan not yet written
**Repo:** `EconGeo/research-claude`
**Supersedes:** the clo-author submodule dependency and `rules/pipeline-precedence.md`

---

## Objective

Fork `research-claude` away from the `hugosantanna/clo-author` submodule and make it a
standalone, Quarto-native research pipeline: one `manuscript_<project>.qmd` as the single
source of truth, a set of format-agnostic critics, and no LaTeX/multi-file layer requiring
translation.

Cherry-pick every good idea from clo-author. Rewrite the format-bound ones rather than
translating them. Harvest the improvements already stranded in `~/Research/` projects.

---

## Why: the evidence

Four findings from an audit of the installed pipeline (2026-09-07/08).

**1. The critics were never the problem.** Measured LaTeX/Beamer/multi-file coupling across
all 47 clo-author agent, rule, and skill files:

| File | Lines | Coupled lines |
|---|---|---|
| `rules/working-paper-format.md` | 273 | 17% |
| `rules/content-standards.md` | 454 | 9% |
| `agents/storyteller.md` | 76 | 9% |
| `agents/writer.md` (104), `writer-critic.md` (62), `verifier.md` (128) | — | 6% each |
| everything else | — | 0–3% |

`coder-critic`, `methods-referee`, `domain-referee`, `strategist-critic`, `librarian*`,
`editor`, `orchestrator`, `explorer*` measure **0%**. The critics are already
format-agnostic. The coupling is concentrated in a handful of standards documents.

**2. The submodule is dead and one-way.** `clo-author` is pinned at **2026-05-10**. Nothing
has been pulled in four months.

**3. Value flows out of projects and never returns.** Improvements made while writing papers
are stranded in those papers:

| Agent | clo-author | POGM4 | zoning2026 |
|---|---|---|---|
| `editor` | 67 | **366** | 67 |
| `coder-critic` | 58 | **99** | **82** |
| `writer-critic` | 62 | 82 | 62 |
| `coder` | 136 | 152 | 136 |
| `methods-referee` | 207 | 212 (rewrite) | 207 |
| `domain-referee` | 147 | 137 (rewrite) | 147 |
| `verifier` | 128 | 90 (de-LaTeXed) | 128 |

The sharpest case: **POGM4 and zoning2026 independently taught `coder-critic` Quarto, and
taught it different halves.** POGM4 added Quarto Empirical Mode, Rmd Mode, and INV-23/INV-24
manifest coverage. zoning2026 added a Correctness Layer — hardcoded prose numbers (INV-11),
no derived CSVs in `data/raw/`, cache discipline, zero-inflation/extrapolation traps for
count outcomes. Neither project knows the other exists. A new project today scaffolds from
the 58-line baseline and gets neither.

**4. Some shipped files give agents actively wrong instructions**, and
`pipeline-precedence.md` does not cover them:

| File | Lines | What it tells the agents |
|---|---|---|
| `analyze/references/table-standards.md` | 321 | export bare `tabular`, wrap in `threeparttable`, prefer `talltblr` — the pipeline uses **flextable** for Word |
| `analyze/references/figure-standards.md` | 206 | "Output PDF for figures — use `ggsave('fig.pdf')`" — Word needs **PNG at `fig-dpi: 200`**; contradicts `quarto-word.md` |
| `rules/working-paper-format.md` | 273 | a live deduction table (−5 missing `\doublespacing`, −3 `natbib`, −3 `\hline`) applied to a `.qmd` |
| `rules/meta-governance.md` | 251 | that the project is a public template with **Emory** context and biology-PhD forkers |

`pipeline-precedence.md` names exactly six files: `analyze/SKILL.md`, `write/SKILL.md`,
`revise/SKILL.md`, `working-paper-format.md`, `content-invariants.md`, `permissions.md`.
`table-standards.md`, `figure-standards.md`, `content-standards.md`, and `meta-governance.md`
are **not on that list** — and that is where the concrete wrong instructions live. The fix is
not four more names on the list; it is that translation-by-precedence is the wrong mechanism.

---

## Decisions taken

| # | Decision | Rationale |
|---|---|---|
| D1 | **Keep worker→critic pairing; cut the orchestration graph** | The orchestrator is unreachable (only `/new-project` dispatches it, and `apply.sh` refuses to install `/new-project`). Its phase graph forbids the coder↔writer looping the research journal shows actually happens. Its pairing + escalation pattern demonstrably catches real defects. |
| D2 | **`research-claude` is authoritative; harvest projects first** | New projects must scaffold correct from day one. A documented promotion step returns future project improvements. |
| D3 | **Fold `librarian` into a ZotPilot bridge skill** | ZotPilot already covers search; `librarian.md` is WebSearch-first, contradicting `literature-search-order.md`. |
| D4 | **Keep `theorist` + `theorist-critic` in the default install** | Research spans empirical and theoretical work. |
| D5 | **De-project every harvested file** | No journal name, dataset name, project noun, or non-standard manuscript filename ships in the template. Standing rule, not a one-time step. |

---

## Architecture

The fork is surgical. Of three submodules, only one is third-party and dead:

| Submodule | Owner | State | Verdict |
|---|---|---|---|
| `clo-author` | `hugosantanna` | last commit 2026-05-10 | **remove** |
| `ai-audit` | `EconGeo` | live | **keep** — `/humanize`, `/verify-claims` are used and format-agnostic |
| `journal-digest` | `EconGeo` | live | **keep** — unrelated |

```
research-claude/
├── apply.sh              # reads only its own dirs
├── agents/         NEW   # vendored + harvested
├── skills/         GROWS # phase skills (absorbs root-skills/) + bridge skills
├── rules/          GROWS # + rewritten standards; pipeline-precedence.md DELETED
├── references/     NEW   # coding standards, voice-profile templates
├── hooks/          NEW   # 7 session/compact/lint hooks
├── templates/      GROWS # + ported design checklists, decision records
├── zotpilot-skills/      # unchanged (vendored — never edited in place)
└── submodules/
    ├── ai-audit/
    └── journal-digest/
```

`apply.sh` gets simpler: `CLO_SKIP_SKILLS`, the submodule traversal, and the precedence rule
all disappear.

---

## Work items

### A. Agents — vendor and harvest

| Agent | Source | De-project work |
|---|---|---|
| `editor` | POGM4 (366 vs 67) | none — verified generic, zero hardcoded journals |
| `coder-critic` | **merge POGM4 + zoning2026** | `manuscript_quarto_word` → `manuscript_<project>.qmd` |
| `methods-referee`, `domain-referee` | POGM4 rewrites | none |
| `writer-critic`, `writer`, `coder` | POGM4 | none |
| `verifier` | POGM4, partial | POGM4 correctly deleted the LaTeX checks but also dropped the two-mode structure and the INV-enforcement line — restore those, keep the deletion |
| `theorist`, `theorist-critic`, `strategist`, `strategist-critic`, `explorer`, `explorer-critic`, `data-engineer` | clo-author (identical everywhere) | vendor as-is |
| `storyteller`, `storyteller-critic` | clo-author | Quarto-only: drop `beamer-scaffold.tex`, keep `quarto-scaffold.qmd` |
| `orchestrator`, `guide-writer` | — | **delete** (D1) |
| `librarian`, `librarian-critic` | — | **delete** as agents; content survives in the bridge skill (D3) |
| `humanize-auditor`, `claim-verifier` | ai-audit | leave in the live submodule |

`editor` brings capability that has not been in use: a novelty check with an explicit
anti-hallucination caveat (every "already done" claim must carry a URL/DOI, otherwise report
"unable to verify"), referee selection that refuses to draw the same disposition twice, and a
`--variance N` mode running 3–5 referees to estimate review variance rather than enforce
diversity.

`NAR_settlement` is at baseline on every agent — nothing to harvest there.

### B. Ports — dormant capability worth having

Each has **never produced an artifact** in any project.

| Port | Quarto-native form |
|---|---|
| 6 design checklists (DiD, IV, RDD, event-study, structural, **descriptive**) | `templates/design-checklists/` verbatim — pure methodology, zero coupling. `descriptive.md` becomes the `/strategize` default for measurement papers |
| `decision-record.md` | `quality_reports/decisions/`; its *What Would Invalidate This* section is the home for threshold choices |
| `robustness-plan.md` + 3 PAP registry templates | ordered robustness checklist committed *before* estimation, so nothing reads as post-hoc |
| `audit-10-checks` | rewritten: check 1 becomes `quarto render` exits 0 (not `latexmk`); checks 5–10 (package inventory, dependency, provenance, execution, cross-reference, README) port unchanged |
| `narrative-arcs.md` | Descriptive arc extracted as a paper-structure aid, independent of `/talk` |
| FATAL / ADDRESSABLE / TASTE | promoted from `disposition-pool` into `/revise` as explicit comment classification |
| `notation-protocol.md` | de-LaTeXed; enforces INV-7 |
| `drafting-gates.md` | prose write-gate ("Results cannot be drafted without output files") — complements `prose_number_check.py` on the axis it cannot see |

### C. Drop — dormant and correctly so

`causal-audit-4-phases` (no causal claims in a descriptive paper) · `literature-review-6-categories` (superseded by D3) · `claim-source-map` (superseded by inline `r` + `prose_number_check.py`; INV-22 formally retired) · `execution-trace`, `pipeline-state.json` (D1) · `requirements-spec` (superseded by `superpowers:brainstorming`) · `constitutional-governance` (already realized as CLAUDE.md Core Principles) · `quality-report`/merges (superseded by the `/commit` gate)

### D. Rewrite — do not translate

| File | Fate |
|---|---|
| `table-standards.md` (321) | rewrite → flextable (Word) + kableExtra (PDF), per `quarto-word.md` / `quarto-pdf.md` |
| `figure-standards.md` (206) | rewrite → PNG `fig-dpi: 200` for Word, vector for PDF; keep the format-independent parts (no in-figure titles, colorblind palettes, serif fonts) |
| `working-paper-format.md` (273) | **delete** |
| `content-standards.md` (454) | rewrite, keeping format-independent content |
| `meta-governance.md` (251) | **delete** |
| `content-invariants.md` INV-12/13/22 | rewrite for chunk options and inline `r`; INV-22 retired |
| `permissions.md`, `lifecycle.md`, `orchestrator.md`, `workflow.md` dependency graph | delete (D1); worker→critic pairing, separation of powers, and 3-strikes escalation relocate into `rules/agents.md` |
| `pipeline-precedence.md` | **delete** — nothing left to take precedence over |

### E. New bridge skill — `skills/lit-position/`

`zotpilot-skills/` is vendored from `EconGeo/ZotPilot`. Editing it in place would recreate the
one-way drift this fork exists to eliminate. Instead, follow the existing bridge-skill pattern
(`new-project-ztp`, `ztp-data-tag`):

```
skills/lit-position/
   calls  ztp-research  → find + ingest
   calls  ztp-review    → synthesize local corpus
   produces  annotated_bibliography.md
             frontier_map.md      ← ZotPilot produces neither
             positioning.md       ←
   self-checks against librarian-critic's 6 categories
             (coverage, journal quality, scope calibration, recency, categorization)
```

---

## Success criteria

1. `submodules/clo-author` removed; `.gitmodules` retains only `ai-audit` and `journal-digest`.
2. `apply.sh` installs from `research-claude`'s own directories; `CLO_SKIP_SKILLS` and the precedence rule are gone.
3. `rules/pipeline-precedence.md` deleted.
4. `apply.sh --update` against a scratch copy of POGM4 leaves `quarto render manuscript_quarto_word.qmd` exiting 0.
5. `python3 ~/Research/scripts/prose_number_check.py` still exits 0 on that scratch copy.
6. No installed file matches `latexmk`, `\doublespacing`, `threeparttable`, `paper/main.tex`, `paper/sections`, or `Emory`.
7. No installed file matches a project noun (`POGM`, `JREPM`, `JRER`, `CoStar`, `SFPP`, `zoning`, `WRLURI`, `NAR`) or `manuscript_quarto_word`.
8. The merged `coder-critic` contains both POGM4's manifest checks (INV-23/INV-24) and zoning2026's Correctness Layer.
9. Every B-list port has a landing place. `templates/design-checklists/` ships in the template;
   `quality_reports/decisions/` and `paper/replication/` are created by the skills that write to
   them (`/strategize`, `/submit`), not at scaffold time — `apply.sh` creates only `explorations/`.

---

## Open items for the implementation plan

- Whether POGM4 is re-applied in place or verified on a scratch copy first (criterion 4 assumes scratch).
- The promotion step that returns future project improvements to `research-claude` — a documented `/promote` skill, or a manual checklist in the README.
- Whether `zoning2026`, `ESG`, `BRI`, `affordable_housing_2026` get re-applied, and in what order. They carry the same clo-author baseline and the same four actively-wrong standards files.
