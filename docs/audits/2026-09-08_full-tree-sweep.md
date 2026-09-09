# Full-tree sweep — line-level evidence for the pipeline repair

**Date:** 2026-09-08 · **Tree:** `main` @ `61277ea` · **Method:** every shipped file read end to end (`cat -n`),
paths tested with `[ -e ]` against repo root, the referring skill's directory, and `.claude/`-stripped root.
Three readers covered the skill sub-trees, references, hooks, templates and the rules not previously read;
the reviewing session read all 17 agents, all 18 `SKILL.md`, and the governance rules itself. Hook-contract
facts are `per docs:` (fetched this session from `code.claude.com/docs/en/hooks` and `/sub-agents`).

**Companion documents.** `2026-09-08_pipeline-audit-findings.md` (F1–F12, C1–C3), `2026-09-08_repair-spec-review.md`
(A1–A5, B1–B6, C, D, E), and the revised spec `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md`.

Class key: **1** multi-file / LaTeX / Rmd / Beamer residue · **2** deleted thing referenced as live · **3** path
reference (resolved / unresolved) · **4** contradicts the one-manuscript model · **5** project noun · **6** rubric
deduction at odds with the Quarto model or a retired invariant · **7** legacy token (`pipeline_state`, `claim_source_map`,
`Task` as tool) · **H** hook contract / README accuracy · **X** cross-file inconsistency or reference to a skill that does
not exist.

---

## 1. Agents (all 17 read in full by the reviewing session)

| File | Lines | Class | Finding |
|---|---|---|---|
| `coder.md` | 59 | 1,4 | "All outputs to `paper/tables/` and `paper/figures/`" |
| `coder.md` | 84–96 | 1,4 | Project Layout: `scripts/R/00_master.R … 07_tables.R (exports bare tabular)`, `functions/` |
| `coder.md` | 57 | 1,6 | "LaTeX via `modelsummary` or `fixest::etable` — bare `tabular` (INV-13)" — INV-13 now says the opposite |
| `coder.md` | 128–129 | 1,4 | Output Location: `paper/figures/main_regression/figure1.pdf` |
| `coder.md` | 60, 293 | 4 | `results_summary.md` as the Writer handoff; naming map in results summary |
| `coder.md` | 4 | X | `tools:` list has no `Agent`, fine; but Stage 0–3 describe scripts, not chunks |
| `data-engineer.md` | 154 | 4 | "Save cleaned dataset(s) as `.rds`" — cleaning is a cached chunk (INV-23) |
| `data-engineer.md` | 177–178 | 1,4 | figures to `paper/figures/`; underlying data `.rds` in `Output/` |
| `data-engineer.md` | 191–192 | 1,4 | "summary stats table (LaTeX format) … Save to `paper/tables/`" |
| `data-engineer.md` | 165, 205 | 4 | `ggsave()` dimensions; `saveRDS()` every object |
| `theorist.md` | 1052–1054 | 1,4 | Output `assumptions.tex`, `results.tex`, `proofs.tex` |
| `theorist.md` | 1032 | 3 | `Bibliography_base.bib` — canonical is `references.bib` |
| `theorist.md` | 1027 | 1 | "using project preamble environments" |
| `verifier.md` | 41 | 1,4 | check 2: `Rscript scripts/R/FILENAME.R` |
| `verifier.md` | 49–51 | 1,4 | check 3: `\input{}`/`\include{}` resolve; `paper/tables/`, `paper/figures/` |
| `verifier.md` | 58–66 | 4 | checks 5, 8, 9: master script, orphan scripts, "traced to a specific script" |
| `verifier.md` | 82 | 1 | report row "LaTeX compilation" |
| `verifier.md` | 21 | X | "Submission Mode (`/audit-replication`, `/data-deposit`, `/submit`)" — first two skills do not exist |
| `writer-critic.md` | 4 | 1 | description: "LaTeX format, compilation … claim-source traceability" |
| `writer-critic.md` | 41 | 2,7 | "enforce INV-1 through INV-13 and INV-22" |
| `writer-critic.md` | 46 | 1,4 | Standalone: "invoked via `/review [file.tex]`" |
| `writer-critic.md` | 50–68 | 1,4 | "Rmd Mode" — `.qmd` treated as the exception; `\@ref()`; `templates/rmd-preamble.tex` |
| `writer-critic.md` | 62, 82 | 2,6,7 | INV-22 "still applies" / "non-negotiable" |
| `writer-critic.md` | 17 | X | "The severity level (from the orchestrator)" — unowned input |
| `writer-critic.md` | 72 | 2 | Strike 3 → Orchestrator (rules/agents.md §3 says User) |
| `writer.md` | — | ✓ | Quarto-native throughout; `Bibliography_base` absent; INV-22 marked retired |
| `coder-critic.md` | 17 | X | severity line from orchestrator |
| `coder-critic.md` | 4, 32, 69 | 4 | description/task/standalone framed as "scripts"; `/review [file.R]` |
| `coder-critic.md` | 90–110 | 1 | Rmd Mode retained (bookdown, `data/cleaned/`, INV numbers that predate current file) |
| `coder-critic.md` | 44–88 | ✓ | Correctness Layer + Quarto Empirical Mode are correct and are the model |
| `editor.md` | 4, 637 | X | "Used by `/review-paper --peer`" — skill is `/review` |
| `editor.md` | 536 | 3 | `templates/journal-profile-template.md` — absent |
| `editor.md` | 573 | X | `/audit-reproducibility` — no such skill |
| `domain-referee.md` | 4, 241 | X | `/review-paper --peer`; `domain-reviewer.md` (a `~/Courses` agent) named as sibling |
| `methods-referee.md` | 4, 517, 693 | X | `/review-paper`; "v1.8.0 … political science use" (clo-author release note); `/audit-reproducibility` |
| `explorer.md` | 390 | 2 | "data used in the Librarian's bibliography" |
| `explorer-critic.md`, `storyteller-critic.md`, `strategist-critic.md`, `theorist-critic.md` | 17 | X | severity line from orchestrator |
| `strategist.md` | 900–905 | 3 | outputs to `quality_reports/strategy/[project]/` — consistent with registry; fine |
| `storyteller.md` | 742, 755 | 3 | `talks/custom.scss` — nothing ships it |
| `editor.md`, `domain-referee.md`, `methods-referee.md` | header | credit | clo-author credit comments — acceptable |

