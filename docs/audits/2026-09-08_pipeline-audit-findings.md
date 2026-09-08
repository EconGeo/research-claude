# Pipeline Audit — Findings
**Date:** 2026-09-08 · **Method:** Pass A (dependency graph) → Pass B (differential vs clo-author) → Pass C (spine trace)
**Trees:** `~/Academic/research-claude` @ main `6456d2a` · `hugosantanna/clo-author` @ `d36c408` (HEAD), pin `8367d51` (2026-05-10)

## Headline

The Quarto-native fork **took callers and left callees**. It vendored agents, skills and rules
that depend on templates, scripts and a pairing registry, and did not carry those dependencies
across. Nothing compared the result against the thing it forked from, so the gap was invisible
until a skill was actually run.

| Measure | ours | clo-author |
|---|---|---|
| agents | 17 | 21 |
| skills | 18 | 14 |
| rules | 16 | 12 |
| root `templates/` | 6 | 12 |
| `scripts/` | 4 | 3 (+`R/`) |
| **dangling path references** | **66** | 34 |
| **deleted agents still named** | **4** | 0 |

## F1 — Critic pairing is broken at three of nine stages

clo-author pairs a critic with a creator at **every** stage (`WORKFLOW_QUICK_REF.md`). Ours:

| Stage | Creator | Critic |
|---|---|---|
| `/discover data` | explorer | explorer-critic ✓ |
| `/lit-position` | — | self-check (D3) |
| `/strategize` | strategist, theorist | both critics ✓ |
| `/analyze` | coder, data-engineer | coder-critic ✓ |
| **`/write`** | writer | **NONE** |
| **`/revise`** | writer, coder | **NONE** |
| **`/submit`** | verifier | **NONE** |
| `/talk` | storyteller | storyteller-critic ✓ |
| `/review` | — | routes to all ✓ |

`/write` contains zero occurrences of "critic". No draft has been critic-reviewed unless
`/review` was run by hand.

## F2 — `lifecycle.md` was deleted under a false description

Our spec deleted `permissions.md`, `lifecycle.md`, `orchestrator.md`, `workflow.md` as one
"dependency graph" (D1). **`lifecycle.md` is not a dependency graph.** It is a *Handoff
Validation Protocol*: PRE-dispatch validation, POST-completion validation, fail-fast. It is the
machinery that guarantees each stage's output is valid before the next consumes it — precisely
the end-to-end integrity this audit exists to restore. It was bundled into a deletion whose
stated rationale (phase serialization) does not describe it.

`permissions.md` was likewise bundled: it held the **declaration registry** (`CRITIC`,
`QUALITY_WEIGHT`, `ESCALATION_TARGET`, `PRODUCES`) as well as the graph. Losing it is why
`rules/quality.md` §1 has gated submission at ≥95 on a weighted aggregate whose weights exist
nowhere, since D1.

## F3 — 5 files are invoked but were never vendored

| File | Invoked by | In clo-author? |
|---|---|---|
| `scripts/generate_dashboard.py` | **7 skills** | ✓ |
| `scripts/generate_html_report.py` | **5 skills** | ✓ |
| `templates/archive-readme.md` | `rules/content-standards.md` | ✓ |
| `templates/exploration-readme.md` | `rules/content-standards.md` | ✓ |
| `templates/pipeline-state.json` | `rules/logging.md` | ✓ |

12 of clo-author's 12 root templates were dropped; several are still referenced.

## F4 — 66 dangling path references, in three classes

- **25 mis-pathed** — file exists, pointer wrong. All in `agents/*.md` naming `templates/X` or
  `references/X`. clo-author keeps `templates/` at repo root, so these were correct there; our
  vendoring moved templates under `skills/<skill>/templates/` without updating agent pointers.
  **An agent has no skill directory to resolve relative to**, so these fail at runtime.
