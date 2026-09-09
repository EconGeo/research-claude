# Design: Pipeline Repair — One Manuscript, Every Pair, Every Gate

**Date:** 2026-09-08 (v2, rewritten after the full-tree review the same day)
**Status:** Approved (design), all seven rulings given by Drew 2026-09-08; implementation plan not yet written
**Evidence base:**
- `docs/audits/2026-09-08_pipeline-audit-findings.md` — F1–F12, C1–C3 (dependency graph, differential, spine trace)
- `docs/audits/2026-09-08_repair-spec-review.md` — A1–A5, B1–B6, C, D, E (review of v1 of this spec)
- `docs/audits/2026-09-08_full-tree-sweep.md` — line-level evidence for every shipped file
**Supersedes:** v1 of this file; the critic-dispatch plan at
`~/Research/POGM4/quality_reports/plans/2026-09-08_critic-dispatch-and-dangling-agent-refs.md`; and the
"Not restored / accepted loss" rulings in `docs/decisions/2026-09-08_cut-the-orchestration-graph.md` (D1 stands
for the *agent*; the graph, registry and lifecycle return).

---

## 0. The contract this whole design serves

**One Quarto document is the single source of ground truth.** `rules/quarto-empirical.md` is the normative
contract: `manuscript_<project>.qmd` holds all cleaning, estimation, robustness, tables, figures and prose as cached
chunks reading `data/raw/` directly; every prose number is an inline `r` expression; the render is the proof of
internal consistency and `prose_number_check.py` is the proof against typed literals. `rules/quarto-pdf.md` and
`rules/quarto-word.md` are its two output formats and own nothing above rendering mechanics.

**Everything else conforms to that contract or is removed.** The previous fork kept clo-author's functionality by
vendoring its skills wholesale and adding Quarto as an exception mode beside a LaTeX default. The sweep shows
where that leaves the tree: `coder.md` lays out `scripts/R/00_master.R`, `analyze/SKILL.md` writes `.tex` tables
to `paper/tables/`, `drafting-gates.md` refuses to draft Results until `paper/tables/*.tex` exists, and the
coder-critic in `quarto-empirical.md` deducts for a script in `scripts/R/`. The creators are instructed to build
what the critics are instructed to fail. That is the single largest defect and it is invisible to every existing
gate. This design inverts the fork: the contract is the default and only path, every agent, skill, template,
rubric, reference and hook is rewritten to it, and a gate fails on any file that describes another layout.

**What is kept from clo-author is the *shape* of the research process** — a creator and a critic at every step,
declared contracts between steps, validation at every handoff, three-strikes escalation, weighted scoring behind
a submission gate, a learning loop with no autonomous self-modification. What is not kept is any file layout,
build step, output artifact or rubric line that presumes more than one source document.

## 1. Objective

Repair the fork so the pipeline runs end to end under the one-manuscript contract: every stage pairs a creator
with a critic, every handoff is validated by an executable check, every declared contract is gate-enforced, every
path reference resolves, and no shipped file instructs an agent to produce anything the contract forbids.
Restore what the fork dropped without justification; keep what it correctly dropped; preserve everything it added.

## 2. What the audits found (summary; detail in the three audit files)

**Contract layer (F1–F12).** 11 of 17 agents cannot reach files they are told to read; pairing absent at `/write`,
`/revise`, `/submit`; 2 scripts invoked by 12 skills never vendored; 66 dangling path references; 4 deleted agents
named in 60+ places; `quality.md` gates submission on weights that do not exist. Root cause: `permissions.md`
bundled a phase graph (correctly cut) with a declaration registry (collateral damage).

**Instruction layer (review A1; sweep §1–§4).** ~45 residue rows in agents, ~60 in `SKILL.md` files, ~150 in skill
sub-files. Two script scaffolds, a separate results-summary handoff, a drafting gate keyed on `paper/tables/*.tex`,
a `/review` routing table with no `.qmd` route, a verifier that runs `Rscript scripts/R/`, a theorist that emits
three `.tex` side files, a talk scaffold whose every asset path is wrong.

**Rubric layer (sweep §4).** `scoring-rubrics.md` is the pre-Quarto rubric end to end: INV-22 deducted in three
rows, a Librarian-Critic section with eight rows, numbered scripts and RDS saves rewarded, none of the twelve
coder-critic deductions `quarto-empirical.md` defines. `code-review-16-categories.md` fails a correct manuscript on
five categories by construction. `manuscript-review-8-categories.md` deducts for a retired artifact and for a
`csl:` the PDF path is told not to have.

**Reference layer (sweep §5).** `coding-standards-rmd.md` is a whole-file Rmd/`scripts/R`/`main.tex` contract
seeded into every project. `discipline-cards.md` claims eight journals are shipped in `journal-profiles.md`; none
are, including every real-estate journal. `prompt-formatting-core.md` has no consumer. Two HTML comments in
`domain-profile.md` instruct deleted agents.

**Hook layer (sweep §7; `per docs:`).** Three README rows name the wrong event. Three hooks emit on channels the
harness does not surface on exit 0 (`log-reminder`, `post-edit-lint`, `pre-compact` normal path). `lint-scripts.sh`
never reads a `.qmd` and false-flags `booktabs` as an unseeded `boot`. `context-monitor` fires each threshold once
per project, ever. `session-guard` exempts the file that switches it off.