## 2. Skills — `SKILL.md` files (read in full by the reviewing session)

| File | Lines | Class | Finding |
|---|---|---|---|
| `analyze/SKILL.md` | 58, 60, 66, 106, 130–143 | 1,4 | tables to `paper/tables/`, `.tex` tables, scripts to `scripts/R/`, `saveRDS` to `scripts/R/output/` |
| `analyze/SKILL.md` | 4, 161–176 | 4 | `--dual` dispatches two coders in parallel on one manuscript |
| `analyze/SKILL.md` | 92–95 | 2,3 | `python3 scripts/generate_html_report.py` / `generate_dashboard.py` — absent |
| `analyze/SKILL.md` | 148–157 | 4 | `results_summary.md` mandatory handoff |
| `analyze/SKILL.md` | 199–219 | 4 | lists script-era templates as live components |
| `write/SKILL.md` | 33–34 | 1,4 | context: `Bibliography_base.bib`, scan `paper/tables/`, `paper/figures/` |
| `write/SKILL.md` | 71–72, 77 | 1,4 | self-check: `\label{eq:…}`, `\cite{}` keys, tables in `paper/tables/` |
| `write/SKILL.md` | 81 | 2,7 | claim-source map checklist item |
| `write/SKILL.md` | 106, 112 | 1 | style corpus `.tex/.pdf` only (no `.qmd`/`.docx`) |
| `write/SKILL.md` | 167–172 | 1 | "LaTeX Conventions" section: `\citet{}`, `\citep{}`, `\toprule` |
| `write/SKILL.md` | — | pairing | zero occurrences of "critic" |
| `review/SKILL.md` | 19, 21, 38 | 1,4 | auto-detect `.tex` only; no `.qmd` route |
| `review/SKILL.md` | 278 | 1,4 | Verifier pass/fail defined for `.tex` |
| `review/SKILL.md` | 108–113, 210–213, 254–257 | 2,3 | six `generate_*` invocations |
| `review/SKILL.md` | 57 | X | "Searches the literature via WebSearch to verify novelty" — editor.md caps at 3 probes; fine |
| `submit/SKILL.md` | 21 | 2 | `/submit target` → "Agent: Orchestrator" |
| `submit/SKILL.md` | 31 | pairing | `/submit package` = Coder + Verifier, no critic |
| `submit/SKILL.md` | 73–74 | 2,3 | `generate_*` |
| `submit/SKILL.md` | 86 | 1 | `templates/cover-letter.tex` |
| `revise/SKILL.md` | 53–56 | pairing | Writer/Coder dispatched, no critic |
| `revise/SKILL.md` | 80 | 3 | `templates/response-letter.md` — file is `.qmd` |
| `discover/SKILL.md` | 70–113, 193 | 2 | `/discover lit` dispatches Librarian → librarian-critic; Principles names the pair |
| `discover/SKILL.md` | 95–98 | 2,3 | `generate_*` |
| `strategize/SKILL.md` | 257–261 | 2,3 | `generate_*` |
| `strategize/SKILL.md` | 397, 426–428 | 1,4 | theory outputs `assumptions.tex`, `results.tex`, `proofs.tex` |
| `talk/SKILL.md` | — | ✓ | RevealJS; clean apart from scaffold paths (below) |
| `tools/SKILL.md` | 18–30 | 2,3 | `/tools dashboard` → absent script |
| `tools/SKILL.md` | 68–70 | 4 | lint default `scripts/`, example `scripts/02_estimate.R` |
| `tools/SKILL.md` | 111–115 | 2,3 | `/tools deploy` → `guide/` (deleted with guide-writer) |
| `tools/SKILL.md` | 120–160 | 2,4 | `/tools upgrade` clones `hugosantanna/clo-author`, deletes `.claude/` — would delete every symlink |
| `tools/SKILL.md` | 151 | X | `Bibliography_base.bib` |
| `tools/SKILL.md` | 5 | 7 | `allowed-tools: … Task` |
| `checkpoint/SKILL.md` | 173–178, 189 | 2,3 | dashboard refresh step → absent script |
| `checkpoint/SKILL.md` | 155 | X | Obsidian REST tool names vs `mcp__obsidian-files__*` used by `obsidian-digest-sync` |
| `checkpoint/SKILL.md` | 247 | 2 | "when invoked from within clo-author" |
| `dashboard/SKILL.md` | 10, 20, 31, 112 | X | `project_dashboard.html` vs `rules/html-dashboard.md` `research_overview.html` |
| `dashboard/SKILL.md` | 23, 59 | 4 | enumerates `scripts/` analysis tree |
| `dashboard/SKILL.md` | 72–78 | 5 | "IV components — instruments (soil, wind, etc.)" — one project's design |
| `dashboard/SKILL.md` | 97 | 2,3 | "Use the clo-author HTML design system" → `templates/html/base/styles.css` absent |
| `freeze/SKILL.md` | 9, 14–15, 36 | 1 | examples `paper/`, `scripts/` |
| `freeze/SKILL.md` | 55 | H | "hook checks a session flag" — it does not |
| `careful/SKILL.md` | 26, 34, 64 | H | lists patterns the hook lacks; claims override prompt that `deny` does not offer |
| `lit-position/SKILL.md` | 22, 126 | 3 | `zotpilot-skills/` repo-root path, meaningless inside a project |
| `new-project-ztp/SKILL.md` | 82, 89, 90 | 2 | librarian ×3; `/discover lit`; `bibliography_base.bib` |
| `promote/SKILL.md` | — | ✓ | clean |
| `ztp-data-tag/SKILL.md` | 51 | 3 | "README Step 7" unresolved |
| `obsidian-digest-sync/SKILL.md` | 24–30, 62, 69 | 3 | `journal_digest/` vs installed `journal-digest/` (`unverified:` which is the runtime dir) |
| all phase skills | frontmatter | 7 | `allowed-tools: … Task` (alias; new files should say `Agent`) |

