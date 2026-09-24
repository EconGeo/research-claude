# Forensic Delivery Audit — the 2026-09-08 → 2026-09-10 pipeline overhaul

**Audit date:** 2026-09-23
**Auditor:** Claude Opus 5 (forensic read-only pass)
**Repo:** `~/Academic/research-claude`
**Scope:** the 168 commits dated 2026-09-08 through 2026-09-10, and the plan/spec set that drove them:

- `docs/superpowers/plans/2026-09-08-pipeline-repair.md` (4,263 lines, 224 unchecked checkboxes)
- `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (391 lines)
- `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` (220 lines)
- `docs/decisions/2026-09-08_pipeline-repair-rulings.md` (1,018 lines)
- `docs/2026-09-10_final-cleanup-handoff.md` (627 lines)

**Method.** Read-only. Nothing was fixed, moved, or created except this file. Every claim below is
labelled `tested:` (a command was run in this session and its output observed) or `per file:` (a file
was read to end-of-file in this session). A grep hit is treated as a locator, never as evidence:
where a grep located a candidate, the file was then read before any claim was made about it.

**Reading log.** The 4,263-line plan was read in full, in successive chunks to EOF. The chunk
boundaries and what each contained are recorded in § 1 below. The three specs, the rulings
document and the handoff were each read in full.

**Central distinction used throughout.** A *promise executed badly* (the plan named the deliverable
and the commit shipped something that does not work, or is not connected) is a different failure
from *a gap the plan never modelled* (the defect exists but no line of the plan ever addressed it).
The ledger marks which each row is, and § 5 separates the two totals.

---

*(sections appended below as the audit proceeds)*

## 1. Reading log (what was read in full, and how)

`tested:` the plan was read with `sed -n` over successive line ranges until EOF, and the three
gaps left by output-truncation were re-read explicitly. Ranges, in order:

| Range | Contents |
|---|---|
| 1–350 | Goal, architecture, global constraints, decisions P-1…P-15, file map (created/modified/deleted), Stage 0 Tasks 0.1–0.3 |
| 350–750 | Fixture manuscript, `tests/run_fixture.sh` skeleton, `scripts/check_refs.py` in full |
| 750–1250 | `scripts/check_paths.py`, `check_fork.sh` full rewrite, `check_install.sh` `branch` check, Stage 1 opening, `rules/registry.yaml` (components + first agents) |
| 1250–1800 | rest of `registry.yaml` (19 entries), `registry_lib.py` + its tests, `render_registry.py` |
| 1800–2350 | `rules/lifecycle.md`, `rules/quality.md`, `rules/meta-governance.md`, `rules/agents.md`, D1 supersession, `tests/test_pipeline.py` |
| 2340–2650 | `scripts/pipeline.py` in full (state, score, predicates, registry check, CLI) |
| 2650–3000 | Stage 1b (manuscript declaration), Stage 2 (seeds/templates split, apply.sh, check_install, embed test, canary), Stage 3 (path inventory), Stage 3b.1 `chunk-structure.md` |
| 2995–3400 | 3b.1 coder/data-engineer/analyze, 3b.2 write, 3b.3 review, 3b.4 agents (writer-critic, coder-critic, verifier) |
| 3400–3720 | rest of 3b.4, 3b.5 (fourteen skills), 3b.6 references, 3b.7 rules, 3b.8 gates, Stage 4 tasks 4.1–4.3 |
| 3720–4090 | `lit-critic`, Claim–Evidence Table, D-16/17, Stage 5 (dispatch-log, critic-pairing, post-compact, `/pipeline` driver, live tiers) |
| 4085–4263 | Stage 6 (deleted-things sweep, README, re-vendor), Stage 7 (hooks), Stage 7b (journal profiles), Stage 8 (six-repo migration, merge, sign-off), plan self-review |

The three specs (391 + 220 lines), the rulings document (1,018 lines) and the handoff (627 lines)
were each read in full. Where a claim below rests on one of them it says so.

**Plan shape.** 224 `- [ ]` checkboxes across 9 stages (0, 1, 1b, 2, 3, 3b, 4, 5, 6, 7, 7b, 8),
none ticked. The plan is unusually specific: most steps carry the complete file contents to be
written, not a description. That matters for the audit, because it means "did this land?" is
answerable by diffing the shipped file against the plan's own text.

---

## 2. The commit window, and what it actually contains

`tested:` `git log --since=2026-09-07 --until=2026-09-11 --oneline | wc -l` → **169** (168 after
excluding the boundary commit dated 2026-09-07). By date: 1 on 09-07, 48 on 09-08, 72 on 09-09,
48 on 09-10.

**The window is two projects, not one**, and the ledger has to separate them or it will credit
the second with the first's deliveries:

| Burst | Commits | Driven by |
|---|---|---|
| **A — the quarto-native fork** | `7729df1` … `999f3f9` (2026-09-08, ~28 commits) | `docs/superpowers/specs/2026-09-08-quarto-native-research-pipeline-design.md` (D1–D5, work items A–E). No implementation plan was ever written for it; it was executed directly from the spec. |
| **B — the pipeline repair** | `55a8ddb` … `7268017`, then `4cf76a8` … `43a80db` (2026-09-08 → 09-10, ~140 commits) | `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (D-1…D-25, R-1…R-7) and the 4,263-line plan. |

