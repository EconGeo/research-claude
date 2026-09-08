# Design: Pipeline Repair — Restore the Contract, Drive from a Skill

**Date:** 2026-09-08
**Status:** Approved (design); implementation plan not yet written
**Evidence base:** `docs/audits/2026-09-08_pipeline-audit-findings.md` (12 findings + 3 corrections)
**Supersedes:** the critic-dispatch plan at `~/Research/POGM4/quality_reports/plans/2026-09-08_critic-dispatch-and-dangling-agent-refs.md`, which addressed one symptom of this

---

## Objective

Repair the Quarto-native fork so the pipeline works end to end: every stage pairs a creator
with a critic, every handoff is validated, every declared contract is checked by a gate, and
every path reference resolves. Restore what the fork dropped without justification; keep what
it correctly dropped; preserve everything it added that clo-author lacks.

## Why: what the audit found

The fork **took callers and left callees**. It vendored agents, skills and rules that depend on
templates, scripts and a declaration registry, and did not carry the dependencies across.
Nothing compared the result to the tree it forked from.

- **11 of 17 agents cannot reach files they are instructed to read** (`coder` 6 of 13,
  `writer` 6 of 12, `storyteller` 3 of 3).
- **Critic pairing is absent at 3 of 9 stages** — `/write`, `/revise`, `/submit`. `/write`
  contains zero occurrences of "critic".
- **Two scripts invoked by 7 and 5 skills were never vendored.**
- **66 dangling path references**, from a half-completed template relocation.
- **Four deleted agents still named in 60+ live references.**
- **`rules/quality.md` has gated submission at >= 95 on weights that did not exist** since D1.

### Three deletions were justified by claims the files contradict

| Claim used to justify D1/D3 | What the file says |
|---|---|
| the dependency graph serializes Coder before Writer | `workflow.md` §3: *"Phases activate by dependency, not sequence. Research is not a waterfall,"* with targeted coder->writer re-entry as its worked example |
| `lifecycle.md` is part of that graph | it is a **Handoff Validation Protocol** — PRE/POST validation, fail-fast |
| the `>= 95` weight set sums to 120 and cannot normalize | `theorist`'s 20% is declared `CONDITIONAL` and renormalized out for applied papers; the remainder sums to **exactly 100** |

`permissions.md` bundled a phase graph (correctly cut) with a **declaration registry**
(collateral damage). Losing the registry is the root cause of the pairing loss, the
uncomputable gate, and the re-hardcoding of relationships across nine skill files.

## Decisions taken

| # | Decision |
|---|---|
| D-1 | **Driver is a skill, not an agent.** `AskUserQuestion` is blocked inside subagents (tested), so an orchestrator agent cannot hold an approval gate. Seam count decides it: skill 0, agent 1 (the relay), hybrid 2 — and unowned seams are this codebase's documented failure mode |
| D-2 | **Registry returns** as single source of truth: *"No other file hardcodes these relationships"* — now gate-enforced |
| D-3 | **Weight set (A)** — the registry's own declared weights, with `CONDITIONAL` renormalization |
| D-4 | **One path rule:** every reference is written relative to the project root, `.claude/`-prefixed |
| D-5 | **Claim–Evidence Table**, produced by `writer-critic`, covering numeric *and* qualitative claims |
| D-6 | **Not restored:** `orchestrator` as an agent (content kept, packaging dropped); `working-paper-format.md` (pure LaTeX); `guide-writer` (dead upstream too); `PHASE` (superseded by `REQUIRES`) |

## Architecture

**Driver:** one skill, `/pipeline`, in the main session with `Task`. Dispatches every worker and
critic, holds loop state, asks the user directly, recovers from `pipeline_state.json`.

| Layer | Owns | File |
|---|---|---|
| Driver | loop, dispatch, approval gates, escalation, recovery | `skills/pipeline/SKILL.md` |
| Contract | per-agent declarations | `rules/permissions.md` |
| Handoff | PRE/POST validation, fail-fast | `rules/lifecycle.md` |
| Pairing | creator->critic, three strikes, separation of powers | `rules/agents.md` |
| Scoring | weight set (A), `CONDITIONAL`, thresholds | `rules/quality.md` |
| Governance | learning promotion, no autonomous self-modification | `rules/meta-governance.md` |
| State | machine-readable progress, survives compaction | `quality_reports/pipeline_state.json` |

**Spine.** `/discover interview` -> `/lit-position` -> `/discover data` -> `/strategize` ->
`/analyze` -> `/write` -> `/review` -> `/submit`, with `/talk` parallel and advisory. Phases
activate by `REQUIRES`, never by sequence; re-entry permitted everywhere except Submission.

**Two modes.** Orchestrated (`/pipeline` drives, validates, pauses) and Standalone (any skill
invoked directly skips *dependency* checks). **Standalone never skips critic dispatch** — that
conflation is what produced the original defect.

## The registry contract

Seven fields per agent: `REQUIRES`, `PRODUCES`, `CRITIC`, `ESCALATION_TARGET`,
`QUALITY_WEIGHT`, `CONDITIONAL`, `WRITES`. `PARALLEL_GROUP` demoted to documentation; `PHASE`
dropped.

**`REQUIRES` predicate types:** path (Glob), score (research journal), section (heading
present), and **render** (`quarto render` exits 0 and named `output/` artifacts exist). The
render predicate replaces `paper/tables/ contains .tex files` and is strictly stronger: it
proves the code *ran*, not that a file was written.