**Install layer (sweep §8).** Linking `templates/` and `scripts/` would create untracked symlinks in six repos;
`check_install.sh` checks neither; root `templates/` mixes shipped files with project seeds; the required
`templates/quarto-preamble.tex` is shipped by nothing; `check_fork.sh` asserts the restored files are absent.

**Three deletions were justified by claims the files contradict** (audit C1–C2): `workflow.md` §3 explicitly
supports the coder↔writer re-entry D1 cut it for; `lifecycle.md` is a handoff-validation protocol, not a graph;
the weight set sums to 100 once `CONDITIONAL` is honoured.

## 3. Decisions

### 3.1 Standing (from v1, unchanged)

| # | Decision |
|---|---|
| D-1 | **Driver is a skill, not an agent.** `per docs:` `AskUserQuestion` is removed from every subagent, so an orchestrator agent cannot hold an approval gate. Seam count: skill 0, agent 1, hybrid 2. The orchestrator's *content* (registry reading, PRE/POST validation, strikes, scoring, dual-critic synthesis, learning loop) survives as what the skill executes |
| D-2 | **Registry returns** as single source of truth, gate-enforced: no other file hardcodes pairing, weights, escalation or produces/requires |
| D-3 | **Weight set (A)** with `CONDITIONAL` renormalisation — see D-15 for the literature component |
| D-4 | **One path rule:** every reference in a shipped file is written relative to the project root, `.claude/`-prefixed; skill-relative references are rewritten too (≈110 rewrites, not 66) |
| D-5 | **Claim–Evidence Table** produced by `writer-critic`, numeric and qualitative claims |
| D-6 | **Not restored:** `orchestrator` as an agent; `working-paper-format.md`; `guide-writer`; `PHASE` (superseded by `REQUIRES`) |

### 3.2 New (from the review and the sweep)

| # | Decision |
|---|---|
| D-7 | **`quarto-empirical.md` is the one contract and has no escape hatch.** No "external fragments", no Rmd mode, no `scripts/R/` reference pipeline, no separate results file, no `.tex` side files. Project-side residue is migrated (§9), never accommodated in the pipeline |
| D-8 | **Per-project manuscript declaration.** A `manuscript:` field in the project's `CLAUDE.md` names the single `.qmd`; the driver, the scripts and every predicate resolve through it; a gate refuses to run when it is absent or names more than one file. The declaration says nothing about layout |
| D-9 | **Lifecycle validation is executable.** `scripts/pipeline.py` implements `pre <agent>`, `post <agent>`, `score`, `state <op>` against a machine-readable registry; the driver calls it, never reasons about it. Red-tested against the fixture (D-12) |
| D-10 | **Registry is machine-readable.** `rules/registry.yaml` is authoritative; `rules/permissions.md` is rendered from it by a script and gate-checked as identical. The YAML is what `pipeline.py`, `check_fork.sh` and the driver read |
| D-11 | **Dispatch is logged by a `SubagentStop` hook** to `quality_reports/agent_dispatch.jsonl` (`per docs:` input carries `agent_type`). POST validation reads the log to prove the critic ran; the `Stop` hook reads it and emits `hookSpecificOutput.additionalContext` (or blocks once, guarded by `stop_hook_active`) when a creator ran without its critic. No transcript parsing |
| D-12 | **A fixture project ships in the repo** (`tests/fixture-project/`: synthetic `data/raw/`, a small manuscript with one estimation chunk, one `tbl-`, one `fig-`, `references.bib`, `templates/quarto-preamble.tex`). Every gate and every `pre`/`post` predicate is red-tested against it; `tests/run_fixture.sh` is the repeatable end-to-end check |
| D-13 | **`templates/` splits into `templates/` (shipped, linked to `.claude/templates/`) and `seeds/` (copied once, project-owned).** A project's own `templates/` directory is project content (`quarto-preamble.tex`, `word-reference.docx`) and is seeded, never linked |
| D-14 | **Every hook emits on a documented channel** (`additionalContext` for Claude, `systemMessage` for the user, exit 2 to block) and every README row matches its hook's event. `post-merge.sh` leaves the Claude hook table. `check_install.sh` gains `hooks-wired` |
| D-15 | **Literature keeps its weight (10) and gains an independent critic, `lit-critic`.** D3 stands for the collector: the librarian was WebSearch-first and stays deleted; `/lit-position` over ZotPilot collects. Its critic was collateral damage. `lit-critic` never searches or collects; it cold-reads `annotated_bibliography.md`, `frontier_map.md` and `positioning.md`, checks coverage against the local Zotero index (`per docs:` an agent file may declare `mcpServers`, so it can query ZotPilot), scores the six categories as a rubric, and escalates to the User on strike three. Dispatched by `/lit-position` after Step 5; the Step 6 self-check becomes the creator's pre-flight, not the score. Roster 18. The D3 decision record gets an addendum. **Ruled 2026-09-08 (R-1 confirmed).** The earlier "drop the weight" recommendation was withdrawn because the only pre-strategy check of search coverage was a self-check, and the referees' Literature Positioning dimension tests the manuscript's positioning paragraph after strategy, code and draft have already been built on the search |
| D-16 | **Severity gradient retired** (ruled 2026-09-08). `quality.md` §2 is phase-indexed and supplied by nobody; each critic carries its own rubric; the Cold-Read "severity level (from the orchestrator)" line is deleted from six critics. Reversible if the driver ever supplies it |
| D-17 | **`/analyze --dual` is dropped** (ruled 2026-09-08); `/review --replicate` writes to `explorations/`, never the manuscript. Two coders cannot share one manuscript under `WRITES` |
| D-18 | **The HTML dashboard / HTML report layer is retired** (ruled 2026-09-08): `/dashboard`, `/tools dashboard`, `rules/html-dashboard.md`, every `generate_*` invocation, the checkpoint refresh step. Two scripts and the stylesheet are absent, two files name the output differently, the state file and research journal cover pipeline state |
| D-19 | **Theory lives in the manuscript.** `theorist` writes a `# Theory` section and an appendix of proofs into the `.qmd` using Quarto theorem environments (`::: {#thm-…}`), plus `quality_reports/theory/<project>/theory_memo.md` and `notation_glossary.md`. No `.tex` side files |
| D-20 | **Talks reuse manuscript output through a defined source.** Preferred: Quarto `embed` of manuscript chunks from `talks/*.qmd`; fallback: the manuscript keeps rendered figures under `manuscript_<project>_files/` and the talk includes them. `unverified:` whether `embed` works from a `.qmd` source in the installed Quarto — settled on the fixture before the storyteller is rewritten (ruled 2026-09-08: test first, fall back) |
| D-21 | **Rmd mode is retired everywhere** (ruled 2026-09-08): `coding-standards-rmd.md`, `writer-critic` and `coder-critic` Rmd sections, `rmd-preamble.tex` references. No project uses it and no rule documents it |
| D-22 | **Explorations are `.qmd` files** in `explorations/` (ruled 2026-09-08); graduation moves chunks into the manuscript. `content-standards.md`'s `R/`/`scripts/`/`output/` layout and the two absent README templates go |
| D-23 | **`/tools upgrade` and `/tools deploy` are deleted** (clo-author release path that would delete every symlink; `guide/` site that no longer exists). `/tools compile` alias in the description goes; `/tools render` stays |
| D-24 | **Orphans are deleted, not repaired:** `references/prompt-formatting-core.md` (no consumer), `references/audit-pet-peeves.md` reference (pools live in `editor.md`), the `Librarian-Critic` rubric section, `templates/cover-letter.tex` (converted to `.qmd` like `response-letter.qmd`) |
| D-25 | **`Agent`, not `Task`.** New files use the current tool name; existing `allowed-tools` lines are updated. `per docs:` `Task` remains an alias in settings and agent definitions |