Burst B exists **because** burst A shipped: the repair spec's § 2 is an audit of what burst A left
behind ("The previous fork kept clo-author's functionality by vendoring its skills wholesale and
adding Quarto as an exception mode beside a LaTeX default"). Burst A is therefore both a set of
promises in its own right and the defect the second plan was written against.

### Classification scheme used in the ledger

| Class | Means |
|---|---|
| **LANDED-AND-WORKS** | the artifact exists, and running it or reading it shows it does the thing promised |
| **LANDED-BUT-UNWIRED** | the artifact exists and is correct in isolation, but nothing invokes, reads, routes to or schedules it |
| **LANDED-BUT-BROKEN** | the artifact exists and is invoked, but does not do what it says — including a gate that reads green on a property it cannot detect |
| **PARTIALLY-LANDED** | some named sub-deliverables landed and others did not |
| **NEVER-LANDED** | nothing was shipped for this promise |
| **SUPERSEDED** | a later recorded decision replaced the promise; the ledger names the decision |

Each row is also marked **[exec]** (a promise the plan named and execution got wrong) or **[gap]**
(a defect the plan never modelled). § 5 totals them separately.

---

## 3. The ledger

### 3.A — Burst A: the quarto-native fork spec

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| A1 | "`submodules/clo-author` removed; `.gitmodules` retains only `ai-audit` and `journal-digest`" | `873a05f` | `tested:` `ls submodules .gitmodules` → both "No such file or directory". The submodule *mechanism* was removed wholesale on 2026-09-09 (R-81, commit `351db7a`/`6c2d025`), going past this promise. | SUPERSEDED (by R-81) |
| A2 | "`rules/pipeline-precedence.md` deleted — nothing left to take precedence over" | `c34d0a2` | `tested:` absent; `scripts/check_fork.sh` carries `absent pipeline-precedence rules/pipeline-precedence.md` and the whole gate exits 0. The deletion is pinned, not merely done. | LANDED-AND-WORKS |
| A3 | "The merged `coder-critic` contains both POGM4's manifest checks (INV-23/INV-24) and zoning2026's Correctness Layer" | `3162a8d` | `per file:` `agents/coder-critic.md` read in full (95 lines): `## Correctness Layer` at line 44 and the INV-23/INV-24 rows at 78–79 are both present. `check_fork.sh` pins each half with `contains cc-zoning-half … 'Correctness Layer'` and `contains cc-pogm-half … 'INV-23'`. | LANDED-AND-WORKS |
| A4 | "`ai-audit` … **keep** — `/humanize`, `/verify-claims` are used and format-agnostic" | `9942a61`, later `6c2d025` | `tested:` `ai-audit/` holds 2 agents + 2 skills and `apply.sh:155–163` links them into every project. `tested:` `grep -rn 'humanize\|verify-claims' skills/pipeline skills/review rules/registry.yaml` → **no matches**. So they install into six repos and are named by no registry entry, no `/pipeline` stage file (12 exist), and no `/review` route. The only tree references are `skills/write/SKILL.md`'s *description* string (a legacy "replaces the old humanizer command" note) and the README. | **LANDED-BUT-UNWIRED** [gap] |
| A5 | "6 design checklists (DiD, IV, RDD, event-study, structural, **descriptive**) → `templates/design-checklists/` verbatim" | `1875b42` | `tested:` `ls skills/strategize/templates/design-checklists/` → `descriptive.md did.md event-study.md iv.md rdd.md structural.md` — six, at the in-skill path success-criterion 9 specified. | LANDED-AND-WORKS |
| A6 | "`decision-record.md` → `quality_reports/decisions/`"; "`robustness-plan.md` + 3 PAP registry templates"; "`narrative-arcs.md`" | `1875b42` | `tested:` all present (`skills/strategize/templates/{decision-record,robustness-plan,pap-safety}.md`, `pap-templates/`, `skills/talk/templates/narrative-arcs.md`). Each was, by the spec's own words, a port that "has **never produced an artifact** in any project"; nothing in this window changed that. | LANDED (dormant as designed) |
| A7 | "`apply.sh` gets simpler: `CLO_SKIP_SKILLS`, the submodule traversal, and the precedence rule all disappear" | `4ca6c9f`, `873a05f` | `tested:` `check_fork.sh` fails if `CLO_SKIP_SKILLS` appears in `apply.sh`; gate exits 0. | LANDED-AND-WORKS |
| A8 | D3: "Fold `librarian` into a ZotPilot bridge skill … self-checks against librarian-critic's 6 categories" | `bce15b5` | `per file:` `skills/lit-position/SKILL.md` exists and is the collector. **The self-check half was reversed**: repair-spec D-15 / R-1 replaced it with an independent `agents/lit-critic.md`, on the stated ground that a creator's self-check is not a score. | SUPERSEDED (by D-15/R-1) |
| A9 | D1: "Keep worker→critic pairing; **cut the orchestration graph**" — delete `permissions.md`, `lifecycle.md`, `orchestrator.md`, `workflow.md`, `pipeline-state.json` | `ebfc15b`, `c34d0a2` | Executed, then **partly reversed 24 hours later**. `docs/decisions/2026-09-08_d1-superseded.md` (read in full) restores `permissions.md`, `lifecycle.md`, `meta-governance.md` and `pipeline-state.json` and keeps only the *agent* deleted. The repair spec's § 2 records why: "Three deletions were justified by claims the files contradict". | SUPERSEDED (by D1-superseded) [exec] |

**A9 is the single most expensive row in the window.** A decision taken on 2026-09-08 deleted
four artifacts on a stated rationale; an audit the same day found the rationale false by reading
the deleted files; and roughly half of burst B (Stage 1, ~15 commits) is rebuilding them. That is
not a promise executed badly — it is a promise that should never have been made, and the cost of
grep-level evidence standing in for a read.

### 3.B — Burst B, Stages 0–2: fixture, gates, contracts, installer

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| B1 | "**A fixture project ships in the repo** … Every gate and every `pre`/`post` predicate is red-tested against it; `tests/run_fixture.sh` is the repeatable end-to-end check" (D-12) | `0b5401f`, `a371592`, `6e77c6e` | `tested:` `tests/fixture-project/` present and tracked; `tests/run_fixture.sh` declares **33 named checks** and `check_fork.sh`'s `fixture` criterion runs it — `./scripts/check_fork.sh` → `PASS [fixture]`, overall exit 0. | LANDED-AND-WORKS |
| B2 | "`scripts/check_refs.py` … `deleted-things`, `inv-refs`, `skill-refs`, `tool-name`, `hooks-readme`, `manuscript-model`, `latex-residue`" | `c2440f7` | `tested:` all seven criteria run from `check_fork.sh` and all report PASS. **But** R-135 (rulings, read in full) records that the final review reinstated "the entire pre-repair multi-file model under different directory names — `sections/*.qmd` with includes, a `code/R/` script tree, `output/tables/*.tex`, a results digest — and **all seven criteria passed**." The gate is a denylist of retired filenames, not a detector of the one-manuscript property. | **LANDED-BUT-BROKEN** (as a property gate) [exec] |
| B3 | "`scripts/check_paths.py` — `path-resolves` with the resolution table" (D-4) | `e116973` | `tested:` `PASS [path-resolves]`, `audit_graph.py` → `dangling path refs : 0`. **But** R-18 and R-21 (rulings) record two permanent holes the repair itself documented: `PATH_RE` cannot see a skill-relative reference at all (false negatives — `audit_graph.py` sees 12 it misses), and it truncates `{lang}`/`*` placeholders into false positives. | PARTIALLY-LANDED [exec] |
| B4 | "`rules/registry.yaml` … AUTHORITATIVE … No other file states a creator→critic pair or a weight (`check_fork`: `registry-authority`)" (D-2, D-10) | `eff91ab`, `d1597c8`, `05d300e` | `tested:` `python3 scripts/pipeline.py --root . registry check` → PASS on all five criteria. **But** R-110 records the gate ran green while ten pair declarations sat outside the registry, purely because `AUTH_ARROW` was compiled without `re.I`; and R-134 records that the fix "rewrote `→` as `, then`, moving the pair statements out of the regex's reach rather than out of the tree." `rules/agents.md`'s 13-row dispatch table still names the critic for seven of eight creators. | **LANDED-BUT-BROKEN** (as an authority gate) [exec] |
| B5 | "`scripts/pipeline.py` implements `pre <agent>`, `post <agent>`, `score`, `state <op>` against a machine-readable registry" (D-9) | `781a253`, `80fb06d`, `264fc7f`, `cb04c9f` | `tested:` all subcommands exercised by `tests/test_pipeline.py` inside a 175-test suite that runs OK, and by 33 fixture checks. `tested:` real state files exist in four of six paper repos with real scores and real critic report paths. This is the single most load-bearing artifact of the repair and it works. | LANDED-AND-WORKS |
| B6 | `rules/lifecycle.md`: "A creator cannot be marked complete without its critic's completion in the dispatch log **and its critic's score** in the state file" | `781a253`, then `264fc7f` + `cb04c9f` | `per file:` only the first half shipped initially. R-41/R-42/R-44/R-45 (rulings, read in full) record the prose promising score enforcement while the code did not implement it, then a first remedy that was itself wrong (a stale score from an earlier round satisfied `post` for all seven creators), then the fix folded into `critic-ran`. It works now — after two reversals. | LANDED-AND-WORKS (after 2 reversals) [exec] |
| B7 | "`rules/permissions.md` is rendered from it by a script and gate-checked as identical" (D-10) | `d1597c8` | `tested:` `PASS [registry-rendered]`. **But** R-50: `critic-ran` — the one predicate binding every creator — "was **absent from `permissions.md` entirely**, because no agent declares it"; the contract shipped to six repos did not mention the gate it runs on. R-48: deleting an `elif` from the renderer degrades the contract to a bare type string while all five verdicts stay green. Both were closed inside the window. | LANDED-AND-WORKS (after fixes) |
| B8 | "Weights (set A, R-1): literature 10, data 10, strategy 25, theory 20 CONDITIONAL, code 15, manuscript 10, referees 12.5 + 12.5, replication 5. Non-conditional sum exactly 100" | `c9b2b14` | `tested:` `PASS [weights-sum]`. **But** R-104 records that five of the eight components had **no `record-score` call anywhere in the tree** — 65 of 100 non-conditional weight points structurally unreachable — invisible to every gate built up to that point, because each gate checks whether an already-recorded score is fresh, never whether anything ever records one. Fixed as controller-authored Task 4.7 (`40e4747`), which the plan does not contain. | **LANDED-BUT-UNWIRED** at first; now LANDED-AND-WORKS [gap] |
| B9 | "D-8 Per-project manuscript declaration … a gate refuses to run when it is absent" | `c8907f0`, `b93a924`, `56a6030` | `tested:` `./scripts/check_install.sh --all` → `PASS [manuscript-declared]` on five repos, WARN on BRI (no `.qmd`). **But** the criterion shipped with *both* branches unreachable: R-53 (`grep -c` prints `0` **and** exits 1, so `"0\n0"` broke the arithmetic) and R-54 (BSD `sed` has no `\s`, so the PASS branch could never fire on macOS). It was green-by-vacuity for two commits. | LANDED-AND-WORKS (after 2 fixes) [exec] |
| B10 | "D-13 `templates/` splits into `templates/` (shipped, linked) and `seeds/` (copied once, project-owned)" | `546ebd0`, `b29380b` | `tested:` `seeds/` holds `gitignore settings.json bootstrap-pipeline.sh ai-use-log.md data_manifest.md quarto-preamble.tex`; `templates/` holds `handoff.md pipeline-state.json journal-profile-template.md`; `apply.sh` links the latter and copies the former; `PASS [seeds-complete]`, `PASS [membership]` ×6. | LANDED-AND-WORKS |
| B11 | `check_install.sh` gains "`scripts-linked`, `templates-linked`, `hooks-wired`, `manuscript-declared`, `state-valid`, `gitignore-covers`" and `branch` | `b32b887`, `21978da`, `ad0545f` | `tested:` `./scripts/check_install.sh --all` exits 0 across six repos with every named criterion present and passing (two WARNs: a stale lock, a project-local `statusline.sh`). | LANDED-AND-WORKS |
| B12 | "`check_install.sh` … 44 mentions in the plan" — but the plan names **no** automated trigger for it | — | `tested:` `hooks/install-check.py` exists, its docstring reads "It was invoked from exactly one place: `/promote`, the workflow a paper session almost never runs" — and it is dated **2026-09-23**, thirteen days after the window, by commit `e285f9d`. For the whole of the overhaul the best project-side diagnostic in the repo ran only when somebody typed a command they had no reason to type. | **NEVER-LANDED** in the window [gap] |
| B13 | Stage 2 exit criterion: "POGM4 is linked to `$W`" (the canary, from Task 2.5 onward) | — | Not done. R-127 (rulings) states it plainly: "The plan's Stage 2 exit criterion ('POGM4 is linked to `$W`') was never met, so: no hook in this branch has fired in a live session … `tests/run_fixture.sh --live` and the two live-tier tasks are **untested, not merely undone**." Closed later, outside the branch, on 2026-09-10. | NEVER-LANDED in-branch; closed post-merge [exec] |

### 3.C — Burst B, Stage 3b: the instruction layer (the largest stage)

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| C1 | "`agents/coder.md` Stages 0–3 become chunk work in the manuscript; Project Layout and Output Location sections deleted" | `a024c74`, `fc62cb4` | `per file:` `skills/analyze/SKILL.md` read: "Run the analysis as chunks of the declared manuscript"; `skills/analyze/templates/chunk-structure.md` present; the three script scaffolds and `results-summary.md` are gone (`tested:` all four absent). | LANDED-AND-WORKS |
| C2 | "`skills/write/templates/drafting-gates.md` — gate = estimation chunk present and `render` clean, **never file existence**" | `6919653` | `per file:` GATE 3 now reads "**Hard prerequisite — never file existence:** at least one `estimate-*` chunk and one `tbl-*` chunk … `quarto render` exits 0 (`pipeline.py pre writer` checks both)". The gate names the executable that checks it. | LANDED-AND-WORKS |
| C3 | "`skills/review/SKILL.md` auto-detect: `.qmd` at the declared manuscript → comprehensive; `scripts/acquire/*` or `explorations/*` → code review; `talks/*.qmd` → talk review" | `f89c9d0` | `per file:` all three routes present verbatim at lines 18–22, each resolving the manuscript through `pipeline.py manuscript`. | LANDED-AND-WORKS |
| C4 | Stage 3b exit criterion: "`latex-residue`, `manuscript-model`, `inv-refs`, `skill-refs`, `path-resolves`, `tool-name` green; `audit_graph.py` dangling = **0**" | `5c0cf9c`, `dccbdc5`, `45e2feb`, `d2c688e` | `tested:` all six criteria PASS and `audit_graph.py` → `dangling path refs : 0`. Reached only after the gates themselves were repaired four separate times (R-61/R-67/R-69 on `audit_graph.py`; R-74/R-87 on the marker regex; R-33 on gates naming absent things; R-122 on a retired name shadowing a live one). R-71 records that the plan's own `dangling = 0` exit criterion was *unreachable at that point* and the real number was 6. | LANDED-AND-WORKS (after 4 gate repairs) [exec] |
| C5 | Spec § 8: a per-file rewrite table covering every shipped agent, skill, sub-file, reference and rule | `a024c74` … `4c85ff1` (14 commits) | Substantially delivered. **But** R-78 records **five agent files had no owning task anywhere in the 4,263-line plan** (`writer`, `strategist`, and three critics) — a fifth of the stage's targets sat outside every task's writable set while the stage's own exit criterion said "every agent … describes the one-manuscript path only". Closed by extending Task 3b.4 (`cd59705`). | PARTIALLY-LANDED by the plan; completed by the executor [exec] |
| C6 | P-3: "`rules/registry-verification-gate.md` is **kept** per spec §8 … made file-level `residue:historical`" | `4c85ff1` | `tested:` the file is **absent**. Deleted on 2026-09-23 by `83205d7` ("superseded"), thirteen days after the window — i.e. the plan's own flagged-for-later-ruling item took two weeks to resolve, in the direction the plan predicted ("Deleting it would be more consistent with D-7"). | SUPERSEDED (post-window) |

### 3.D — Burst B, Stage 4: pairing, `lit-critic`, the Claim–Evidence Table

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| D1 | "**writer-critic dispatched on every mode that touches prose**, `style-guide` alone exempt" | `806b6be`, `6a65269` | `per file:` `skills/write/SKILL.md:66` dispatches writer-critic, records with `--deductions` and `--scope section:`, and names `style-guide` as the only exempt mode. **But** R-101: the first version asserted the gate in Step 5 while `/write humanize` was a *sibling* mode section that never reached Step 5 — "A sentence claiming the gate applied had been added to Step 5 without checking whether Step 5 was ever executed on this path." | LANDED-AND-WORKS (after 1 reversal) [exec] |
| D2 | "`agents/lit-critic.md` (new) — cold-read critic … `mcpServers: zotpilot` for coverage queries; never collects" (D-15) | `9d7a46a`, `b98d26c` | `per file:` `agents/lit-critic.md` read in full — cold-read protocol, six categories, `mcpServers: zotpilot`, explicit "Never call `search_academic_databases` or `ingest_by_identifiers`". `tested:` `skills/lit-position/SKILL.md` Step 7 dispatches it and records the score. `tested:` `ESG/quality_reports/reviews/lit-critic_2026-09-15.md` and `_round2.md` exist — it has run twice for real. | LANDED-AND-WORKS |
| D3 | "**Claim–Evidence Table** produced by `writer-critic` at every review, recorded to `quality_reports/reviews/claim_evidence_<project>_<date>.md`" (D-5, spec §7) | `e1d5f84` | `tested:` template present; rubric rows (CONTRADICTED −25 / UNSUPPORTED −15 / OVERSTATED −10 / UNVERIFIABLE −5) in `scoring-rubrics.md`; and **six real tables exist on disk** across POGM4 (4) and NAR_settlement (2). | LANDED-AND-WORKS |
| D4 | Every creator dispatch in every skill is followed by its critic | `40e4747` | `tested:` every scored component now has a `record-score` site. **But** R-103: `/strategize pap` shipped with "**optionally** strategist-critic" and a section headed "Optional strategist-critic Review" — a direct contradiction of `rules/agents.md` §1, on the one artifact whose value is that it was committed to before seeing results. Fixed in the same commit. | LANDED-AND-WORKS (after 1 fix) [exec] |
| D5 | D-2: skills write artifacts at the paths the registry declares | `4a93afa`, `05d300e` | R-108/R-111/R-112: **three** skills instructed writing to a path contradicting their own agent's registry `produces` — `/discover data` (one file vs three), `/strategize` (the heaviest component, 25 weight), `/talk`. R-108's consequence is the sharpest single finding in the repair: the `score-if-scored data` gate **the user personally asked for in R-38** could never fire, because `explorer`'s artifacts were never written where `strategist.requires` looks. | **LANDED-BUT-BROKEN**, now fixed [gap] |

### 3.E — Burst B, Stage 5: the driver and the two new hooks

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| E1 | "`skills/pipeline/SKILL.md` + `skills/pipeline/references/{setup,literature,data,strategy,theory,analyze,write,review,submit,talk,recovery}.md` — the driver" (D-1) | `2ec48c4` | `tested:` `skills/pipeline/SKILL.md` present; `references/` holds **12** files — the 11 named plus `adopt.md`, added post-window (`631af04`) when the plan's assumption that projects start empty met six in-progress papers. | LANDED-AND-WORKS |
| E2 | "`hooks/dispatch-log.py` — `SubagentStop` appends to `quality_reports/agent_dispatch.jsonl`" (D-11) | `9230186`, `b8d26ff` | `tested:` wired in `seeds/settings.json` under `SubagentStop`; `check_install.sh` `hooks-wired` PASS ×6; real logs exist with 21 lines (POGM4), 23 (NAR_settlement), 3 (ESG), 2 (affordable_housing). **But** R-109: the plan's own brief specified naive local-time second-resolution timestamps — "exactly the format R-39 had already proven broken" — and transcribing it as written would have silently reopened two bugs in the one file created to feed `critic-ran`. | LANDED-AND-WORKS (plan's code was wrong) [exec] |
| E3 | "`hooks/critic-pairing.py` (Stop) … blocks **once per session per pair**" (P-10) | `906b55d`, `88b75d0`, `b8d26ff` | `tested:` wired; four fixture checks (`pairing-block`, `pairing-once`, `pairing-active-guard`, `pairing-clean`, plus `pairing-empty-sid`) pass. **But** R-113: the plan's session filter `e.get("session") in ("", sid)` dropped **every** line written by `pipeline.py log` (which never writes a `session` key) — i.e. the hook whose whole purpose is catching an unpaired creator was blind to precisely the standalone-dispatch path most likely to skip a critic. And R-117 is explicit that this hook "is a nag, not a gate". | LANDED-AND-WORKS (after 3 fix rounds) [exec] |
| E4 | "`post-compact-restore.py` surfaces the state file first" | `36d8e66` | `tested:` `tests/test_compaction_hooks.py` runs in the green suite. Note R-121: `last_component` is *derived* from lexicographic timestamp order and is only correct while R-49's fixed-width UTC format holds. | LANDED-AND-WORKS (fragile by construction) |
| E5 | Task 5.6/5.7: "Live observation of the two hooks"; "`tests/run_fixture.sh --live`" | `a70885b`, `d6f4a9e`, `12cbcee` | **Not done in the window.** R-2: "The live tier … is not executed." R-127: "no hook in this branch has fired in a live session … the runtime tier is entirely ahead." Built and first exercised on 2026-09-10 *after* the merge; the handoff (read in full) records six defects found on the way, including a **false green**: "the live tier ran in the mechanical tier's `$T`, so `live-dispatch-log` passed on residue — `run_fixture: PASS` with the pipeline never executed." As of the last entry, a full green `--live` run is still open. | **NEVER-LANDED** in-window; PARTIALLY-LANDED since [exec] |