**Structural adaptation.** clo-author splits work across `scripts/`, `paper/tables/*.tex`,
`paper/sections/*.tex`. Our pipeline has **one `manuscript_<project>.qmd`** that coder and
writer both edit, ingesting `data/raw/` directly. `PRODUCES` therefore names manuscript
sections and `output/` artifacts, not separate files.

**Concurrency hazard, new to our design.** Because coder and data-engineer would both write the
single manuscript, `WRITES` is declared per agent and the driver refuses concurrent dispatch
when write-targets intersect. A straight port would have carried clo-author's parallel groups
over and silently clobbered the manuscript.

**Weights (set A):** literature 10, data 10, strategy 25, theory 20 `CONDITIONAL`, code 15,
manuscript 10, referees 12.5+12.5, replication 5. Applied paper: exactly 100. With theory: 120,
renormalized. Declared inline in `rules/quality.md`, the file that consumes them.

## Handoff validation

**PRE-dispatch:** `REQUIRES` satisfied; required sections present; on failure do not dispatch,
name the missing artifact and the skill that produces it.

**POST-completion:** `PRODUCES` exist including named sections; render clean where declared;
**the paired critic has produced a score, logged in the research journal**; on failure do not
advance. A creator cannot be marked complete without its critic's score — the structural fix
for the defect that opened this work.

**Limits:** 3 rounds per pair, 5 overall, 2 verification retries. Escalation targets come from
the registry.

## Claim–Evidence Table

Produced by `writer-critic` at every review, recorded to
`quality_reports/reviews/claim_evidence_<project>_<date>.md`.

| Claim (verbatim) | Location | Type | Evidence | What the evidence shows | Verdict |

Covers numeric *and* qualitative claims. `prose_number_check.py` verifies provenance mechanics
(the number is computed live); it cannot verify **interpretation** — a coefficient of 0.04 with
p=0.31 can be rendered by a valid inline expression and described as "a substantial increase",
and every existing check passes. This table closes that.

**Deductions:** CONTRADICTED −25, UNSUPPORTED −15, OVERSTATED −10 (significance claimed at
p > 0.10, "causes" for an association, a subgroup difference asserted without an interaction
test), UNVERIFIABLE −5.

Produced by the **critic**, not the creator — `agents.md` §2 forbids self-scoring, and a
hand-maintained map by the Writer is what clo-author had and what rots. Regenerated per review,
so it cannot go stale. `INV-22` is then genuinely retired: INV-11 for provenance, this for
interpretation.

## Enforcement

**Every gate is red-tested** — the failure it catches is injected and the gate must fail before
a pass is trusted. Three vacuous-green checks were found in one day.

`check_fork.sh`: `agent-refs` (two exemption tiers — line marker in the owned tree, path-based
WARN for vendored/submodule trees), **`path-resolves`** (the D-4 rule; would have caught all
66), `registry-complete`, `registry-authority`, `weights-sum`, `no-latex-residue`.

`check_install.sh`: existing checks plus **`branch`** (FAIL when the shared checkout is on
neither `main` nor a detached lock SHA; `RESEARCH_CLAUDE_ALLOW_BRANCH=1` downgrades to a named
WARN) and **`scripts-linked`**.

**Runtime gap.** No static check proves a skill *actually dispatches* its critic. Mitigated by
`hooks/critic-pairing.py` (Stop, advisory, exit 0, wired in three places) and by one
user-run smoke test per stage. This is why migration is staged.

## Migration

Worktree development; the shared checkout stays on `main`; **POGM4 is the single canary**,
re-linked per stage while the other five stay untouched until the final merge.

0. Baseline snapshot; all new gates written **failing**
1. Contracts: `permissions.md`, `lifecycle.md`, `quality.md` weights, `meta-governance.md`
2. Missing files: 8 shared templates, 2 scripts, `journal-profile-template.md`; `apply.sh`
   links `templates` and `scripts`
3. Path layer: all 66 references rewritten — largest delta, stop on anything unexplained
4. Pairing: `/write`, `/revise`, `/submit`; dispatch-ownership table; Claim–Evidence Table
5. Driver: `/pipeline`, `pipeline_state.json`, recovery
6. Dangling names cleared with two-tier exemptions
7. Hook wired in three places; `branch` and `scripts-linked` checks
8. Merge, re-link six, lock bump

**Stop conditions:** an unintended graph delta; a gate green without a prior red; a smoke test
passing while the advisory hook fires; a stage needing a file a later stage builds.

## Success criteria

- `check_fork.sh` exits 0 with every criterion red-tested
- `check_install.sh --all` passes on six repos
- `audit_graph.py` reports **0** dangling path references and **0** agents named but absent
- `/write abstract` produces a `writer-critic` score and a Claim–Evidence Table before the draft
- `/pipeline` runs end to end on a scratch project, pausing for approval and resuming after
  `/compact`
- 11 of 17 agents reaching unresolvable files becomes 0 of 17

## Open items for the implementation plan

1. **`new-project-ztp`** is invoked by nothing and names the deleted librarian 3 times. Not yet
   read. Stage 5 opens by reading it and proposing: fold its scaffolding into `/pipeline`, or
   keep it as a setup skill `/pipeline` calls. **Unresolved by design, not by omission.**
2. **`generate_dashboard.py` / `generate_html_report.py`** must be inspected for a
   `paper/sections/*.tex` layout assumption before being trusted.
3. **`/promote`** may already implement part of `meta-governance.md`'s learning promotion —
   verify before restoring, to avoid two mechanisms for one job.
4. **`scripts/` copy-to-link conversion** (F13) affects `apply.sh` and six repos; sequence it
   with Stage 2's linking change.