## 4. Architecture

**Driver:** `/pipeline`, one skill in the main session with `Agent`. Loop, dispatch, approval gates, escalation,
recovery. It reads `rules/registry.yaml` through `scripts/pipeline.py`; it never hand-evaluates a predicate.
`SKILL.md` carries the loop only; per-stage dispatch text lives in `skills/pipeline/references/<stage>.md`, read
when that stage runs, so the skill body stays small.

| Layer | Owns | File |
|---|---|---|
| Contract | one-manuscript model, caching, write gate, coder-critic deductions | `rules/quarto-empirical.md` (+ `quarto-pdf.md`, `quarto-word.md`) |
| Registry | per-agent declarations | `rules/registry.yaml` → rendered `rules/permissions.md` |
| Lifecycle | PRE/POST predicates, state, score | `scripts/pipeline.py`, `rules/lifecycle.md` (prose description of what the script does) |
| Driver | loop, dispatch, gates, escalation, recovery | `skills/pipeline/SKILL.md` + `references/` |
| Pairing | creator→critic, strikes, separation of powers, dispatch-ownership table | `rules/agents.md` |
| Scoring | weights, `CONDITIONAL`, thresholds | `rules/quality.md` |
| Governance | learning promotion, no autonomous self-modification | `rules/meta-governance.md` (restored, de-Emoried) |
| State | machine-readable progress | `quality_reports/pipeline_state.json` (schema in `templates/pipeline-state.json`) |
| Dispatch log | every subagent completion | `quality_reports/agent_dispatch.jsonl` (written by `hooks/dispatch-log.py`) |

**Spine.** `/discover interview` → `/lit-position` → `/discover data` → `/strategize` → `/analyze` → `/write` →
`/review` → `/submit`, with `/talk` parallel and advisory. Phases activate by `REQUIRES`, never by sequence;
re-entry permitted everywhere except Submission.

**Two modes.** Orchestrated (`/pipeline` drives, validates, pauses) and Standalone (any skill invoked directly
skips *dependency* checks). Standalone never skips critic dispatch, and standalone skills still write the dispatch
log and the state file, so a later `/pipeline` run sees what happened.

## 5. The registry contract

Seven fields per agent: `REQUIRES`, `PRODUCES`, `CRITIC`, `ESCALATION_TARGET`, `QUALITY_WEIGHT`, `CONDITIONAL`,
`WRITES`. `PARALLEL_GROUP` is documentation only; `PHASE` is dropped.

**Predicate types** (all implemented in `pipeline.py`):