## 3. Skills — sub-files (`analyze`, `write`, `revise`)

| File | Lines | Class | Finding |
|---|---|---|---|
| `analyze/gotchas.md` | 7, 9, 33 | 1,6 | bare `tabular` / `latex_tabular` advice; cites INV-13 for the opposite of its text |
| `analyze/gotchas.md` | 18, 35 | 1,4 | `saveRDS()` all objects; `results_summary.md` mandatory |
| `analyze/gotchas.md` | 32, 34 | 1,6 | titles in `\caption{}` (INV-12 now `fig-cap`); PDF required for figures |
| `analyze/references/table-standards.md` | 57–64 | 6 | canonical `tbl-main` example omits `booktabs = TRUE` (−5 in quarto-empirical.md:300) |
| `analyze/references/table-standards.md` | 27, 52 | 3 | bare `journal-profiles.md` |
| `analyze/references/figure-standards.md` | — | ✓ | clean (prohibitions only) |
| `analyze/templates/paper-to-code-map.md` | 3, 9, 36–38 | 1,3,4 | map lives in `01_setup.R` and `results_summary.md`; multi-script |
| `analyze/templates/pre-code-report.md` | 57–59, 75 | 1,3,4 | tables/figures "with filenames"; `paper/tables/`; `01_setup.R` |
| `analyze/templates/r-script-structure.R` | whole | 1,4,6 | numbered-script scaffold: creates `paper/tables/`, `saveRDS` to `scripts/R/output/`, writes `.tex`, `ggsave`; INV-12/13 misattributed; `df` top-level |
| `analyze/templates/python-script-structure.py` | whole | 1,4,6 | same in Python; `df` top-level |
| `analyze/templates/results-summary.md` | whole | 1,4 | the separate handoff file; `paper/tables/*.tex`, `scripts/R/output/*.rds` |
| `analyze/config/replication-tolerances.json` | — | ✓ | clean; consumer is `--dual` |
| `write/gotchas.md` | 7–8 | 1,3 | `\citet`/`\citep`; `Bibliography_base.bib` |
| `write/gotchas.md` | 5 | 3 | bare `personal-style-guide.md` |
| `write/templates/drafting-gates.md` | 32–33, 43 | 1,3,4,6 | gate requires `paper/tables/*.tex` and `paper/figures/*.pdf` — blocks every correct project |
| `write/templates/style-extraction-protocol.md` | 13, 48 | 1,3 | corpus `.tex/.pdf` only; scans `\cite{}`; `Bibliography_base.bib` |
| `write/templates/section-templates.md` | 163, 165 | 4 | "Figure N shows" placeholders (minor) |
| `write/templates/paragraph-moves.md` | 16 | 4 | "Table N" placeholder (minor) |
| `write/references/notation-protocol.md` | 24 | 4 | "coder's naming map" → survives only if the map moves into the setup chunk |
| `write/templates/cleanup-patterns.md` | — | ✓ | clean |
| `revise/templates/response-letter.qmd`, `response-tracker.md`, `gotchas.md` | — | ✓ | clean |
| `revise/templates/diplomatic-disagreement.md` | 14 | 4 | "Appendix Table X" placeholder (minor) |

