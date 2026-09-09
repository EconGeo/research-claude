# Review of the Pipeline Repair Design — what the spec misses

**Date:** 2026-09-08 · **Reviewed:** `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (read in full)
**Also read in full:** the audit and its corrections, the D1 decision record, both prior plans, all 18 `skills/*/SKILL.md`,
`agents/{writer,writer-critic,coder,verifier,editor}.md`, `rules/{agents,quality,logging,quarto-empirical,shared-pipeline,
session-handoff,revision,registry-verification-gate}.md`, `apply.sh`, `scripts/{check_fork,check_install}.sh`,
`scripts/audit_graph.py`, `templates/{gitignore,settings.json,bootstrap-pipeline.sh}`, `hooks/{README.md,pre-compact.py,
post-compact-restore.py,session-guard.py}`, the archived clo-author `rules/{permissions,lifecycle,workflow,meta-governance}.md`
and `agents/orchestrator.md` in `~/Research/NAR_settlement_legacy_archive/.claude/`, and the hooks / sub-agents docs at
`code.claude.com` (fetched this session, labelled `per docs:` below).

**Verdict.** The diagnosis is right and the architecture is sound. The spec is not yet the "final" rewrite it is meant to be,
because it repairs the *contract layer* (registry, lifecycle, gates) while leaving the *instruction layer* (skill bodies and
creator agents) in a state where the creators are told to produce what their critics penalise. Five findings would break an
end-to-end run; the rest bite during migration or leave the plan under-specified. Every finding names the file that shows it.

---

## A. Would break an end-to-end run

### A1. Creators are instructed to produce what critics penalise — and no stage rewrites them

The spec's "Structural adaptation" paragraph states the one-manuscript model, but no migration stage rewrites the skill and
agent bodies that still describe clo-author's `scripts/` + `paper/tables/*.tex` + `paper/sections/*.tex` world:

| File | What it still says |
|---|---|
| `skills/analyze/SKILL.md` Step 3 | "tables to `paper/tables/`", "`.tex` tables for LaTeX", "Save scripts to `scripts/R/`", "saveRDS everything" |
| `agents/coder.md` Stage 3 + Project Layout | `scripts/R/00_master.R … 07_tables.R (exports bare tabular)`, "LaTeX via modelsummary — bare `tabular` (INV-13)", outputs to `paper/tables/` |
| `skills/write/SKILL.md` §1, §5, "LaTeX Conventions" | reads `paper/`, scans `paper/tables/`; self-check requires `\label{eq:…}`, `\cite{}` keys in `Bibliography_base.bib`, tables in `paper/tables/`; a whole `\citet{}`/`\citep{}`/`booktabs` section |
| `skills/review/SKILL.md` routing | auto-detect is `.tex` → comprehensive review; **there is no `.qmd` route at all**; Verifier pass/fail is defined "For papers (`.tex`)" |
| `agents/writer-critic.md` | Standalone mode "via `/review [file.tex]`"; "Rmd Mode" as the exception; INV-22 required at lines 41, 62, 82 |
| `agents/verifier.md` checks 2–3 | `Rscript scripts/R/FILENAME.R`; every `\input{}` resolves; tables in `paper/tables/` |

Meanwhile `rules/quarto-empirical.md` ("What the Coder-Critic Checks") deducts −5 per analysis script in `scripts/R/` and −10
per `source()`. So `/analyze` as shipped dispatches a coder that is told to build the thing its critic is told to fail.
`check_fork.sh`'s `latex-residue` pattern (`latexmk|\doublespacing|threeparttable|paper/main\.tex|paper/sections|Emory`)
catches none of the above. **This is a migration stage of its own, and the largest one.** The gate pattern must widen to
at least `paper/tables/`, `paper/figures/`, `scripts/R/`, `\.tex\b` as a manuscript type, `\\cite[tp]?\{`, `\\input\{`,
`\\label\{`, `Bibliography_base`, `results_summary.md`-as-handoff, and the `.tex`-keyed routing in `/review`.

### A2. Every path predicate assumes `manuscript_<project>.qmd` at the project root; half the fleet does not match

Measured this session:

| Project | Manuscript |
|---|---|
| POGM4 (the canary) | `manuscript_quarto_word.qmd` |
| ESG | `manuscript.qmd` |
| zoning2026 | `paper/manuscript.qmd` **and** `paper/manuscript_quarto_pdf.qmd` |
| BRI | none yet |
| NAR_settlement, affordable_housing_2026 | match |

`REQUIRES`/`PRODUCES`/`WRITES`, the render predicate, and `verifier` check 1 all key on the convention. On POGM4 they fail on
day one of Stage 1. The registry needs a per-project manuscript declaration (a `CLAUDE.md` field or `.claude/state/pipeline.json`)
that the driver and scripts resolve, with a gate that refuses to run when it is absent or ambiguous (zoning2026 has two).

### A3. The literature weight has no scorer

Weight set A gives literature 10, but D3 folded `librarian-critic` into a `/lit-position` **self-check**, and `rules/agents.md` §2
forbids self-scoring. The `registry-complete` gate cannot pass an entry whose `QUALITY_WEIGHT` is 10 and whose `CRITIC` is
none. Decide: a literature critic (the superseded plan's own fallback was `/review --lit`), or drop the weight and renormalise
(applied papers then sum to 90 before renormalisation, so the "exactly 100" claim in the spec changes). Also declare where
`data-engineer` scores — the archived registry says "included in code weight, not scored separately".

### A4. Runtime validation is still prose

PRE/POST validation, score aggregation, state updates, three-strikes counting and the `WRITES`-intersection refusal are
described as things the driver *does*. That is the class of instruction that failed silently through six migrations. Make them
executable: one script (`scripts/pipeline.py` with `pre <agent>`, `post <agent>`, `score`, `state …` subcommands), fixture-tested
red then green, called from `/pipeline` via Bash. That forces the registry into a machine-readable form (YAML/JSON, or a
strictly parsed markdown), which the `registry-complete`, `weights-sum` and `registry-authority` gates need anyway.

### A5. The advisory `Stop` hook cannot be seen, and it parses an undocumented format

`per docs:` on exit 0 a `Stop` hook's stdout goes to the debug log only; content reaches Claude only through
`hookSpecificOutput.additionalContext` and the user through `systemMessage`; `{"decision":"block","reason":…}` keeps Claude
working. The spec's "advisory, exit 0" copies `log-reminder.py`, whose visibility was verified by piping payloads and reading
exit codes, never by observing it in a live session. An advisory nobody sees is the failure mode this repo keeps rediscovering.
The superseded plan's hook also greps the transcript JSONL for `Task` tool_use blocks — an undocumented format, and the tool is
now named `Agent` (`per docs:` renamed in 2.1.63, `Task` kept as an alias in settings and agent definitions).

Better: a `SubagentStop` hook (`per docs:` input carries `agent_type`) appends one line per agent completion to
`quality_reports/agent_dispatch.jsonl`. The `Stop` hook reads that log, emits `additionalContext`, and optionally blocks once
(guarded by `stop_hook_active`) when a creator ran without its critic. The same log is the evidence `post <agent>` uses to
prove the critic actually ran, closing the spec's "runtime gap" without a transcript parser. Red-test visibility in a live session.

---

## B. Will bite during migration

### B1. Linking `templates/` and `scripts/` creates untracked symlinks in six repos, and `check_install.sh` cannot see them

`templates/gitignore:399` ignores only `.claude/scripts/prose_number_check.py`; nothing ignores `.claude/templates/*` or
`.claude/scripts/*`. The six repos' `.gitignore` files are seeds (`copy_seed` never overwrites), so the template fix reaches
nobody. `check_install.sh` `LINKED` has no `templates`, and membership (`want`) covers only `prose_number_check.py`. Stage 2
needs: gitignore template + six repo edits, `LINKED`/`want` extended, and red tests for both.

### B2. Root `templates/` means two different things

`templates/` holds shipped pipeline templates *and* project seeds (`gitignore`, `settings.json`, `bootstrap-pipeline.sh`,
`ai-use-log.md`, `data_manifest.md`). Agents also reference **project-level** paths that happen to share the name:
`templates/ai-use-log.md` (seeded to `<project>/templates/`) and `templates/quarto-preamble.tex` (required by
`quarto-empirical.md`'s YAML and shipped by nothing — a new project following the rule cannot render). Split shipped
`templates/` from `seeds/`, seed the preamble, and exempt project-level paths from the D-4 rewrite or it will break them.

### B3. The old gate contradicts the repair, and so do three live files

`check_fork.sh`'s D1 block asserts `rules/{permissions,lifecycle,workflow,meta-governance}.md` and `agents/orchestrator.md` are
absent. Stage 1 turns it red; the spec inverts nothing. `rules/agents.md` §4 ("No phase graph… there is no dependency graph")
and `docs/decisions/2026-09-08_cut-the-orchestration-graph.md` state the opposite of D-2 and must be rewritten and superseded;
`rules/logging.md`'s Pipeline State section names `templates/pipeline-state.json`, which must now exist.

### B4. Restoration source is unnamed, and it is a rewrite, not a vendor

clo-author is no longer a submodule. Sources: GitHub `hugosantanna/clo-author` (reachable, HEAD `d36c408`) and the archive at
`~/Research/NAR_settlement_legacy_archive/.claude/`. The archived `permissions.md` is fully multi-file (`paper/tables/` contains
`.tex`, `paper/main.tex`, `scripts/`, `librarian`, `PHASE`, `PARALLEL_GROUP`), and the spec's registry adds `WRITES`, render
predicates and `CONDITIONAL` renormalisation. Name the commit, and plan it as a rewrite against the archived file.

### B5. Canary mechanics do not work as written

Re-linking POGM4 to a worktree points its symlinks at the worktree path. `bootstrap-pipeline.sh --tip` cannot be used for that
(it runs `git checkout main` in `$RC`, and `main` is already checked out in the primary worktree), so the canary must call
`apply.sh` directly with the worktree as `SCRIPT_DIR`. After merge and worktree removal the links dangle until re-linked. The new
`branch` check FAILs on POGM4 for the whole migration unless `RESEARCH_CLAUDE_ALLOW_BRANCH=1` is set. And the D-D hazard (any
`git checkout` in the shared tree re-points all six papers) is only closed at Stage 7 — move `branch` to Stage 0.

### B6. The render predicate is a full re-run on the canary

POGM4's `CLAUDE.md` sets `execute: cache: false` deliberately. A PRE-dispatch render before every writer dispatch re-runs the whole
analysis. Use freshness (rendered output newer than the `.qmd` and everything in `data/raw/`) as the predicate and render only
when stale; `verifier` checks 1 and 4 already define those semantics.

---

## C. Audit findings the spec does not address

- **F7 — no real-estate journal profiles.** The spec adds `journal-profile-template.md` only. `references/` are seeds copied
  once and, in practice, symlinked to `~/Research/.claude/references/` via `--link-references`, so profiles must land in that
  shared directory as well as the template. `agents/editor.md` opens with "If the profile does not exist, STOP" — every project
  in the fleet stops at `/review --peer`.
- **F8 — hooks.** Four remain unwired; `post-merge.sh` is a git hook listed in the Claude hook table; `hooks/README.md` labels
  `session-guard.py` as `SessionStart` (it is `PreToolUse`). Wiring is invisible to `check_install.sh`. Add a `hooks-wired`
  check that parses `settings.json` for the hooks shipped skills depend on (`session-guard`, `critic-pairing`) and rejects a git
  hook in the Claude table.
- **F6 — INV-22 is still deducted.** `skills/review/config/scoring-rubrics.md:15` (−15 "No claim-source map"),
  `skills/review/templates/manuscript-review-8-categories.md:47`, `agents/writer-critic.md:41,62,82`. The Claim–Evidence
  deductions in the spec must replace these in the rubric files. `clo-author` is still named in three agents, and `/tools
  upgrade` (clones clo-author) and `/tools deploy` (guide site, `guide-writer` deleted) are dead subcommands.
- **`/submit` pairing is asserted, not defined.** `/submit target` still reads "Agent: Orchestrator"; `/submit package` is
  "Coder + Verifier" with no critic. Define: `target` → the skill itself; `package` → coder + coder-critic; `audit`/`final` →
  verifier pass/fail.
- **`/analyze --dual`** dispatches two coders in parallel; under one manuscript that violates the `WRITES` rule the spec
  introduces. Drop it or redefine it.
- **`skills/new-project-ztp`** still tells the user to run `/discover lit` and describes the librarian (open item 1 — fine,
  but `/discover lit` itself still dispatches Librarian → librarian-critic and its `Principles` line names the pair; the
  fix-branch stash `stash@{0}` holds a partial edit).

---

## D. Under-specified

1. **Score semantics.** Which score counts (latest per component), whether writer-critic scores per section or per manuscript
   for the "manuscript 10" component, and whether `pipeline_state.json` or the research journal is authoritative. Pick the
   state file; derive the journal entry from it.
2. **Severity gradient.** `rules/quality.md` §2 is phase-indexed and every critic's Cold-Read Protocol lists "the severity
   level (from the orchestrator)". Phases return via `REQUIRES`; either the driver supplies severity or §2 is retired. Silence
   leaves an unowned input.
3. **`registry-authority` gate** has no detection method. Define it: any `creator → critic` pair or weight number outside the
   registry and `quality.md` is a FAIL, marker-exempt, red-tested.
4. **`path-resolves` gate** needs a resolution table: `.claude/skills/X` → `skills/X` or `submodules/ai-audit/skills/X` or
   `zotpilot-skills/X`; `.claude/references/*` → `references/`; project-level paths exempt; vendored trees WARN. D-4 also
   rewrites the ~44 skill-relative references the addendum found *correct*, so the delta is ~110 references, not 66.
5. **Compaction recovery.** `post-compact-restore.py` surfaces plans and session logs, not `pipeline_state.json`; the success
   criterion "resumes after `/compact`" needs that hook extended. Decide whether the state file is committed (noisy) or ignored
   (coauthor loses state).
6. **`/pipeline` context cost.** A skill body that carries per-agent dispatch prompts for nine stages loads in full on every
   invocation. Keep SKILL.md to the loop and put per-stage dispatch text in `skills/pipeline/references/<stage>.md`, read when
   that stage runs.
7. **Tool naming.** New files should say `Agent`, not `Task`; the alias is documented for settings and agent definitions, not
   for skill `allowed-tools`.

---

## E. The one addition that makes "final" true

A permanent fixture project in the repo (`tests/fixture-project/`: synthetic `data/raw/`, a 200-line manuscript with one
estimation chunk, one `tbl-`, one `fig-`, a bib) that `/pipeline` runs against, with every gate and every `pre`/`post` predicate
red-tested against it. The spec's success criterion "runs end to end on a scratch project" is a one-time smoke test on POGM4;
a fixture makes it a repeatable test that every future change re-runs. Without it the next patch has the same silent-failure
exposure as the last three.

---

## Stage list the implementation plan should carry (delta to the spec's eight)

0. Baseline; gates written failing; **invert the D1 block**; **`branch` check now**; **fixture project**
1. Contracts — as a machine-readable registry + `scripts/pipeline.py`; rewrite `agents.md` §4; supersede the D1 decision record
1b. **Per-project manuscript declaration** and its gate
2. Missing files — plus preamble seed, `templates/` vs `seeds/` split, gitignore template + six repos, `check_install` `LINKED`/`want`
3. Path layer — with the resolution table and the widened residue pattern
3b. **Rewrite the instruction layer** (A1): `/analyze`, `/write`, `/review`, `/submit`, `coder`, `writer-critic`, `verifier`
4. Pairing — including `/submit` definitions, `--dual` decision, literature scorer decision, rubric edits for INV-22 → Claim–Evidence
5. Driver — with the dispatch log, `SubagentStop` hook, recovery hook extension
6. Dangling names — plus `/tools upgrade`/`deploy`, `new-project-ztp`, `/discover lit`
7. Hooks — `hooks-wired` check, README corrections, `post-merge.sh` out of the table
7b. **Journal profiles** in the shared references dir and the template
8. Merge, re-link six (POGM4 first, back off the worktree), lock bump, fixture run green