| Type | Meaning |
|---|---|
| `path` | Glob relative to project root resolves to ≥ 1 file |
| `section` | Heading present in the declared manuscript |
| `score` | Latest critic score for the component in `pipeline_state.json` ≥ threshold |
| `fresh` | Rendered output newer than the manuscript and every file under `data/raw/`; **render only when stale**. A PRE-dispatch full render is a full re-run on any project with `cache: false` |
| `render` | `quarto render <declared manuscript>` exits 0 and named artifacts exist — used at POST for coder/data-engineer and at `/submit`, not at every PRE |
| `critic-ran` | `agent_dispatch.jsonl` shows the paired critic completed after the creator's last completion |

**PRODUCES under one manuscript.**

| Agent | PRODUCES |
|---|---|
| `/lit-position` (creator role) | `quality_reports/literature/<project>/{annotated_bibliography,frontier_map,positioning}.md`; CRITIC `lit-critic`; weight 10 |
| explorer | `quality_reports/data-assessment/<project>/{data_sources,data_dictionary,access_instructions}.md` |
| strategist | `quality_reports/strategy/<project>/strategy_memo.md` with sections Estimand, Specification, Assumptions, Robustness Plan, Threats |
| theorist | `# Theory` section + proofs appendix in the manuscript; `quality_reports/theory/<project>/{theory_memo,notation_glossary}.md` |
| data-engineer | data-wrangling chunks (`cache.extra` on every raw file) and `data/raw/data_manifest.md` rows; `render` clean |
| coder | estimation, robustness, `tbl-` and `fig-` chunks; `render` clean; `prose_number_check.py` exit 0 |
| writer | named sections in the manuscript; `render` clean; `prose_number_check.py` exit 0 |
| editor / referees | `quality_reports/peer_review_<manuscript>/{desk_review,referee_domain,referee_methods,editorial_decision}.md` |
| storyteller | `talks/<format>_talk.qmd`; `quarto render` exit 0 |
| verifier | `quality_reports/verification_report.md` |

**`WRITES`.** coder, data-engineer, theorist and writer all write the manuscript; the driver refuses concurrent
dispatch when write targets intersect. That serialises the manuscript writers by construction and is why D-17 drops
`--dual`.

**Manuscript resolution (D-8).** `pipeline.py` reads `manuscript:` from the project `CLAUDE.md`; every predicate,
`verifier` check, hook and skill instruction that says `manuscript_<project>.qmd` means "the declared manuscript".
The convention `manuscript_<project>.qmd` remains what a new project is scaffolded with.

**Weights (set A, R-1 confirmed).** literature 10, data 10, strategy 25, theory 20 `CONDITIONAL`, code 15, manuscript 10,
referees 12.5 + 12.5, replication 5 — exactly 100 for an applied paper, 120 renormalised with theory. Declared in
`rules/quality.md`, the file that consumes them, and mirrored in the registry; the `weights-sum` gate fails if the two disagree.

## 6. Handoff validation and state

`pipeline.py pre <agent>` evaluates every `REQUIRES` predicate; on failure it prints the missing artifact and the
skill that produces it and exits non-zero. The driver does not dispatch. `pipeline.py post <agent>` evaluates
`PRODUCES`, `render`/`fresh` where declared, and `critic-ran`; on failure it does not advance. A creator cannot be
marked complete without its critic's score — the structural fix for the defect that opened this work.

`pipeline_state.json` is authoritative for scores and progress; the research journal entry is written from it,
never the other way round. Latest score per component counts; `writer-critic` scores the whole manuscript at
`/review` and per section at `/write`, and the aggregate uses the latest whole-manuscript score. The schema ships as
`templates/pipeline-state.json`; `pipeline.py state validate` is a gate. `post-compact-restore.py` surfaces the
state file first, then plans and logs. The state file is committed (it is replication provenance); the dispatch
log is gitignored (it is session mechanics).

**Limits:** 3 rounds per pair, 5 overall, 2 verification retries. Escalation targets come from the registry.

## 7. Claim–Evidence Table

Unchanged from v1 in intent. Produced by `writer-critic` at every review, recorded to
`quality_reports/reviews/claim_evidence_<project>_<date>.md`, covering numeric and qualitative claims, with
CONTRADICTED −25, UNSUPPORTED −15, OVERSTATED −10, UNVERIFIABLE −5. What v1 did not say: the deductions replace the
INV-22 rows in `review/config/scoring-rubrics.md:15,28,29` and `manuscript-review-8-categories.md:47–51,204–207`,
and `writer-critic.md:41,62,82` stop requiring the retired map. INV-11 stays mechanical; the table is the
interpretation check.

## 8. The instruction-layer rewrite (the largest stage)

Every row below is line-cited in the sweep. The rule for each file: describe the one-manuscript path only; name
`.claude/`-prefixed paths only; name no deleted thing; cite an invariant only for what it currently says.