## 4. Skills — sub-files (`review`, `submit`, `talk`, `discover`, `strategize`)

| File | Lines | Class | Finding |
|---|---|---|---|
| `review/config/scoring-rubrics.md` | 15, 28, 29 | 2,6,7 | INV-22 deductions (−15, −5 per, −10 per) |
| `review/config/scoring-rubrics.md` | 168–179 | 2 | `## Librarian-Critic` section with 8 deduction rows |
| `review/config/scoring-rubrics.md` | 56, 62, 69, 74, 82, 84, 86 | 4,6 | "Scripts don't run", naming map, "Missing RDS saves −10", output files, stale outputs, "No project layout (no numbered scripts) −5" |
| `review/config/scoring-rubrics.md` | 48–90 | 6 | Coder-Critic block carries none of the 12 quarto-empirical.md deductions |
| `review/config/scoring-rubrics.md` | 31, 44, 143 | 1 | "document class", "Overfull hbox warnings", "preamble" |
| `review/templates/manuscript-review-8-categories.md` | 11, 47–51, 204–207 | 2,6,7 | INV-22 enforced; claim-source map section with −15/−5/−10/−5 |
| `review/templates/manuscript-review-8-categories.md` | 113 | 6 | "Missing `csl:` in YAML −3" — PDF path must not have top-level `csl:` (quarto-empirical.md:67) |
| `review/templates/manuscript-review-8-categories.md` | 174 | 1,4 | standalone "via `/review [file.tex]`" |
| `review/templates/manuscript-review-8-categories.md` | 102, 194 | 1 | "LaTeX and Format" headings |
| `review/templates/code-review-16-categories.md` | 25, 62–64, 77, 104, 106, 109–110, 115–118, 179 | 1,4,6 | `01_setup.R`, `00_master.R`, `functions/`, `\caption{}`, `ggsave()`, bare tabular, `\toprule`, RDS = HIGH severity, `/review [file.R]`; no Quarto category at all |
| `review/templates/code-review-16-categories.md` | 11 | X | enforces INV-13–19 only; content-invariants.md:125 assigns coder-critic INV-11, 23, 24 too |
| `review/templates/theory-review-4-phases.md` | 99, 127, 139 | 1,3,4 | `preambles/header.tex`; `Bibliography_base.bib`; "LaTeX compiles" |
| `review/gotchas.md` | 19 | X | stale self-note ("4 categories" vs 6) |
| `review/templates/{data-review,disposition-pool,referee-report-template,talk-review}.md` | — | ✓ | clean |
| `submit/gotchas.md` | 8 | 1,4 | "delete `.aux` files first" |
| `submit/templates/audit-10-checks.md` | 12–13 | X | refers to "check 11" that does not exist (it is 4b) |
| `submit/templates/audit-10-checks.md` | 15–18, 58, 63, 72 | 4 | script execution, master script, "traced to a specific script" |
| `submit/templates/audit-10-checks.md` | 77–79 | 1 | stale INV-9/10/14 phrasing |
| `submit/templates/cover-letter.tex` | whole | 1 | only LaTeX-source template shipped; convert to `.qmd` like `response-letter.qmd` |
| `submit/templates/replication-readme.md` | 24–25, 31–32 | 1,3,4 | `01_clean.R`, `02_analysis.R`, `paper/tables/` |
| `submit/templates/submission-checklist.md` | 17–19, 23, 27 | 1,4 | stale INV-9/10; `\ref`/`\cref`; scripts; master script |
| `talk/templates/quarto-scaffold.qmd` | 8, 17, 24–25, 59, 111, 129 | 1,3,4 | `custom.scss` unshipped; `fig-format: pdf` on HTML; `../../Bibliography_base.bib`; `apa.csl`; `../../paper/figures/*.pdf` ×3 |
| `talk/references/slide-design-principles.md` | 31, 33 | 1 | `\pause`, `\only<>` (Beamer) |
| `talk/gotchas.md`, `templates/format-constraints.md`, `templates/narrative-arcs.md` | — | ✓ | clean |
| `discover/gotchas.md` | 10 | 2 | "librarian and explorer agents run in parallel" |
| `discover/references/pdf-processing.md` | 3, 6 | 3 | `master_supporting_docs/` (project upload dir, unshipped) |
| `discover/templates/*` | — | ✓ | clean |
| `strategize/templates/theory-memo.md` | 3, 29–34, 81–84 | 1,3,4 | `assumptions.tex`, `results.tex`, `proofs.tex` |
| `strategize/templates/strategy-memo.md` | 54 | note | pseudo-code `data = df` |
| `strategize/{gotchas,references,design-checklists,pap-templates,pre-strategy-report,robustness-plan,decision-record}` | — | ✓ | clean |

