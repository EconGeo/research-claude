# D1 superseded in part: the registry, lifecycle and governance return; the agent does not

**Date:** 2026-09-08 · **Status:** Decided (spec v2 §3, D-1, D-2, D-6, D-9, D-10)

**What changes.** `rules/permissions.md` (now rendered from `rules/registry.yaml`), `rules/lifecycle.md`
and `rules/meta-governance.md` are restored as rewrites against the archived clo-author files
(`~/Research/NAR_settlement_legacy_archive/.claude/rules/`, upstream `hugosantanna/clo-author@d36c408`).
`rules/workflow.md` is not restored: its loop is `skills/pipeline/SKILL.md`, its graph is the registry.
`agents/orchestrator.md` is not restored: a subagent cannot hold an approval gate, so the driver is a skill.

**Why D1 was wrong about the files.** Audit corrections C1–C2 (`docs/audits/2026-09-08_pipeline-audit-findings.md`):
`workflow.md` §3 explicitly supports the coder↔writer re-entry D1 cut it for; `lifecycle.md` is a
handoff-validation protocol, not a graph; the weight set sums to 100 once `CONDITIONAL` is honoured.
Losing `permissions.md` left `quality.md` gating submission on weights that existed nowhere.

**What would invalidate this.** A driver that can hold an approval gate inside a subagent — then
the orchestrator could return as an agent. Nothing in the harness today allows it.