| File | Rewrite |
|---|---|
| `agents/coder.md` | Stages 0–3 become chunk work in the manuscript (wrangling chunk with `cache.extra`, estimation chunks with `dependson`, `tbl-`/`fig-` chunks); Project Layout and Output Location sections deleted; naming map lives in the `setup` chunk comment; no `results_summary.md` |
| `agents/data-engineer.md` | cleaning is a cached chunk on raw files; codebook goes to `data/raw/data_manifest.md` rows + `quality_reports/data-assessment/`; no `.rds`, no `paper/figures/`, no LaTeX summary table |
| `agents/theorist.md` | D-19 outputs; `references.bib` |
| `agents/verifier.md` | check 2 = chunks execute (render), 3 = `@fig-`/`@tbl-`/`@sec-` and citations resolve, 4 = `fresh`; submission checks 5–10 rewritten for a package that is the `.qmd`, `references.bib`, `templates/`, `data/raw/data_manifest.md`, `scripts/acquire/`, `renv.lock`, README; "master script" = `quarto render` |
| `agents/writer-critic.md` | description, standalone mode and Rmd mode rewritten to `.qmd`-only; INV-22 lines removed; severity line removed; strike 3 → User |
| `agents/coder-critic.md` | Quarto Empirical Mode becomes the only mode; Rmd Mode deleted; standalone mode reviews the manuscript's chunks or a file under `scripts/acquire/` or `explorations/` |
| `agents/{explorer,storyteller,strategist,theorist}-critic.md` | severity line removed |
| `agents/explorer.md` | "Librarian's bibliography" → `/lit-position` output |
| `agents/editor.md`, `domain-referee.md`, `methods-referee.md` | `/review-paper` → `/review`; `/audit-reproducibility` → `/submit audit`; `domain-reviewer.md` sibling reference removed; clo-author release notes removed, credit comments kept |
| `agents/storyteller.md` | D-20 figure source; `talks/custom.scss` shipped in `skills/talk/templates/` or the theme line dropped |
| `skills/analyze/SKILL.md` | Steps 2–3 dispatch data-engineer and coder into the manuscript; Step 4 is the twelve `quarto-empirical.md` deductions; `--dual` removed (D-17); `generate_*` removed; templates table lists only what survives |
| `skills/analyze/templates/{r,python}-script-structure.*` | replaced by `chunk-structure.md` (setup chunk, wrangling chunk, estimation chunk, `tbl-`, `fig-` patterns) |
| `skills/analyze/templates/{results-summary,paper-to-code-map,pre-code-report}.md` | results-summary deleted; naming map moves to the setup-chunk comment; pre-code report lists chunk labels, not filenames |
| `skills/analyze/gotchas.md`, `references/table-standards.md` | bare-tabular advice deleted; `booktabs = TRUE` in the canonical example; INV-12/13 cited correctly |
| `skills/write/SKILL.md` | context step reads the manuscript, `references.bib`, `quality_reports/strategy/`; self-check in Quarto terms (`{#eq-}`, `@key`, `@tbl-`); "LaTeX Conventions" section deleted; claim-source item deleted; **writer-critic dispatched on every mode that touches prose**, `style-guide` alone exempt; style corpus accepts `.qmd`/`.docx`/`.pdf` |
| `skills/write/templates/drafting-gates.md` | gate = estimation chunk present and `render` clean, never file existence |
| `skills/write/gotchas.md`, `templates/style-extraction-protocol.md`, `references/notation-protocol.md` | `@key`, `references.bib`, setup-chunk naming map |
| `skills/review/SKILL.md` | auto-detect: `.qmd` at the declared manuscript → comprehensive; `scripts/acquire/*` or `explorations/*` → code review; `talks/*.qmd` → talk review; Verifier pass/fail for `.qmd`; `generate_*` removed |
| `skills/review/config/scoring-rubrics.md` | INV-22 rows → Claim–Evidence rows; Librarian-Critic section deleted; Coder-Critic block = the twelve `quarto-empirical.md` deductions + numerical discipline; "numbered scripts", "RDS saves", "scripts don't run" rows replaced by render/cache rows; "document class", "overfull hbox" removed |
| `skills/review/templates/code-review-16-categories.md` | categories 5, 6, 11, 12, 13 rewritten for chunks (setup chunk, chunk labels, `fig-cap`, `booktabs = TRUE`, cache DAG); INV-11/23/24 added |
| `skills/review/templates/manuscript-review-8-categories.md` | INV-22 section → Claim–Evidence; `csl:` row → "PDF path has no top-level `csl:`; Word block has one"; standalone via `.qmd`; headings "Format" and "Render" |
| `skills/review/templates/theory-review-4-phases.md` | `templates/quarto-preamble.tex`; `references.bib`; "renders" |
| `skills/submit/SKILL.md` | `target` performed by the skill; `package` → coder + coder-critic; `audit`/`final` → verifier; `generate_*` removed; cover letter `.qmd` |
| `skills/submit/templates/{audit-10-checks,replication-readme,submission-checklist}.md` | package = the one manuscript + inputs; `@fig-`/`@tbl-`; INV-9/10/14 phrased as the invariants read today; "check 11" → 4b |
| `skills/revise/SKILL.md` | Writer and Coder each followed by their critic; `response-letter.qmd` pointer |
| `skills/talk/templates/quarto-scaffold.qmd`, `references/slide-design-principles.md` | `../references.bib`; no `fig-format: pdf`; D-20 figure source; `. . .` / `{.fragment}` not `\pause`/`\only<>` |
| `skills/discover/SKILL.md`, `gotchas.md` | `lit` mode → pointer to `/lit-position`; Principles line; `generate_*` removed |
| `skills/strategize/SKILL.md` | theory outputs per D-19; `generate_*` removed |
| `skills/tools/SKILL.md`, `gotchas.md` | D-23; lint default `scripts/acquire/` + `explorations/`; `references.bib`; `Agent` |
| `skills/checkpoint/SKILL.md`, `gotchas.md`, `templates/memory-entry-types.md` | dashboard step removed (D-18); pipeline-state line rewritten for the real file; Obsidian tool names aligned with `obsidian-digest-sync`; "within clo-author" → research-claude; HANDOFF.md regeneration per `session-handoff.md`; example identity removed |
| `skills/freeze/SKILL.md`, `careful/SKILL.md` | examples and pattern tables match `session-guard.py`; no override claim |
| `skills/new-project-ztp/SKILL.md` | librarian → `/lit-position`; `references.bib` |
| `skills/lit-position/SKILL.md` | `zotpilot-skills/` → `.claude/skills/ztp-*`; Step 6 becomes the creator pre-flight; **dispatch `lit-critic`** after Step 5, three strikes → User |
| `agents/lit-critic.md` (new) | cold-read critic for the three literature artifacts; six-category rubric with deductions in `review/config/scoring-rubrics.md` (replacing the deleted Librarian-Critic section, not restoring it by name); `mcpServers: zotpilot` for coverage queries; never collects |
| `references/coding-standards-rmd.md` | deleted (D-21) |
| `references/coding-standards-r.md`, `-julia.md` | `functions/` section → helper functions in the setup chunk or `scripts/acquire/`; `source()` row → prohibited in chunks; PGF path removed |
| `references/discipline-cards.md` | consumers → `/discover interview`, `/discover ideate`, `/strategize pap`, `/review --peer`; "shipped" claims true or removed; `audit-pet-peeves` → `editor.md` pools; JHE collision fixed |
| `references/domain-profile.md` | two HTML comments rewritten (`/submit target`, `/lit-position`) |
| `references/journal-profiles.md` | + REE, JREFE, JRER, JREPM, Journal of Housing Economics, APSR, AJPS, JOP profiles via `templates/journal-profile-template.md`; also landed in `~/Research/.claude/references/` (§9) |
| `rules/content-invariants.md` | INV-9 no top-level `csl:`; INV-18 rewritten (code writes nothing outside `_cache`/`_files`); INV-23/24 meanings reconciled with `data-manifest.md`; "enforced by" column true for each row |
| `rules/data-manifest.md` | INV numbers reconciled; write-gate claim corrected; zoning example generalised |
| `rules/content-standards.md` | D-22 explorations; `master_supporting_docs/` documented as a project upload dir |
| `rules/quarto-word.md` | `csl` YAML and prose agree; `word-reference.docx` seeded or documented as project-created |
| `rules/quarto-pdf.md` / `quarto-empirical.md` | `templates/quarto-preamble.tex` seeded (D-13) |
| `rules/agents.md` | §1 enforcement rewritten; librarian row and "Beamer" gone; §3 actor = dispatching skill; §4 replaced by the dispatch-ownership table and a pointer to the registry |
| `rules/quality.md` | weights table; §2 per D-16 |
| `rules/logging.md` | Pipeline State section rewritten for the real schema and the dispatch log; Learning Loop → `meta-governance.md` |
| `rules/revision.md`, `registry-verification-gate.md` | actor nouns reassigned; "registry" disambiguated |
| `rules/html-dashboard.md`, `skills/dashboard/` | D-18 |
| `README.md` | 11 references rewritten |
| `zotpilot-skills/seed-papers/SKILL.md` | fixed upstream in `EconGeo/ZotPilot`, re-vendored |