## 5. References (seeded into every project by `apply.sh`)

| File | Lines | Class | Finding |
|---|---|---|---|
| `coding-standards-rmd.md` | whole | 1,4,X | `.Rmd`/bookdown/`scripts/R/` contract: `cache = FALSE` globally (quarto-empirical requires `cache: true`), `tab-` prefix (should be `tbl-`), data prep in `scripts/R/01_data_preparation.R`, `format = "latex"`, `\@ref`, `main.tex`, `paper/tables/`; names `rmd-coder-critic` (no such agent); INV-23/24 cited with stale meanings |
| `coding-standards-r.md` | 139–140, 208 | 4 | `functions/` directory of files; `source(here(...))` implied fine (−10 in a chunk) |
| `coding-standards-julia.md` | 23, 29 | 1 | LaTeX/PGF figure path assumed |
| `coding-standards-python.md` | — | ✓ | clean |
| `discipline-cards.md` | 3, 101–104, 144 | X | consumers `/research-ideation`, `/interview-me`, `/preregister`, `/review-paper` — none exist |
| `discipline-cards.md` | 23, 52, 81, 95 | X | "shipped in journal-profiles.md": AEA P&P, APSR, AJPS, JOP, REE, JREFE, JRER, JREPM — **none shipped** |
| `discipline-cards.md` | 81 | X | "JHE (housing policy)" collides with journal-profiles' JHE = Journal of Health Economics |
| `discipline-cards.md` | 143 | 3 | `.claude/references/audit-pet-peeves.md` — absent (pet-peeve pools live in `agents/editor.md`) |
| `domain-profile.md` | 19, 74 | 2 | HTML comments instructing the Orchestrator and the Librarian |
| `journal-profiles.md` | — | X | 34 profiles; **no real-estate journal** (REE, JREFE, JRER, JREPM, JHE-housing all absent; JUE only) |
| `journal-profiles.md` | 29 | X | "see content-standards.md for implementation details" — now delegated to `skills/analyze/references/table-standards.md` |
| `personal-style-guide.md` | 22 | 1,3 | `.tex` corpus example; `master_supporting_docs/` |
| `prompt-formatting-core.md` | 3, 64, 168, 170, 176, 178 | X | orphan — consumers `/prompt`, `/prompt-only`, `/seven-pass-review`, `/devils-advocate`, `/promote-memory`, `/interview-me`, `/preregister`, `/research-ideation`, `/data-analysis` — none exist |

## 6. Rules (remaining eight, read in full by the third reader)

| File | Lines | Class | Finding |
|---|---|---|---|
| `content-invariants.md` INV-9 | 38–40 | X | "with a `csl:`" — quarto-empirical.md:67 and quarto-pdf.md:31–32 forbid a top-level `csl:` on the PDF path |
| `content-invariants.md` INV-18 | 73–74 | 4 | "Output files go to CLAUDE.md Output Organization path" — the model writes no output files |
| `content-invariants.md` INV-10 | 42–44 | 1 | hyperref/cleveref order — PDF-preamble specific by design; fine if conditional |
| `content-invariants.md` | 109, 128 | X | INV-14/15/16/19 "enforced by lint hook + verifier" — `lint-scripts.sh` never reads `.qmd` (L22 `*.R/*.py/*.jl` only), has no `source()` check, checks library position only after line 30 |
| `content-invariants.md` | 110 vs `data-manifest.md` 86–87, 95 | X | INV-23/INV-24 meanings swapped between the two files; data-manifest.md:94 claims "write gate item 3 requires manifest completeness" — item 3 is `prose_number_check.py` |
| `content-standards.md` | 109–131 | 4,3 | explorations layout `R/`, `scripts/`, `output/`; "graduate to production — copy to `R/`, `scripts/`"; `templates/exploration-readme.md`, `templates/archive-readme.md` absent |
| `content-standards.md` | 8, 51 | 3 | `master_supporting_docs/` |
| `html-dashboard.md` | 3 | X | `research_overview.html` vs dashboard skill's `project_dashboard.html` |
| `html-dashboard.md` | 102, 113, 118 | 5 | "counties, panel years", "[Wind]", "Wind/instrument deep-dive" — one project's design |
| `html-dashboard.md` | 148 | 2,3 | "clo-author design system from `templates/html/base/styles.css`" — absent |
| `html-dashboard.md` | 186–191 | X | no generator exists; rule demands manual rebuild "after every pipeline-related interaction" |
| `ai-disclosure.md` | 66–69 | 2 (provenance) | dated librarian entry — keep, marker-exempt |
| `data-manifest.md` | 25–28 | 5 | "National Zoning Atlas", `nza_cbsa_baseline.csv`, `zoneomics.com` — project shape in a shared rule |
| `quarto-pdf.md` | 23 | 3 | `include-in-header: "templates/quarto-preamble.tex"` required (−3 if missing) but **shipped by nothing** (same at quarto-empirical.md:27, 55) |
| `quarto-word.md` | 27–28 vs 37 | 3,X | YAML `csl: "templates/apa.csl"` vs prose "no need to bundle a copy"; `~/Zotero/styles/` tilde path; `templates/word-reference.docx` unshipped |
| `registry-verification-gate.md` | — | legacy | 16 `scripts/R/` refs, 4 orchestrator refs; self-declared legacy |
| `logging.md` | 46–79 | 7 | Pipeline State / traces / Learning Loop → `templates/pipeline-state.json` absent; cites `orchestrator.md §9` |
| `agents.md` | §1, §2, §3, §4 | 2,X | Orchestrator ×9; librarian row; "Beamer talk"; §4 "No phase graph" contradicts the repair |
| `quality.md` | §1, §2 | X | weights absent; §2 severity gradient supplied by nobody |
| `revision.md` | 28, 40 | 2 | Orchestrator ×2 |
| `literature-search-order.md`, `shared-pipeline.md`, `session-handoff.md` | — | ✓ | clean |