### 3.F — Burst B, Stages 6–8: deletions, hooks, profiles, migration

| # | Promise (quoted) | Commit | Current state | Class |
|---|---|---|---|---|
| F1 | "D-18 The HTML dashboard / HTML report layer is retired: `/dashboard`, `/tools dashboard`, `rules/html-dashboard.md`, every `generate_*` invocation" | `a8df5c0`, `4c85ff1` | `tested:` `skills/dashboard/` and `rules/html-dashboard.md` absent; `check_fork`'s `d1-deletions` block asserts both. **Not** applied to `ESG/scripts/generate_dashboard.py` — deliberately (handoff §2c: "D-18 removed the dashboard from the *shipped pipeline*, not from a project's own tooling"). | LANDED-AND-WORKS |
| F2 | "D-24 Orphans are deleted, not repaired: `references/prompt-formatting-core.md`, `templates/cover-letter.tex` (converted to `.qmd`)" | `f46265c`, `5d9fa0f` | `tested:` `prompt-formatting-core.md`, `coding-standards-rmd.md`, `cover-letter.tex` all absent; `cover-letter.qmd` present. | LANDED-AND-WORKS |
| F3 | "D-14 Every hook emits on a documented channel … every README row matches its hook's event. `post-merge.sh` leaves the Claude hook table" | `9c722b0`, `0bb99a3`, `098760c` | `tested:` `hooks/post-merge.sh` absent; `PASS [hooks-readme]`; twelve rows in `hooks/README.md` each naming an event. **But** R-128: three of the criterion's ten hits were a *checker* defect (its row regex read any first backticked cell as a filename) — and the alternative considered was restyling the document to dodge the regex. | LANDED-AND-WORKS (after a checker fix) [exec] |
| F4 | Task 7.3: "`lint-scripts.sh` reads `.qmd` chunks (extracted by a small Python helper) and matches `\bboot\(`" | `1e7fa71` | `per file:` `hooks/lint-scripts.sh` read — `.qmd` branch at line 43 extracts chunks via `scripts/qmd_chunks.py` and rewrites the temp path back in the report; two fixture checks (`lint-qmd-clean`, `lint-qmd-setwd`) pass. **But** R-129: the plan asserted a `booktabs` false positive "the code cannot produce — `'boot' in 'booktabs'` is `False`". The executor verified rather than staging a red. | LANDED-AND-WORKS (plan's premise was false) [exec] |
| F5 | R-7: "`protect-files.sh` stays opt-in" | `ad0545f` | `tested:` present, documented in `hooks/README.md:35`, and registered in **no settings file anywhere**. Deliberate — but the rulings' own §6 notes "`hooks-readme` only checks existence and event agreement, never registration — so nothing distinguishes 'deliberately unwired' from 'forgotten'." | LANDED-BUT-UNWIRED (by design, undistinguishable from an accident) |
| F6 | Stage 7b: "+ REE, JREFE, JRER, JREPM, Journal of Housing Economics, APSR, AJPS, JOP profiles … also landed in `~/Research/.claude/references/`" | `8254f6f`, `43a80db` | `tested:` all eight plus AEA P&P present in `references/journal-profiles.md`; `JHousE` disambiguated from Journal of Health Economics `JHE`; `tested:` `~/Research/.claude/references/journal-profiles.md` carries the identical headings at the same line numbers. The `~/Research` half was deferred under R-1 and closed 2026-09-10/13. | LANDED-AND-WORKS (after the window) |
| F7 | Stage 8 success criteria: "Six repos declare a manuscript; zoning2026 has one manuscript and no `.tex` fragments; **no repo has a `scripts/R/` analysis tree**" | `8a7ca92` | `tested:` five of six declare (`BRI` correctly has none — no `.qmd` yet); `ls -d */scripts/R` → "no matches found" across `~/Research`; `zoning2026/paper/tables` does not exist; `POGM4/archive/scripts_R_reference` present as promised. `tested:` `prose_number_check.py` exits 0 on all five declared manuscripts. | LANDED-AND-WORKS |
| F8 | Stage 8.4 (ESG): "seven numbered analysis scripts … any whose output the manuscript reads becomes a chunk; the rest move to `archive/scripts/`" | — | `tested:` `ESG/scripts/` still holds `00_config.R` … `07_grouped_cv_ladder.py` and `generate_dashboard.py`. **Deliberately not done** (handoff §2b): ESG's manuscript is "a 154-line skeleton whose abstract reads `PLACEHOLDER`"; folding its scripts in "fights that plan rather than serving it." Revisit condition recorded. | NEVER-LANDED (deliberate, with a recorded reason) |
| F9 | "`check_fork.sh` exits 0 on `main`; `check_install.sh --all` exits 0 on six repos" (spec §13) | `8bb6218`, `7268017` | `tested:` today, `./scripts/check_fork.sh` → `✓ check_fork: PASS`, exit 0; `./scripts/check_install.sh --all` → `✓ check_install: PASS`, exit 0 on six repos (2 WARNs). | LANDED-AND-WORKS |
| F10 | "`tests/run_fixture.sh` runs `/pipeline` on the fixture end to end … resumes after `/compact`" (spec §13) | — | The mechanical tier does 33 checks and passes. The end-to-end criterion is not met: the handoff's last entry on the subject reads "**Live tier not re-run to green.** A run on 2026-09-10 ended `FAIL [live-pipeline] exit 1` after 126 dispatch events … Deferred by the user." No `/compact`-resume test of the driver exists. | PARTIALLY-LANDED [exec] |
| F11 | R-136: "**Wire the six repos' `.claude/settings.json` AS PART OF THE MERGE, not after it.** `apply.sh`'s `copy_seed` never overwrites" | `ad0545f` + six manual repo commits | `tested:` `hooks-wired` PASS ×6 today. The structural hazard remains and is stated in the handoff's §4: "A new hook added to `seeds/settings.json` reaches **no existing project** — each `.claude/settings.json` must be edited by hand." That bill came due again on 2026-09-23 with `install-check.py`. | LANDED-AND-WORKS (mechanism still unfixed) [gap] |

### 3.G — The established facts, tested against the ledger

Each row asks: **did this plan promise to fix it?** and **what happened?**

| # | Established fact | Did the plan promise it? | What happened | Class |
|---|---|---|---|---|
| G1 | "Of 24 live invariants only INV-11 had an executable gate. INV-15, INV-19b and INV-24 were enforced by nothing while the enforcement table named enforcers for all three." | **Yes — and the plan wrote the false table itself.** Task 3b.7 specifies verbatim: "Enforcement table: `INV-14, INV-15, INV-16, INV-19 \| lint hook (`.claude/hooks/lint-scripts.sh`, reads .qmd chunks) + verifier`". `tested:` `git show <post-overhaul>:rules/content-invariants.md` shows exactly that row shipped. The plan promised the *table*, not the *enforcement*. | The table was delivered exactly as drafted and was false on delivery. Corrected only on **2026-09-23** (`3b1eb9f`, `07aa079`), which added an executable `no-source` predicate for INV-19b and rewrote the INV-15 row to read "**The lint hook does not check this**, despite being named for it". | **LANDED-BUT-BROKEN** [exec] — a promise executed faithfully whose content was wrong |
| G2 | "Nine agents are instructed to write reports but declare no Write tool; the peer-review chain (25% of scoring weight) cannot write any of its four outputs. The string 'Write tool' appears ZERO times in the plan." | **No.** `tested:` `grep -c "Write tool"` on the 4,263-line plan → **0**. `tested:` the plan authors three `tools:` lines verbatim (lines 3337, 3385, 3721 — `writer-critic`, `verifier`, `lit-critic`), every one of them `Read, Grep, Glob[, Bash]`, in the same breath as "Save to `quality_reports/...`". The plan modelled the report path, the report format and the report's score, and never once modelled the capability to write it. | `tested:` 11 of 18 agents declare no `Write`; `editor` ("Write to `.../desk_review.md`", "Write to `.../editorial_decision.md`"), `domain-referee`, `methods-referee`, `writer-critic`, `lit-critic` and `verifier` all carry an explicit write instruction they cannot execute. **The outputs nonetheless exist** — `tested:` `NAR_settlement/quality_reports/peer_review_manuscript_NAR_settlement/` holds all four files, and six Claim–Evidence tables exist across two repos — because the *dispatching session* writes what the critic returns as text. That workaround is undocumented in any agent file, and it has already failed once: the handoff records "POGM4's first run died with strategist-critic done but its report unsaved (critics return reports as text; the orchestrating session writes them)." | **NEVER-LANDED** [gap] — the purest gap in the audit |
| G3 | "`ai-audit` is installed and wired to nothing — no registry entry, no `/pipeline` stage, no `/review` route." | **No.** The repair spec mentions ai-audit only as a vendoring target (R-81/R-82), and R-82 gives the reason it stays off the roster: `registry-complete` compares `agents/*.md` against the registry, and the two audit agents "have no paired critic, no quality component and no business on that roster." Nothing then routed them. | `tested:` `apply.sh:155–163` links 2 agents + 2 skills into every project; `grep` across `skills/pipeline/`, `skills/review/SKILL.md` and `rules/registry.yaml` → zero references. Two skills ship to six repos and are reachable only if a human types `/humanize` or `/verify-claims`. | **LANDED-BUT-UNWIRED** [gap] |
| G4 | "`pipeline.py chunk_labels()` read only `#\| label:` and returned `['setup']` for an 80-chunk manuscript." | **No.** The plan's own code (Task 1.7, transcribed into `scripts/pipeline.py`) is `re.findall(r"^#\|\s*label:\s*([A-Za-z0-9_-]+)", ...)` — one spelling of three. The fixture the gate was red-tested against uses that one spelling for every chunk, so the fixture could never expose it. | `per file:` fixed **2026-09-23** (`ec8905e`); the current docstring records the measurement: "tested against a real 80-chunk manuscript, 79 chunks carried their label in the brace header and only one (`setup`) used `#\| label:` — so the pre-fix version returned a single label for the whole document." A second commit the same day (`5820ac0`) fixed the related hole that the `chunk` predicate's `n >= min` count "cannot fail on prefix correctness". | **LANDED-BUT-BROKEN** [gap] — and specifically a *fixture-shaped* blind spot |
| G5 | "`check_install.sh` exists, is mentioned 44 times in the plan, works well — and had no automated trigger until today." | **No.** `tested:` the plan extends `check_install.sh` in five separate tasks (0.8, 1b.1, 2.3, 7.5, plus Stage 8 sign-off) and never once asks what *runs* it. Its only caller was `/promote`. | `tested:` `hooks/install-check.py` (SessionStart) created 2026-09-23 by `e285f9d`. Its docstring states the general lesson: "A rule that tells an agent to verify the install is the same class of artifact that already failed here — the rules were right and nothing executed them." | **NEVER-LANDED** in the window [gap] |
| G6 | "The test suite (20 files, `tests/run_fixture.sh`) exists and passes: 160 tests." | Yes for the fixture harness (D-12); the unit suite grew organically. | `tested:` `python3 -m unittest discover -s tests -p 'test_*.py'` → **175 tests, OK**, 127 s. `tested:` `tests/run_fixture.sh` declares 33 named checks and `check_fork` runs it green. See § 6 for what the suite does and does not test. | LANDED-AND-WORKS |

### 3.H — Two findings this audit establishes that no prior document records

| # | Finding | Evidence |
|---|---|---|
| H1 | **`context-monitor.py` is wired in the seed and in none of the six paper repos — and `hooks-wired` cannot see it.** Task 7.5 Step 3 says: "In each of the six repos, edit `.claude/settings.json` by hand to add the `SubagentStop` block, the `critic-pairing.py` Stop entry, **and the `context-monitor.py` PostToolUse entry**." Commit `ad0545f`'s subject is "hooks-wired; seed wires context-monitor (R-7)". | `tested:` parsing all six `.claude/settings.json` files gives the identical 9-hook set in every one: `critic-pairing, dispatch-log, log-reminder, notify, post-compact-restore, post-edit-lint, pre-compact, session-guard, verify-reminder`. `context-monitor.py` is in none. `tested:` `check_install.sh:310` — `for h in session-guard.py dispatch-log.py critic-pairing.py` — the gate checks three hooks and reports `PASS [hooks-wired]` ×6. R-7 was ruled, the seed was edited, the six repos were not, and the gate built in the same commit was scoped narrowly enough not to notice. **LANDED-BUT-UNWIRED [exec].** |
| H2 | **Today's fix for G5 has already reproduced R-136 verbatim.** `install-check.py` exists, is wired in `seeds/settings.json`, and reaches **zero** of the six repos — `tested:` `grep -c install-check` on each of the six settings files → 0. It also has **no row in `hooks/README.md`** (`tested:` `grep -c install-check hooks/README.md` → 0), and `hooks-wired` does not look for it. R-136, written 2026-09-10, says exactly this: "`apply.sh`'s `copy_seed` never overwrites an existing settings file, so the two new hooks reach no existing project … This is a prerequisite for the pairing gate being true in production, not a tidy-up." The mechanism was diagnosed thirteen days ago, written down in the durable ruling log, and the next hook added still landed nowhere. |

---

## 4. Proportion in each class

The class in each row is **the state the overhaul left, as it still stood on the morning of
2026-09-23**. Where a row says "after N fixes" the fix landed inside the window or in the
immediate follow-on sessions, and the current class is the one shown. Rows G1 and G4 were
repaired earlier today; they are counted as the overhaul left them, because the point of the
audit is what the overhaul delivered.

| Class | Rows | Share of 57 |
|---|---|---|
| LANDED-AND-WORKS | 35 | **61.4 %** |
| LANDED-BUT-UNWIRED | 5 | 8.8 % |
| LANDED-BUT-BROKEN | 4 | 7.0 % |
| PARTIALLY-LANDED | 3 | 5.3 % |
| NEVER-LANDED | 6 | 10.5 % |
| SUPERSEDED | 4 | 7.0 % |

**Promise executed badly vs gap never modelled.** Of the 22 rows that are not clean deliveries:

| | Rows | Which |
|---|---|---|
| **[exec]** — the plan named the deliverable and execution got it wrong | **10** | A9, B2, B3, B4, B13, C5, E5, F10, G1, H1 |
| **[gap]** — the defect is real and no line of the plan addresses it | **7** | A4, B12, G2, G3, G4, G5, H2 |
| deliberate — superseded by a recorded decision, or not-done with a written reason | 5 | A1, A8, C6, F5, F8 |

That ratio is the headline. **A 4,263-line plan with 224 checkboxes, whose code blocks were
transcribed almost verbatim, still left seven substantive defects it never modelled at all** — and
five of the seven (G2, G3, G4, G5, H2) are of exactly one kind: *a thing exists and nothing
reaches it*. The plan is exhaustive about **what to build** and close to silent about **what will
invoke it**. Its "File map" has a **Created** column, a **Modified** column and a **Deleted**
column, and no column for *who calls this*.

The five deliberate rows are worth separating out because they are the plan working as intended:
each was reversed or skipped with a reason recorded in `docs/decisions/` or the handoff, and each
reason survives reading. Only A9 is a reversal that cost real work.

---

## 5. Where execution broke down — the three recurring shapes

### Shape 1 — **Seeded, never propagated: the artifact exists in the template and reaches no project**

Five separate instances, spanning the window and continuing past it.

| Instance | Evidence |
|---|---|
| `context-monitor.py` (H1) | `tested:` in `seeds/settings.json`; in **0 of 6** project settings files; `hooks-wired` checks only three hook names, so `PASS` ×6 |
| `install-check.py` (H2) | `tested:` in `seeds/settings.json` as of today; in **0 of 6**; no `hooks/README.md` row |
| `ai-audit`'s two skills + two agents (G3, A4) | `tested:` linked by `apply.sh` into every project; named by no registry entry, no `/pipeline` stage file, no `/review` route |
| Five of eight quality components (B8) | R-104: `data`, `strategy`, `referees`, `replication`, `theory` had **no `record-score` call anywhere in the tree** — 65 of 100 weight points structurally unreachable, including the gate the user personally asked for in R-38 |
| `protect-files.sh` (F5) | shipped, documented, registered nowhere; deliberate, but the rulings note nothing distinguishes it from an oversight |

**The mechanism is named in the repo's own record and was not fixed.** R-136: "`apply.sh`'s
`copy_seed` never overwrites an existing settings file, so the two new hooks reach no existing
project." Every subsequent hook has hit the same wall. The fix the record does *not* contain is
the one that would close the class: `hooks-wired` enumerating the seed's own hook list instead of
a hardcoded three, so that adding a hook to the seed automatically reddens six repos.

### Shape 2 — **The gate is a denylist of known-bad strings, and reads green on a property it cannot detect**

The repo diagnosed this itself (R-135) and the diagnosis is understated: it recurred at least six
times, on six different gates.

| Gate | How it read green while false |
|---|---|
| `latex-residue` / `manuscript-model` (B2) | R-135: the final review reinstated "the entire pre-repair multi-file model under different directory names — `sections/*.qmd` with includes, a `code/R/` script tree, `output/tables/*.tex`, a results digest — and **all seven criteria passed**" |
| `registry-authority` (B4) | R-110: case-blind regex, ten genuine pair declarations evaded it by capitalization; R-134: the fix rewrote `→` as `, then`, moving the statements out of the regex's reach rather than out of the tree |
| the INV enforcement table (G1) | named `lint-scripts.sh` as INV-15's enforcer for thirteen days; the hook's only relevant rule is "`library()` call after line 30" |
| `manuscript-declared` (B9) | R-53 + R-54: **both** branches unreachable on macOS — green by vacuity for two commits |
| `chunk` predicate / `chunk_labels()` (G4) | one of Quarto's three label spellings, red-tested against a fixture that uses only that spelling |
| `registry-rendered` (B7/R-48) | delete an `elif` from the renderer and "the contract silently degrades to a bare type string while **all five registry verdicts stay green**" |
| identity scan (R-131) | `grep -rInE` without `-i`, and two patterns requiring a preceding character, so a private dataset name shipped in a public rule file for the entire repair |

The common root is that **every one of these gates was red-tested against the fixture, and the
fixture was built by the same plan that specified the gate**. A red-before-green discipline
proves the gate fires on the case its author imagined. It cannot prove the case its author
imagined is the case that occurs.

### Shape 3 — **Prose shipped as if it were the mechanism**

A sentence describing enforcement was written, reviewed, and installed into six repos, while the
code path it described did not exist or was not reachable.

| Instance | Evidence |
|---|---|
| `rules/lifecycle.md` (B6) | R-41: "Shipped prose promised score enforcement that did not exist." Only the `critic-ran` half was implemented; the score half took three rulings (R-42 → R-44 → R-45) |
| `/write humanize` (D1) | R-101: the gate was asserted in Step 5 of a mode section that never reaches Step 5 — "A sentence claiming the gate applied had been added to Step 5 without checking whether Step 5 was ever executed on this path" |
| `/strategize pap` (D4) | R-103: "optionally strategist-critic" plus a section headed "Optional strategist-critic Review", contradicting `rules/agents.md` §1 |
| `/submit` (R-133) | promised a per-component completeness check the submission gate does not perform — it renormalises, so `code` at 100 with seven components unscored reads `overall=100.0` and **passes** |
| the INV enforcement table (G1) | the canonical case: a table of enforcers, three of them fictional |
| the peer-review chain (G2) | "Write to `quality_reports/peer_review_.../desk_review.md`" in an agent with `tools: Read, Grep, Glob` |

**The plan's own text was the source in five further cases** (R-39 second-resolution timestamps,
R-40 a tautological test leaving the `section` predicate uncovered, R-109 a dispatch-log timestamp
format already proven broken, R-113 a session filter that dropped every standalone log line,
R-129 a `booktabs` false positive the code cannot produce). Transcribing the plan faithfully would
have shipped all five.