## 9. Reference, seed and legacy-project layer

**Seeds vs shipped (D-13).** `seeds/`: `gitignore`, `settings.json`, `bootstrap-pipeline.sh`, `ai-use-log.md`,
`data_manifest.md`, `quarto-preamble.tex`, `word-reference.docx` (or documented as project-created), `pipeline-state.json`
schema copy. `templates/`: `journal-profile-template.md`, `pipeline-state.json`, and anything an agent reads by a
`.claude/templates/` path. `apply.sh` links `templates/` and `scripts/` into `.claude/`; the gitignore seed ignores
`.claude/templates/*` and `.claude/scripts/*`; the six repos' gitignores are edited by hand (seeds never overwrite).

**References are seeds and, in practice, symlinks to `~/Research/.claude/references/`** via `--link-references`.
Journal profiles and discipline-card corrections therefore land in that shared directory as well as in the template,
or every existing project keeps calibrating against the old file.

**Legacy-project residue (migrated, never accommodated — Drew, 2026-09-08).**

| Repo | Items, each done before the repo is re-linked |
|---|---|
| POGM4 (canary) | declare `manuscript: manuscript_quarto_word.qmd`; delete or archive `scripts/R/` reference pipeline; remove `.claude/WORKFLOW_QUICK_REF.md`, `.claude/commands/`; `cache: false` stays as a declared deviation in `CLAUDE.md` (the `fresh` predicate makes it cheap) |
| zoning2026 | declare `manuscript: paper/manuscript.qmd`; delete `paper/manuscript_quarto_pdf.qmd`; fold `paper/tables/*.tex` fragments into `tbl-` chunks; delete `scripts/`; clear 41 literals |
| affordable_housing_2026 | replace the hand-written `pipeline_state.json` with a schema-valid one generated by the first `/pipeline` run |
| ESG | declare `manuscript: manuscript.qmd`; clear 14 literals |
| NAR_settlement | declare; branch `phase1-event-study`; clear 2 literals |
| BRI | declare once a manuscript exists; `/pipeline` refuses until then |
| all six | gitignore additions; `settings.json` wiring for `dispatch-log.py` and `critic-pairing.py`; `hooks-wired` green |

