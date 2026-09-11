# Reference: recovery

After `/compact` or in a fresh session, do not guess what already ran — read the state.

## Resume sequence
```
python3 .claude/scripts/pipeline.py state show
python3 .claude/scripts/pipeline.py score
tail -3 quality_reports/agent_dispatch.jsonl
python3 .claude/scripts/pipeline.py next
```
`next` reads the state file and the dispatch log together and names the stage to work on
(see `SKILL.md`, `status`/`next`, for the statuses). An OPEN line is a round this or an earlier
session started and never closed — its critic has not scored since the creator ran — and it is
suggested ahead of anything READY.

## The rule: state file wins over the research journal
`quality_reports/pipeline_state.json` is authoritative. It is committed, so it survives a
`/compact` and travels with the repo; the research journal is a narrative written **from**
it, never the other way round (`.claude/rules/quality.md` §1, `.claude/rules/lifecycle.md`).
If a journal entry claims a stage is done but the state file carries no matching score, or a
score older than the creator's last dispatch-log completion, the state file is what
`post <creator>` checks — trust it, not the prose.

## What "done" means on resume
Within a run, a stage is closed only when `pipeline.py post <creator>` passes: every `PRODUCES`
predicate holds, and (unless the component is `none`) the critic-ran predicate holds — the
critic completed after the creator, and a score for the creator's component was recorded after
that same completion. A section-scoped `/write` score never closes the `write` stage on its own.

For deciding where to start, `next` also treats a component score with **no** logged creator
completion as CLOSED. That is the adopted or cloned case (the log is gitignored; the state file
is committed), documented in `.claude/skills/pipeline/references/adopt.md` and
`.claude/rules/lifecycle.md`. It is not a loophole in `post`: the moment a creator runs, the
stage is OPEN until its critic scores again.

## Blocked state
`state show` also reports `blocked_by`, set by `state set-blocked "<reason>"` when a stage
cannot proceed for a reason outside the creator/critic loop (e.g. missing external data
access). Clear it with `state clear-blocked` once resolved, not by editing the JSON by hand.