- **11 genuinely absent** — 5 above, plus `references/audit-pet-peeves.md`,
  `templates/journal-profile-template.md`, `templates/{quarto,rmd}-preamble.tex`,
  `skills/prompt-references/formatting-core.md`, `scripts/R/00_master.R`.
- **5 illustrative examples** — `FILENAME.R`, `01_download_cbp.py`. Not defects.

## F5 — 4 deleted agents still named in 30+ live references

`orchestrator` (31), `librarian` (30 across 12 files), `librarian-critic`, `guide-writer`.
Two librarian references are **deliberate and must survive**: `skills/lit-position/SKILL.md:94`
(D3-inherited categories) and `rules/ai-disclosure.md:66` (a dated provenance record). Two more
sit in trees we may not edit (`zotpilot-skills/`, `submodules/ai-audit/`).

## F6 — Other deleted things still named (not yet scoped)

`clo-author` 11 refs / 7 files incl. 3 agents · `INV-22` 8 refs / 5 files **in violation of our
own stated constraint**, incl. two scoring rubrics that still deduct for it ·
`rules/{table,figure}-standards.md` 6 refs, files deleted.

## F7 — `references/journal-profiles.md` has no real-estate journals

No REE, JREFE, JRER, JREPM. `references/discipline-cards.md:81` advertises all six as shipped
there. `agents/{editor,methods-referee,domain-referee}.md` all open by reading it to locate a
profile. For a real-estate paper — every project in this fork — calibration falls through.

## F8 — Hooks

4 of 12 installed but unwired in all six repos (`context-monitor.py`, `protect-files.sh`,
`lint-scripts.sh`, `post-merge.sh`). `post-merge.sh` is a **git** hook sitting in the Claude
hook table. `check_install.sh` cannot see wiring — `settings.json` is project-owned.

## F9 — Install layer is healthy

All six repos PASS membership and link resolution. Only lock drift (`1ad4140` vs `6456d2a`).
This layer is not the problem.

## The pattern

Every finding is one shape: **a file declares a capability, its dependents keep asserting it
works, and nothing compares the assertion to reality.** F1 (pairing claimed in `rules/agents.md`
§1, enforced nowhere), F2 (weights gated on, deleted), F3 (scripts invoked, never vendored),
F7 (journals advertised, absent), F8 (hooks installed, unwired). The remedy is not 66 edits —
it is a gate per class, plus declaring each contract in the file that consumes it.

## F10 — 11 of 17 agents cannot reach files they are told to read

This is the single most consequential finding, and only a per-agent contract check surfaces it.

| Agent | paths read | unresolvable |
|---|---|---|
| coder | 13 | **6** |
| writer | 12 | **6** |
| strategist | 8 | **5** |
| storyteller | 3 | **3 — all of them** |
| theorist | 4 | 2 |
| writer-critic | 6 | 2 |
| coder-critic, editor, explorer-critic, storyteller-critic, theorist-critic | — | 1 each |

Cause is F4: clo-author keeps `templates/` at repo root and its agents reference `templates/X`.
Our fork relocated templates under `skills/<skill>/templates/` — correct for skills, which
resolve relative to their own directory — but **agents have no skill directory**, so every such
pointer in an agent file dangles. The relocation was half-completed and nothing checked the
other half.

## F11 — clo-author upstream (14 commits since our pin) holds nothing we lack

All 14 are HTML-dashboard work: `rules/html-dashboard.md`, `skills/dashboard/`, a `logging.md`
tweak. We already carry both files and they are **byte-identical** to upstream HEAD. There is no
outstanding cherry-pick from clo-author. The divergence to justify is entirely what we *dropped*,
not what we failed to take.

## F12 — Vendored/submodule layer

`zotpilot-skills/` 6 skills, `librarian` refs (fix upstream, re-vendor). `submodules/ai-audit`
2 agents / 1 rule, one `librarian` provenance ref (leave). `submodules/journal-digest` is a
standalone tool with no pipeline coupling — clean, out of scope.