### A fourth, smaller shape worth naming

**Artifact-path contradiction.** R-108/R-111/R-112: three skills instructed writing an artifact to
a path their own agent's registry `produces` contradicted. The audit method that found them has a
stated blind spot — "checking a skill's declared save path against the registry glob finds a
*missing* path, not a *contradicting* one" — and the inverse check (`artifact-paths`) only landed
on 2026-09-13, three days after the merge.

---

## 6. What verified completion at the time?

### 6.1 The 224 checkboxes

Zero are ticked, and that is not neglect — it is an artifact of where the state lived. R-24
records it: the execution ledger lived in `.superpowers/sdd/`, "which is git-ignored and **deleted
when the plan finishes**. Everything below would otherwise have been lost, and several of these
decisions changed how the pipeline behaves." The plan file was committed at the **end**
(`82212b8`, 2026-09-10), in its pre-execution form. The handoff says how to read it: "**Treat it
as the argument as it stood before execution**, not as instructions — R-92…R-136 record where
execution found it wrong."

So the checkbox count answers nothing. What actually verified completion was four things, and the
ruling log (R-11) is blunt about one of them:

1. **Per-task red-before-green against the fixture** — real, and Shape 2 bounds what it proves.
2. **An independent review after each task** — this is the machinery that produced R-1…R-136, and
   it is the single most effective thing in the whole record. It caught R-104 (65 unreachable
   weight points), R-110, R-108/111/112, R-113, R-131. Every one of those was invisible to every
   gate.
