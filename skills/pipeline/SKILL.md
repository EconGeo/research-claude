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
  below 80: creator fixes → critic re-scores; `state strike <creator>`; at 3 → escalate to
            registry's ESCALATION_TARGET with a specific question
  approval gate: present the stage summary and the score; wait unless --yes
after the loop: score; "Suggested Learnings" (strikes, escalations, first-pass ≥ 90) per
  .claude/rules/meta-governance.md — suggestions only, user approves, /promote lands
```
Limits: 3 rounds per pair, 5 overall, 2 verification retries (`registry.yaml: limits`).

## `resume`
After `/compact` or a new session: `state show`, `score`, the last three lines of
`quality_reports/agent_dispatch.jsonl`, then `next`. See
`.claude/skills/pipeline/references/recovery.md`.

## Two modes
Orchestrated (this skill) validates dependencies. Standalone (any stage skill invoked directly)
skips `pre` but never skips the critic, and still writes the dispatch log and the state file,
so a later `/pipeline` sees what happened.

## Principles
- Never hand-evaluate a predicate. Never dispatch without `pre`. Never advance without `post`.
- Escalation carries a question, not a disagreement.
- The state file is the truth; the research journal is written from it.