## 7. Hooks (`per docs:` contract)

| Hook | Event | Contract | Output channel | README row |
|---|---|---|---|---|
| `context-monitor.py` | PostToolUse, **unwired** | ✓ stdin JSON | ✓ `systemMessage` + `additionalContext` | L37 omits 90% tier |
| `context-monitor.py` | — | X | thresholds keyed by project, never reset → each fires **once per project ever** (L135–155); transcript size ÷ 4 as proxy over-reads after compaction | — |
| `lint-scripts.sh` | CLI, called by post-edit-lint | n/a | plain stdout, exit 0 → **invisible** when called from a hook | L34 "analysis scripts" |
| `lint-scripts.sh` | — | X | L138 bare `boot` substring matches `booktabs` → false HIGH "no set.seed()" on any table-building file; never reads `.qmd` | — |
| `log-reminder.py` | Stop | ✓ | stderr + exit 0 → **not a documented channel; inert** | L38 accurate to code, channel dead |
| `notify.sh` | Notification | ✓ | desktop | ✓ |
| `post-compact-restore.py` | SessionStart(compact\|resume) | ✓ `source` | ✓ `additionalContext` | **L32 says `PostCompact` — no such event** |
| `post-compact-restore.py` | — | X | surfaces `quality_reports/plans/` and `session_logs/`, not `pipeline_state.json` | — |
| `post-edit-lint.sh` | PostToolUse | ✓ jq `.tool_input.file_path` | delegates to lint stdout, stderr discarded → **invisible** | L33 |
| `post-merge.sh` | **git** post-merge | n/a | never installed to `.git/hooks/` by anything | L36 lists it beside Claude hooks |
| `pre-compact.py` | PreCompact | ✓ | block path exit 2 ✓; normal path ANSI stderr → inert; appends to latest session log on every compaction | **L31 description does not match code** |
| `protect-files.sh` | PreToolUse, **unwired** | ✓ exit 2 | ✓ | L35 ✓; L3 "customise for your project" edits every project through the link |
| `session-guard.py` | PreToolUse | ✓ `permissionDecision: deny` | ✓ | **L30 says `SessionStart` / "Session state checks" — wrong on both columns** |
| `session-guard.py` | — | X | L54 exempts everything under `/.claude/`, including `.claude/state/session-guards.json`, so the guard can be disabled by an Edit it does not block | — |
| `verify-reminder.py` | PostToolUse | ✓ | ✓ | L39 omits `.tex`; L33 `.tex → /compile-latex` (no such skill) |
| `templates/settings.json` | — | — | wires 7 of 12; unwired: `context-monitor`, `protect-files`, `lint-scripts` (CLI), `post-merge` (git) | — |

## 8. Templates and install layer