3. **The gates themselves** — `check_fork.sh` (56 criteria at the merge per the handoff; `tested:` **57** today), `check_install.sh`, `audit_graph.py`.
4. **The fixture harness** — 33 mechanical checks.

`tested:` all four are green today. R-127, written at the moment the branch was declared complete,
already states the limit: "**Do not read this branch's green as live validation.** The mechanical
tier is thorough and the judgment tier was reviewed; the runtime tier is entirely ahead."

And R-11 records that the plan's *prose estimates* — the numbers a reader would use to sanity-check
progress — "were wrong in every instance measured (residue 250–350 → **109**; paths ~150/~66/~44 →
**203/8/109**; dangling 66 → **75**; `d1-restored` 15 → **14**). Its *code* was accurate
throughout. Measure, don't trust."

### 6.2 "The suite passes but tests component behaviour, not whether components are connected"

**Confirmed for the overhaul; partly refuted for the tree as it stands — with a sharp boundary.**

`tested:` the suite today is **175 tests in 16 `test_*.py` files**, and it runs OK in 127 s. At the
moment of the merge it was **62** (the handoff's own count, corrected the same day to 75 after the
compaction-hook tests). So roughly two-thirds of today's suite postdates the overhaul.

`tested:` dating every test file by `git log --diff-filter=A`:

| Added in the window (2026-09-08 → 09-10) | Added after (09-13 → 09-16) |
|---|---|
| `test_pipeline.py`, `test_registry_lib.py`, `test_check_refs.py`, `test_check_paths.py`, `test_critic_pairing.py`, `test_dispatch_log.py`, `test_compaction_hooks.py`, `test_prose_number_check.py` | `test_audit_graph.py`, `test_check_install.py`, `test_apply_lock.py`, `test_check_install_clone_links.py`, **`test_review_contracts.py`**, `test_session_guard.py`, **`test_skill_contracts.py`**, `test_submit_gate.py` |

**Every connectivity test in the repo is in the right-hand column.** `per file:`
`tests/test_skill_contracts.py` (read in full) asserts that "A bundled file must be named in the
step that reads it, or in the agent that reads it", and its docstring says why: a catalogue table
"tells the model what exists, never when to read it, so the model either reads nothing (the file
rots into an orphan that contradicts its inline summary) or reads everything defensively. **Both
were found across this tree on 2026-09-15.**" `per file:` `tests/test_review_contracts.py`'s
docstring: "Each test pins a defect the 2026-09-13 adoption runs surfaced, where two shipped files
disagreed and the agent followed whichever one it happened to read." Both were written *after*
running the thing found what reading it had not.

