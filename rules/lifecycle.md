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

**Both halves are one predicate.** `critic-ran` checks the dispatch log *and* the state file, and
it passes only when all three of these hold: the creator has a completion in the log; the paired
critic has a completion strictly after it; and the creator's `COMPONENT` carries a score in
`quality_reports/pipeline_state.json` whose `at` is strictly after that same creator completion.
A score recorded *before* the creator ran reviewed earlier work, so it does not close the round.

The score half deliberately checks only that a fresh score exists, never how high it is. The
quality bar is enforced elsewhere — by the `score` predicates in the *next* agent's `REQUIRES`
and by `score --gate`. A legitimate 0.0 therefore closes the round and then blocks everything
downstream, which is the intended division of labour.

The two halves live in one predicate on purpose. `pipeline.py post` **auto-appends** `critic-ran`
for every agent whose `CRITIC` is not `none`, so no agent can be missing it. The same contract
expressed as a per-agent entry in `PRODUCES` would be hand-maintained and could be omitted for
one agent — which is the shape of the defect that opened this work. The score half is skipped
for any agent whose `COMPONENT` is `none` (there is nothing to score); that skip is keyed on the
component, never on an agent's name, so a new creator without a component inherits it correctly.

**A limitation this does not close.** Two creators may share a `COMPONENT` — as the analysis and
data-engineering creators both do under `code`. A single critic score timestamped after both of
them satisfies `critic-ran` for both, even though it reviewed only one creator's work. A score
entry records who scored, when, and against which report, but never *which creator's output* was
scored, so no timestamp comparison can recover the difference. Closing it properly needs either a
`for:` field naming the creator on the score entry, or a component of its own for the second
creator. Until then: when two creators share a component, treat a passing `post` on the second as
evidence that a critic ran recently, not as evidence that this creator's work was reviewed.

One further consequence is intended, not a limitation. A section-scoped score is recorded under
`sections`, never as the manuscript component, so `post` for the manuscript's creator fails after
a section-only draft — `post` asserts the whole stage is complete and a section draft is
mid-stage. The refusal says so explicitly rather than reporting it as a missing critic.

## Predicate types

| Type | Passes when |
|---|---|
| `path` | the glob (relative to the project root) matches at least `min` files (default 1) |
| `section` | a Markdown heading with that text exists in the file (`file: manuscript` = the declared manuscript) |
| `score` | the latest score for the component in `quality_reports/pipeline_state.json` is ≥ `min`; `component: overall` uses the weighted aggregate |
| `score-if-scored` | the component has **not** been scored yet, **or** its latest score is ≥ `min`. A missing state file fails (absent is not "unscored"). `component: overall` is rejected — the aggregate is derived, so "has been scored" is undefined for it |
| `fresh` | the rendered output is newer than the manuscript and every file under `data/raw/` |
| `render` | `quarto render <file>` exits 0 (the declared manuscript unless `file` is given); **the manuscript is rendered only when stale** |
| `critic-ran` | `quality_reports/agent_dispatch.jsonl` shows the paired critic completing after the creator's last completion, **and** `pipeline_state.json` carries a score for the creator's `COMPONENT` recorded after that same completion. An agent whose `COMPONENT` is `none` is held to the log half only. The three failures — critic never ran, critic ran but scored nothing, score predates the creator — are reported distinctly |
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
Because `critic-ran` compares an `at` from the committed file against one from the local log,
every timestamp either writes is UTC with an explicit `+00:00` offset and fixed width, so string
order is chronological order across machines and across a daylight-saving change. **Anything else
that appends to the dispatch log must use that same format**, or its entries will compare wrong
against the state file.

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
