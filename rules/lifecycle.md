# Lifecycle: Handoff Validation

Validation between agents is **executable**, not prose. `python3 .claude/scripts/pipeline.py`
reads `.claude/rules/registry.yaml` and evaluates it; the `/pipeline` skill calls the script and
never evaluates a predicate itself. This file says what the script does so a reader of a linked
project can understand a refusal.

## PRE-dispatch — `pipeline.py pre <agent>`

Evaluates every `REQUIRES` predicate of the agent — all of them, not just up to the first
failure — printing each one's verdict, and for each failure the missing artifact **and the skill
that produces it** (the predicate's `producer`). It exits 1 if any predicate failed, so one run
reports the full list of what is missing. The driver does not dispatch. Standalone skills skip
this step (spec §4, two modes) but nothing else.

## POST-completion — `pipeline.py post <agent>`

Evaluates every `PRODUCES` predicate, then `critic-ran` for any agent whose `CRITIC` is not
`none`. On failure it exits 1 and the driver does not advance or mark the agent complete.
**A creator cannot be marked complete without its critic's completion in the dispatch log and
its critic's score in the state file.** That is the structural fix for the defect that opened
this work.

Both halves are declared, not implied. `critic-ran` covers the dispatch log; the score half is a
`score` predicate on the creator's own component in its `PRODUCES`, carried by every creator whose
`COMPONENT` is a real component. Its threshold is `min: 0` on purpose: the predicate reads
`val is not None and val >= min`, so `min: 0` asserts only that *a score has been recorded at
all* — a legitimate 0.0 satisfies it, an unscored component does not. The quality bar itself is
enforced elsewhere, by the `score` predicates in the *next* agent's `REQUIRES` and by
`score --gate`. A creator whose `COMPONENT` is `none` has nothing to score and carries no such
predicate; `critic-ran` still binds its critic.

Two consequences of that design are intended. A creator that shares a component with another
creator can have this half satisfied by the shared component's score from an earlier round —
`critic-ran` is what independently requires *its* critic to have completed after *its* last
completion, and the two predicates only bind together. And because a section-scoped score is
recorded under `sections` rather than as the manuscript component, `post` for the manuscript's
creator fails after a section-only draft: `post` asserts the stage is complete, and a section
draft is mid-stage.

## Predicate types

| Type | Passes when |
|---|---|
| `path` | the glob (relative to the project root) matches at least `min` files (default 1) |
| `section` | a Markdown heading with that text exists in the file (`file: manuscript` = the declared manuscript) |
| `score` | the latest score for the component in `quality_reports/pipeline_state.json` is ≥ `min`; `component: overall` uses the weighted aggregate |
| `score-if-scored` | the component has **not** been scored yet, **or** its latest score is ≥ `min`. A missing state file fails (absent is not "unscored"). `component: overall` is rejected — the aggregate is derived, so "has been scored" is undefined for it |
| `fresh` | the rendered output is newer than the manuscript and every file under `data/raw/` |
| `render` | `quarto render <file>` exits 0 (the declared manuscript unless `file` is given); **the manuscript is rendered only when stale** |
| `critic-ran` | `quality_reports/agent_dispatch.jsonl` shows the paired critic completing after the creator's last completion |
| `prose-check` | `python3 .claude/scripts/prose_number_check.py <manuscript>` exits 0 |
| `chunk` | at least `min` chunks in the declared manuscript have a `#| label:` matching `label_glob` |
| `any_of` | at least one of the listed predicates passes |

## State — `pipeline.py state <op>`

`init` creates `quality_reports/pipeline_state.json` (schema in `.claude/templates/pipeline-state.json`);
`validate` checks it; `record-score <component> <score> --critic <name> --report <path> [--scope section:<name>]`
records a critic score (latest per component counts; a section-scoped `writer-critic` score is
recorded under `sections`, never as the manuscript component); `strike <creator>` takes one agent
name and increments that creator's strike count, printing the escalation target at three;
`show` prints it. The state file is
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
