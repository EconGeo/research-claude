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