**The boundary, which matters more than the headline.** The connectivity tests that now exist test
**documentary** connection — does file X name file Y; do two documents state the same invariant
list; does a declared save path match a registry glob. None tests **runtime** connection.
Specifically, `tested:`

- `grep -l "tools:" tests/*.py` → **no matches.** No test reads an agent's tool declaration. G2
  (nine agents told to write with no `Write`) is invisible to the entire suite.
- `grep -l "settings.json" tests/*.py` → **no matches.** No test reads a project's hook wiring.
  H1 (`context-monitor` in 0 of 6) and H2 (`install-check` in 0 of 6) are invisible.
- No test dispatches a subagent. The only exercise of "does dispatching X actually cause Y to run
  and produce Z" is `tests/run_fixture.sh --live`, which per the handoff **has never completed
  green** — its last run "ended `FAIL [live-pipeline] exit 1` after 126 dispatch events."
- `test_skill_contracts.py`'s scan is scoped to `skills/**/*.md`. `ai-audit/` is not under
  `skills/`, so G3 is outside its reach by construction.

So the characterisation is right in the way that counts: the suite is excellent at pinning a
function's behaviour and a document's internal consistency, and it has **no instrument at all** for
"is this thing reachable from where it is supposed to be reached from." Three of the five
established gaps (G2, G3, G5) and both new findings (H1, H2) sit precisely in that hole, and every
one of them was found by a human tripping over it rather than by anything in `tests/`.

---

## 7. The one-sentence verdict

The overhaul delivered its **architecture** — a machine-readable registry, an executable lifecycle,
a driver, a fixture, a dispatch log and a per-project state file are all real, all exercised in six
live paper repos, and all green today — and it delivered its **instruction-layer cleanup**; what it
did not deliver, and never modelled, is the answer to *what invokes each thing it built*, which is
why 7 of the 22 non-clean rows are things that exist and nothing reaches, and why the two defects
found while writing this audit are the same defect the repo diagnosed as R-136 thirteen days ago.