## 10. Rulings

| # | Question | Ruling (Drew, 2026-09-08) |
|---|---|---|
| R-1 (D-15) | Literature: critic or drop the weight? | **Keep weight 10; add `lit-critic`** (D-15) |
| R-2 (D-16) | Severity gradient | **Retire** |
| R-3 (D-17) | `--dual` | **Drop** |
| R-4 (D-18) | HTML dashboard / report layer | **Retire** |
| R-5 (D-20) | Talk figure source | **Test `embed` on the fixture first; fall back to `manuscript_<project>_files/`** |
| R-6 (D-21/D-22) | Rmd mode; `R/`+`scripts/` exploration layout | **Retire both** |
| R-7 | Baseline wiring | **Wire `context-monitor.py` after the per-session fix; `protect-files.sh` stays opt-in** |

## 11. Enforcement

**Every gate is red-tested against the fixture** before its green is trusted. Three vacuous-green checks were
found in one day; this design assumes a fourth is waiting.

`check_fork.sh` (template gate):

| Criterion | Fails when |
|---|---|
| `latex-residue` (widened) | any shipped file matches `paper/tables\|paper/figures\|paper/sections\|main\.tex\|scripts/R/\|00_master\|\\cite[tp]?\{\|\\input\{\|\\label\{\|\\ref\{\|\\cref\|latexmk\|threeparttable\|\\doublespacing\|Bibliography_base\|results_summary\.md\|\.Rmd\|bookdown\|\\pause\|\\only<`, outside a line marked `<!-- residue:prohibition -->` or `<!-- residue:historical -->` |
| `manuscript-model` | any shipped file instructs producing a file the contract forbids (`ggsave(`, `saveRDS(` outside `scripts/acquire`, `writeLines(` to `.tex`, `dir.create("paper`) |
| `deleted-things` (9a/9b generalised, two exemption tiers) | a shipped file names `orchestrator`, `librarian(-critic)`, `guide-writer`, `rmd-coder-critic`, `domain-reviewer`, an absent skill (§11 list in the sweep), a `generate_*` script, `guide/`, an instruction to fetch from clo-author, or INV-22 as live |
| `inv-refs` | an `INV-NN` citation names an invariant that does not exist or is `RETIRED`, outside its definition |
| `path-resolves` (D-4) | a `.claude/…` path fails the resolution table: `skills/X` → `skills/X` \| `submodules/ai-audit/skills/X` \| `zotpilot-skills/X`; `agents/X` likewise; `rules/X` → `rules/X` \| `submodules/ai-audit/rules/X`; `references/X` → `references/X`; `templates/X` → `templates/X`; `scripts/X` → `scripts/X`; project-level paths (`data/`, `quality_reports/`, `talks/`, `explorations/`, `scripts/acquire/`, the project's own `templates/`) exempt; vendored trees WARN |
| `registry-complete` | any agent lacks a field, or `CRITIC` is `none` with a non-zero weight (`/lit-position` therefore needs `lit-critic` on the roster for the literature weight to pass) |
| `registry-authority` | a `creator → critic` pair or a weight number appears outside `registry.yaml`, `quality.md` and the rendered `permissions.md` |
| `registry-rendered` | `permissions.md` differs from the render of `registry.yaml` |
| `weights-sum` | non-`CONDITIONAL` weights ≠ 100, or `quality.md` ≠ registry |
| `hooks-readme` | a README row's event ≠ the hook's docstring event; a git hook in the Claude table |
| `tool-name` | `Task` in any `allowed-tools` or `tools` line |
| `skill-refs` | a `/name` in a shipped file names no skill under `skills/`, `submodules/ai-audit/skills/`, `zotpilot-skills/` |
| `seeds-complete` | `seeds/quarto-preamble.tex` absent while any rule requires it |
| `fixture` | `tests/run_fixture.sh` fails |
| existing | `project-identity`, `project-nouns`, `cc-*-half`, `course-leak`, structural criteria; the D1 block inverted to assert presence |

`check_install.sh` (project gate): existing six checks plus `branch` (FAIL when the shared checkout is on neither
`main` nor a detached lock SHA; `RESEARCH_CLAUDE_ALLOW_BRANCH=1` → named WARN), `scripts-linked`, `templates-linked`,
`hooks-wired` (parses `settings.json` for `session-guard`, `dispatch-log`, `critic-pairing`; rejects a git hook),
`manuscript-declared` (D-8), `state-valid` (schema), `gitignore-covers` (`.claude/{scripts,templates}/*`).

**Hook layer (D-14).** `log-reminder.py` → `additionalContext`; `post-edit-lint.sh` → `additionalContext` with the lint
output; `pre-compact.py` normal path → `systemMessage`; `lint-scripts.sh` reads `.qmd` chunks (extracted by a small
Python helper) and matches `\bboot\(`; `context-monitor.py` keys thresholds per session; `session-guard.py` does not
exempt `.claude/state/session-guards.json`; `verify-reminder.py` drops `.tex`; README rows corrected; `post-merge.sh`
moved out of the table (installed to `.git/hooks/` by `apply.sh` or deleted). New: `hooks/dispatch-log.py`
(`SubagentStop`), `hooks/critic-pairing.py` (`Stop`, reads the log, `additionalContext`, optional one-shot block).
Every hook is tested by piping a real payload **and** by observing its output in a live session once.

## 12. Migration

Worktree development; the shared checkout stays on `main`; POGM4 is the single canary. The canary is re-linked
by calling the worktree's `apply.sh` directly (not `bootstrap-pipeline.sh --tip`, which would `git checkout main`
in a checkout where `main` is already held by the primary worktree). `check_install.sh` runs on POGM4 with
`RESEARCH_CLAUDE_ALLOW_BRANCH=1` for the duration. After merge, POGM4 is re-linked to the shared checkout before
the worktree is removed, or its links dangle.

