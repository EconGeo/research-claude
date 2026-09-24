---
name: pipeline
description: Drive the research pipeline end to end or from any stage — resolves the manuscript, evaluates REQUIRES/PRODUCES with pipeline.py, dispatches each stage skill's creator→critic pair, holds approval gates, escalates on three strikes, records state, recovers after /compact. Use for "run the pipeline", "what's next", "resume", or to run a stage under validation.
argument-hint: "[run | status | next | resume] [--from <stage>] [--until <stage>] [--yes]"
allowed-tools: Read,Grep,Glob,Write,Edit,Bash,Agent,mcp__zotpilot__*
---

# Pipeline

The driver. It **reads** `.claude/rules/registry.yaml` through `python3 .claude/scripts/pipeline.py`
and never evaluates a predicate itself. Per-stage dispatch text lives in
`.claude/skills/pipeline/references/<stage>.md`, read only when that stage runs.

Stages, in `REQUIRES` order (never by sequence): `setup` → `literature` → `data` → `strategy`
→ `theory` (conditional) → `analyze` → `write` → `review` → `submit`; `talk` parallel, advisory.

## `status` / `next`
```bash
python3 .claude/scripts/pipeline.py manuscript && python3 .claude/scripts/pipeline.py state show && python3 .claude/scripts/pipeline.py score && python3 .claude/scripts/pipeline.py next
```
`next` prints one line per component stage and ends with `next: <component>`. The statuses:
**CLOSED** (its score postdates every logged creator completion — or it has a score and no
completion at all, which is adopted or cloned work), **OPEN** (a creator ran and its critic has
not scored since — the round is unfinished and is suggested first), **READY** (`pre` passes),
**BLOCKED** (with the missing artifact and the skill that produces it), **SKIPPED** (unscored
but behind the furthest stage reached — excluded from `overall`, never suggested, never faked),
**OPTIONAL** (conditional; the user opts in) and **PENDING** (not evaluated — `pre` can render,
and a stage after the one about to be suggested does not get to spend that). Report the table
and the `next:` line. `next` stops here.

Before `run` reaches `theory`, ask once — "Does this paper need a formal theory section?" (the
four paper types in `.claude/skills/strategize/SKILL.md`, theory mode) — and record the answer
in `quality_reports/decisions/theory_opt-in.md`; `--yes` answers no.

Component → stage reference: `literature` → `literature.md`, `data` → `data.md`, `strategy` →
`strategy.md`, `theory` → `theory.md`, `code` → `analyze.md`, `manuscript` → `write.md`,
`referees` → `/review --peer` (see `review.md`), `replication` → `submit.md`. The parallel,
advisory `talk` stage (no component) → `talk.md`.

**A project with existing work and no state file** — a manuscript, an analysis, referee rounds —
is adopted, not restarted: read `.claude/skills/pipeline/references/adopt.md` before `run`. Its
stages are scored by dispatching each critic on the work that exists; nothing is back-filled.

## `run [--from <stage>] [--until <stage>] [--yes]`
```
read .claude/skills/pipeline/references/setup.md and run its driver sequence:
  resolve manuscript (refuse if absent/ambiguous: "declare `manuscript:` in CLAUDE.md")
  ZotPilot check (`mcp__zotpilot__get_index_stats` available, else /new-project-ztp)
  state init (no-op if present); state validate (refuse on INVALID)
start = the stage `pipeline.py next` names (`next: none` → report its table and stop);
        --from <stage> overrides it and re-opens that stage whatever its status
loop over stages from start in REQUIRES order, stop after --until:
  pre <creator>            → FAIL: report missing artifact + producer skill; stop
  conflicts <creator> <…>  → never dispatch two manuscript writers at once
  read references/<stage>.md; dispatch the creator per that file (Agent)
  dispatch the critic per that file; record-score <component> <score> --critic … [--deductions …] --report …
  post <creator>           → FAIL (critic-ran / render / prose-check): re-dispatch or stop
  below 80: the stage skill loops creator → critic and owns the strike for its creator
            (the driver never issues one — `strike` has no round key, so a second call in
            the same round is a second strike); the driver reads the count from `state show`
            and at `limits.rounds_per_pair` escalates to the registry's ESCALATION_TARGET:
            when the target is the user, as an **Option gate** (`.claude/rules/option-gates.md`)
            of 5–10 alternatives drawn from the Escalation block of
            `.claude/skills/pipeline/references/<stage>.md`, `--yes` takes rank 1; when the
            target is an agent, with that block's question
  approval gate: present the stage summary and the score; wait unless --yes
after the loop: score; "Suggested Learnings" (strikes, escalations, first-pass ≥ 90) per
  .claude/rules/meta-governance.md — suggestions only, user approves, /promote lands
```
Limits: 3 rounds per pair, 5 overall, 2 verification retries (`registry.yaml: limits`).

## `resume`
After `/compact` or a new session: `state show`, `score`, the last three lines of
`quality_reports/agent_dispatch.jsonl`, then `pipeline.py next`. See
`.claude/skills/pipeline/references/recovery.md`.

## Two modes
Orchestrated (this skill) validates dependencies. Standalone (any stage skill invoked directly)
skips `pre` but never skips the critic, and still writes the dispatch log and the state file,
so a later `/pipeline` sees what happened.

## Principles
- Never hand-evaluate a predicate. Never dispatch without `pre`. Never advance without `post`.
  Never decide where to start by reading the journal — `pipeline.py next` reads the state.
- Escalation carries a question, not a disagreement.
- The state file is the truth; the research journal is written from it.