| File | Lines | Class | Finding |
|---|---|---|---|
| `templates/gitignore` | 67–72 | X | ignores only `.claude/scripts/prose_number_check.py`; nothing for `.claude/scripts/*` or `.claude/templates/*`; six repos' copies identical (seed, never overwritten) |
| `templates/gitignore` | 36 | 4 (mild) | `data/cleaned/` implies a cleaned-data stage |
| `templates/handoff.md` | 9 | X | "Regenerated by /checkpoint" — checkpoint skill never mentions HANDOFF.md |
| `templates/bootstrap-pipeline.sh` | 20 | note | maintainer default `$HOME/Academic/research-claude` (env override exists; coauthor path is project-local) — accepted |
| `templates/` (root) | — | X | mixes shipped templates with project seeds (`gitignore`, `settings.json`, `bootstrap-pipeline.sh`, `ai-use-log.md`, `data_manifest.md`); agents reference project-level `templates/ai-use-log.md` and `templates/quarto-preamble.tex` |
| `apply.sh` | 79–80, 175–184 | X | links `scripts/prose_number_check.py` only; no `templates/`; `references/*.md` copied once |
| `scripts/check_install.sh` | `LINKED`, `want` | X | no `templates`; membership covers only `prose_number_check.py`; no `hooks-wired`; no `branch` |
| `scripts/check_fork.sh` | D1 block | X | asserts the five files the repair restores are absent; `latex-residue` pattern misses every item in §1–§4 above |
| `scripts/check_fork.sh` | — | X | criteria 9a/9b exist only on `fix/critic-dispatch` @ `cd1d47a`, unmerged; `stash@{0}` holds a partial `/discover` edit |
| `README.md` | — | 2 | 11 references to librarian / orchestrator / clo-author (D-A ruled in scope) |

## 9. Vendored and submodule trees

| File | Lines | Class | Finding |
|---|---|---|---|
| `zotpilot-skills/seed-papers/SKILL.md` | 4, 7, 9, 16, 20, 22, 125, 138, 147 | 2 | librarian ×7, `/discover lit` ×4 — fix upstream in `EconGeo/ZotPilot`, re-vendor |
| `submodules/ai-audit/rules/ai-disclosure.md` | 66 | provenance | dated librarian entry — WARN tier, never edited |

## 10. Paper repos (project-side residue, migrated not accommodated)

| Repo | Finding |
|---|---|
| POGM4 | manuscript `manuscript_quarto_word.qmd`; `execute: cache: false` by declared deviation; `scripts/R/` "standalone reference pipeline"; `.claude/WORKFLOW_QUICK_REF.md`, `.claude/commands/` (clo-author residue) |
| zoning2026 | two manuscripts under `paper/` (`manuscript.qmd` live, `manuscript_quarto_pdf.qmd` deprecated); `paper/tables/*.tex` fragments read by the manuscript; `scripts/` deprecated; 41 unexplained prose literals |
| affordable_housing_2026 | hand-written `quality_reports/pipeline_state.json` from the clo-author era (records `librarian: complete`); otherwise conforming |
| ESG | `manuscript.qmd`; 14 unexplained literals |
| NAR_settlement | conforming; on `phase1-event-study`; 2 literals |
| BRI | no manuscript yet |
| all six | `.gitignore` covers only `prose_number_check.py` under `.claude/scripts/`; `settings.json` wires 7 hooks |

## 11. Missing things referenced by shipped files (tested absent)

Scripts: `scripts/generate_dashboard.py`, `scripts/generate_html_report.py`. Templates: `templates/quarto-preamble.tex`,
`templates/pipeline-state.json`, `templates/journal-profile-template.md`, `templates/exploration-readme.md`,
`templates/archive-readme.md`, `templates/html/base/styles.css`, `templates/rmd-preamble.tex`, `talks/custom.scss`,
`templates/apa.csl`, `templates/word-reference.docx`. References: `references/audit-pet-peeves.md`. Directories: `guide/`.
Agents: `orchestrator`, `librarian`, `librarian-critic`, `guide-writer`, `rmd-coder-critic`, `domain-reviewer`.
Skills: `/new-project`, `/review-paper`, `/audit-replication`, `/data-deposit`, `/audit-reproducibility`, `/compile-latex`,
`/prompt`, `/prompt-only`, `/interview-me`, `/research-ideation`, `/preregister`, `/seven-pass-review`, `/devils-advocate`,
`/promote-memory`, `/data-analysis`, `/tools compile`.

## Addendum (found during repair)

Found running the widened residue grep for baseline snapshot
`docs/audits/baseline-2026-09-08/` (2026-09-08, Task 0.1): the sweep's own row for
`writer.md` (§1, line 49) reads "Quarto-native throughout; `Bibliography_base` absent;
INV-22 marked retired" and marks the file **✓ clean**. It is not.

| File | Lines | Class | Finding |
|---|---|---|---|
| `writer.md` | 44 | 4 | "Read `quality_reports/results_summary.md` (produced by `/analyze`)" — a separate handoff file read as a Results-drafting prerequisite; the same class-4 "contradicts the one-manuscript model" issue already flagged at `coder.md:60`, `analyze/SKILL.md:59`, and `analyze/gotchas.md:35` for the file `writer.md` reads here |

Checked systematically (fix round 1): every row in §1–§8 whose Class column is `✓`
was cross-referenced against `docs/audits/baseline-2026-09-08/residue_grep.txt`, by
grepping the grep output for each such row's filename(s) — not by a whole-document
read alone, since the first pass missed a partial-range case (below). Two shapes of
✓ row exist in this document:

- **Whole-file ✓** (Lines column is `—`): `writer.md` (gap found, above),
  `talk/SKILL.md`, `promote/SKILL.md`, `analyze/references/figure-standards.md`,
  `analyze/config/replication-tolerances.json`, `write/templates/cleanup-patterns.md`,
  `revise/templates/{response-letter.qmd,response-tracker.md,gotchas.md}`,
  `review/templates/{data-review,disposition-pool,referee-report-template,talk-review}.md`,
  `talk/{gotchas.md}`, `templates/{format-constraints.md,narrative-arcs.md}`,
  `discover/templates/*`, `strategize/{gotchas,references,design-checklists,
  pap-templates,pre-strategy-report,robustness-plan,decision-record}`,
  `coding-standards-python.md`, `literature-search-order.md`, `shared-pipeline.md`,
  `session-handoff.md`. None of these (other than `writer.md`) has a hit in the
  grep output.
- **Partial-range ✓** (Lines column names a span within a file that is otherwise
  not clean): exactly one such row exists in §1–§8 — `coder-critic.md` line 53,
  `44–88`, "Correctness Layer + Quarto Empirical Mode are correct and are the
  model." This is a second gap (below). (The apparent ✓ marks in §7's hooks table,
  e.g. `log-reminder.py`, `notify.sh`, `pre-compact.py`, are a different table
  schema — Contract/Output-channel columns, not a residue Class column — and do
  not assert a file or line-range is free of the multi-file/LaTeX/Rmd residue this
  grep targets; they are out of scope for this check.)

**Second entry — `coder-critic.md:44–88` is not actually all clean:**

| File | Lines | Class | Finding |
|---|---|---|---|
| `coder-critic.md` | 84 | 1 | "no analysis `.R` script in `scripts/R/` beyond acquisition (−5 per)" — inside the range the sweep marks ✓ (44–88) |
| `coder-critic.md` | 87 | 1 | "This mode supersedes Rmd Mode for `.qmd` targets. (The Rmd Mode invariant numbers below predate the current content-invariants and apply only to genuine `.Rmd` projects.)" — also inside 44–88 |

Both are **documentation gaps in the sweep, not unscheduled repair work**: both
lines are already scheduled for treatment by the repair plan's Task 3b.4 Step 2
(plan line 3377) — line 84 gains a `<!-- residue:prohibition -->` marker, and the
"This mode supersedes Rmd Mode..." sentence is deleted along with the whole
`## Rmd Mode` section. This row exists so the sweep's ✓ on 44–88 is not trusted at
face value later, not to add new work.

**Third entry — `analyze/references/figure-standards.md` is not free of the
`manuscript-model` pattern, found running `scripts/check_refs.py --criterion
manuscript-model` (Task 0.5, 2026-09-08) against the whole-file ✓ mark at §3 line
127 ("clean (prohibitions only)"):**

| File | Lines | Class | Finding |
|---|---|---|---|
| `analyze/references/figure-standards.md` | 29 | 1 (prohibition) | "Never `ggsave()` to a file and include it by hand." |
| `analyze/references/figure-standards.md` | 175 | 1 (prohibition) | "`ggsave()` inside a manuscript chunk \| Quarto emits the figure; saving it to disk produces a stale duplicate and breaks Word output" |

Read in full: both lines are prohibition prose — exactly what the sweep's own
"(prohibitions only)" qualifier already says is present. The gap is not in the
sweep's classification (it is right) but in the file: neither line carries a
trailing `<!-- residue:prohibition -->` marker, so `check_refs.py`'s
`MANUSCRIPT_MODEL` regex has no way to distinguish "here is the forbidden
pattern, don't do it" prose from a real instance and flags both. (A third hit at
line 5 — "Nothing is `ggsave()`d to disk" — is the same shape and is covered by
the same fix.) This row exists so the ✓ is not read as "the checker will pass on
this file"; it will not, until the three lines are marked. Recorded here per the
plan's Global Constraint rather than fixed, since Task 0.5/0.6 may not edit
`references/`.

## 12. Counts

| Layer | Files read | Files clean | Residue rows (classes 1–7) | Hook/contract rows |
|---|---|---|---|---|
| agents | 17 | 5 (`writer`, `strategist`, `storyteller`, `theorist-critic`*, `explorer-critic`*) | ≈45 | — |
| skill `SKILL.md` | 18 | 2 (`promote`, `talk`) | ≈60 | — |
| skill sub-files | 60 | 32 | ≈150 | — |
| references | 9 | 2 | ≈30 | — |
| rules | 16 | 3 | ≈40 | — |
| hooks + README | 12 | 4 (code) | — | 14 |
| templates + install | 8 | 3 | ≈12 | — |

\* clean apart from the shared "severity level (from the orchestrator)" line.