| Stage | Content |
|---|---|
| 0 | Baseline snapshot; **fixture project** (D-12); all new gates written failing; **D1 block inverted; `branch` check now**; `fix/critic-dispatch` 9a/9b and `stash@{0}` folded in or discarded |
| 1 | Contracts: `registry.yaml` + renderer + `permissions.md`; `lifecycle.md`; `quality.md` weights (R-1); `meta-governance.md`; `agents.md` §4 → dispatch table; supersede the D1 decision record; `scripts/pipeline.py` with fixture tests |
| 1b | **Manuscript declaration** (D-8) and `manuscript-declared` gate; POGM4 declares |
| 2 | Missing and mis-homed files: `templates/` vs `seeds/` split (D-13); preamble seed; `journal-profile-template.md`; `pipeline-state.json` schema; gitignore seed + six repo edits; `apply.sh` links `templates/` and `scripts/`; `check_install` `LINKED`/`want`/`templates-linked`/`scripts-linked`/`gitignore-covers` |
| 3 | Path layer: every reference rewritten to D-4 (≈110); `path-resolves` with the resolution table; `revise` pointer; `lit-position` path |
| 3b | **Instruction layer** (§8): agents, `SKILL.md` files, skill sub-files, references, rules — largest delta; the widened `latex-residue`, `manuscript-model`, `inv-refs`, `skill-refs` gates go green here and not before |
| 4 | Pairing: `/write`, `/revise`, `/submit`, `/lit-position` dispatch; `agents/lit-critic.md`; rubric rewrite (§7, §8); Claim–Evidence Table; D-15/16/17 applied |
| 5 | Driver: `/pipeline` + `references/<stage>.md`; `dispatch-log.py`; `critic-pairing.py`; `post-compact-restore.py` reads the state file; recovery tested on the fixture through a `/compact` |
| 6 | Deleted-things sweep: `deleted-things` gate green; `seed-papers` upstream + re-vendor; README; D-18/23/24 deletions |
| 7 | Hooks: D-14 fixes, README rows, `hooks-wired`, wiring in `seeds/settings.json` and six repos (R-7) |
| 7b | Journal profiles and discipline cards in the template and in `~/Research/.claude/references/` |
| 8 | Legacy-project migration (§9) one repo at a time, POGM4 first, each re-linked after its residue is cleared; merge; re-link six to the shared checkout; lock bump; `tests/run_fixture.sh` green on `main` |

**Stop conditions:** an unintended graph delta; a gate green without a prior red; a smoke test passing while the
critic-pairing hook fires; a stage needing a file a later stage builds; a residue row found that the sweep did not
list (the sweep is the expectation; the tree is the truth).

## 13. Success criteria

- `check_fork.sh` exits 0 with every criterion red-tested against the fixture
- `check_install.sh --all` passes on six repos, `hooks-wired` and `manuscript-declared` included
- `audit_graph.py` reports 0 dangling path references and 0 agents named but absent
- `grep -rE` for every pattern in the widened `latex-residue` set returns only marked prohibitions and historical lines
- `tests/run_fixture.sh` runs `/pipeline` on the fixture end to end: every predicate evaluated by `pipeline.py`, every creator followed by its critic in `agent_dispatch.jsonl`, a Claim–Evidence Table produced, state file schema-valid, resumes after `/compact`
- `/write abstract` on POGM4 produces a `writer-critic` score and a Claim–Evidence Table before the draft
- 11 of 17 agents reaching unresolvable files becomes 0 of 18 (roster + `lit-critic`); 0 shipped files instruct a forbidden artifact
- Six repos declare a manuscript; zoning2026 has one manuscript and no `.tex` fragments; no repo has a `scripts/R/` analysis tree

## 14. Open items for the implementation plan

1. `new-project-ztp` — fold into `/pipeline` as its setup step, or keep as a skill `/pipeline` calls (unchanged from v1)
2. `/promote` vs `meta-governance.md` learning promotion — verify one mechanism, not two
3. `obsidian-digest-sync` `journal_digest/` vs installed `journal-digest/` — `unverified:` which is the runtime directory; read the submodule before touching it
4. Quarto `embed` from a `.qmd` source (R-5) — test on the fixture before rewriting the storyteller
5. Whether `pipeline_state.json` is committed (recommended) and how `/checkpoint` reads it for the staleness sweep in `session-handoff.md`
6. The `scripts/` copy-to-link conversion (F13) sequenced with Stage 2
