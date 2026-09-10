# Pipeline Repair — Sign-off

**Date:** 2026-09-10 · **Merge:** `8bb6218` on `main` · **Branch:** `pipeline-repair`, 96 commits
**Spec:** `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (v2)
**Plan:** `docs/superpowers/plans/2026-09-08-pipeline-repair.md`
**Rulings:** `docs/decisions/2026-09-08_pipeline-repair-rulings.md` (R-1…R-136)

---

## Gates, on `main`

```
✓ check_fork:    PASS      56 criteria, 0 failures
✓ check_install: PASS      six repos
✓ run_fixture:   PASS      32 checks
  unittest                 57 tests, 0 failures
  registry check           5 PASS, 0 FAIL
  audit_graph              dangling path refs: 0
                           agents named, not on roster: []
                           roster agents never dispatched anywhere: []
                           skills never invoked: []
  check_paths              0 unresolved, 0 unprefixed (non-vendored)
```

## The six repos

| Repo | Commit | Manuscript declared |
|---|---|---|
| POGM4 | `80b6425` | `manuscript_quarto_word.qmd` |
| zoning2026 | `9626f1d` | `paper/manuscript.qmd` |
| affordable_housing_2026 | `b5fdb8b` | `manuscript_affordable_housing_2026.qmd` |
| ESG | `0512c30` | `manuscript.qmd` |
| NAR_settlement | `790a13a`, `a8a75f8` | `manuscript_NAR_settlement.qmd` |
| BRI | `128140a` | none — no `.qmd` exists yet |

All six: linked to the shared checkout, lock at `8bb6218`, `dispatch-log.py` and
`critic-pairing.py` wired, `.gitignore` covering the linked dirs and the local dispatch log.

BRI has no `CLAUDE.md`, so `pipeline.py manuscript` refuses — verified:

```
pipeline.py: CLAUDE.md not found — declare `manuscript: <file>.qmd` in it (D-8)
exit=1
```

That is the gate working. A project cannot run the pipeline until it says what its manuscript is.

---

## Success criterion 6 — the first live run

`/write abstract` in POGM4, 2026-09-10. **This is the first time anything in this repair executed
outside a test harness.** Until this run every gate was green on structure alone (R-127).

**The dispatch log, written by the SubagentStop hook:**

```
{"at": "2026-09-10T10:32:49.601+00:00", "agent": "writer",        "source": "hook"}
{"at": "2026-09-10T10:39:20.466+00:00", "agent": "writer-critic", "source": "hook"}
{"at": "2026-09-10T10:44:15.480+00:00", "agent": "writer",        "source": "hook"}
```

**The state file:**

```json
"sections": { "abstract": { "score": 76.0, "critic": "writer-critic",
              "at": "2026-09-10T10:39:46.254+00:00" } },
"strikes":  { "writer": 1 },
"components": {}, "overall": null
```

What each line proves:

- **R-109 held.** UTC, explicit `+00:00`, millisecond precision. The plan's own code would have
  written naive local time at second resolution, which `critic-ran` cannot compare against the
  committed state file at all, and which reintroduces the same-second equality bug.
- **R-136 held.** `"source": "hook"` — this came from `dispatch-log.py` on SubagentStop, not a
  skill's manual `log` call, so the hand-wiring of `settings.json` is what made it fire.
- **The SubagentStop field name resolved.** The plan flagged `agent_type` / `agent_name` /
  `subagent_type` as `unverified:`; the hook accepts all three and found the live one.
- **The gate held.** 76 is below 80, so `strikes.writer = 1` and the writer was re-dispatched.
  The loop ran; the draft did not reach the user unscored.
- **R-44/R-45 held, visibly.** The third line (10:44:15) postdates both the critic's completion
  and the recorded score, so `critic-ran` now correctly treats that 76 as **stale**. This is the
  defect that took the most work to establish, and it is enforced against real timestamps.
- **R-101 held.** The score landed in `sections`, not on the `manuscript` component —
  `--scope section:` diverts it, and any other scope string would have overwritten the
  whole-manuscript score. `overall: null` is correct: no component is scored yet.

**`critic-pairing.py` fired and blocked**, once, then went advisory (R-116/R-117):

```
⚠ Creator ran without its critic this session: writer → dispatch writer-critic.
```

It fired while the critic was *running* — a backgrounded subagent has no log line until it
stops — so it held the turn open until the critic landed. Correct, and the session diagnosed
the mechanism rather than re-dispatching.

**The Claim–Evidence Table was produced** with the specified vocabulary and weights: 9 rows,
7 SUPPORTED / 1 OVERSTATED (−10) / 1 UNVERIFIABLE (−5). The cold-read protocol held — the critic
declined to assert a strike count, because it does not receive the round number.

**The critic caught what the mechanical gate cannot.** `prose_number_check.py` exits 0 (94
literals, all allowlisted), and the critic still deducted for `(1983--2024)` being retyped when
`YEAR_START` and `YEAR_END` are live objects one line above `N_MARKETS` — which the same
sentence reads live. It scored it at half the rubric weight and explained why the rubric's row
does not fire on its terms. This is R-135 demonstrated rather than argued: the gates are
denylists of known-bad strings; they do not detect the property they are named for.

---

## Found by the live run

`pipeline.py` writes `__pycache__` into the **linked** `.claude/scripts/`, so `override-tracked`
failed on the first project to actually run the pipeline. Generated bytecode is never a project
override and a coauthor's clone should not receive it, so `check_install.sh` now excludes it —
rather than asking each project to commit a build artifact via a `!negation`.

Nothing else in the six repos moved.

---

## Stage 8 migrations — what happened

The plan's per-repo lines were written months before execution, and three of the six had moved.
Each was checked before anything was deleted.

**POGM4 (8.1).** `scripts/R/` — 16 scripts — archived to `archive/scripts_R_reference/`. The plan
expected the manuscript to reference it nowhere; it referenced it four times. None was a
`source()`: three comments and a `stopifnot` message pointing at `lock_market_list.R`, which
regenerates a CSV the manuscript reads. Archiving it wholesale would have left an error message
telling a user to run a file that no longer existed. It is data preparation, not analysis, so it
moved to `scripts/acquire/` and stays live; all four pointers were repointed. `execute: cache:
false` is now a declared deviation rather than an undocumented one.

**zoning2026 (8.2).** The migration the plan describes **was already done**. `paper/manuscript.qmd`
(3,870 lines) has zero `\input{}` and zero `source()`; it computes inline and reads only
`data/raw/`. The 21 `.tex` fragments were read by exactly one file — `manuscript_quarto_pdf.qmd`,
which the project's own `CLAUDE.md` marked "DEPRECATED — do not edit or render". So this was
removal of dead weight, not a port: the deprecated manuscript and its `.pdf`/`.tex` deleted,
`paper/tables/` deleted, `scripts/R/` (23 scripts) archived. `scripts/python/` kept — its 11 files
are downloaders, which the contract permits as acquisition.
`CLAUDE.md` had described `paper/tables/` as "read by manuscript.qmd". It was not; only the
deprecated file read them. Corrected.

**affordable_housing_2026 (8.3).** Legacy state file renamed and its two scores ported.

**NAR_settlement (8.5).** `compare_golden.sh` documented as a verification aid — it computes
nothing, it reads two files and calls `cmp`, so the one-manuscript contract does not reach it.

**BRI (8.6).** Nothing to migrate. `pipeline.py manuscript` refuses, correctly, with the
declaration message.

**Three things the plan called for that were NOT done, because the tree contradicted the
instruction.** Each is a judgment, and each is reversible if judged wrong:

- **ESG's seven analysis scripts stay.** Its manuscript is a 154-line skeleton whose abstract
  reads `PLACEHOLDER — rewritten at Stage G, after the results set is frozen (plan F-3)`. The
  project is mid-analysis under its own staged plan. Folding its scripts into the manuscript now
  would fight that plan, not serve it.
- **`ESG/scripts/generate_dashboard.py` stays.** D-18 deleted the dashboard layer from the
  *shipped pipeline*. This is a project's own tool, documented in its `CLAUDE.md`, preserving
  authored content in `dashboard_state.json`. Deleting it would orphan that state.
- **POGM4's `.claude/commands/{zotero-notes,zotero-review}.md` stay.** The plan offered removal or
  conversion, conditional on whether they are still used. That could not be established: they do
  Zotero-to-Obsidian reading notes, `obsidian-digest-sync` was dropped from the shipped tree, and
  nothing replaces them. They break no gate.

## Not done, and deliberately

| Item | Why |
|---|---|
| Prose literals: NAR 54, ESG 14, zoning2026 41 | The plan anticipated 2 for NAR. Most are not results — `17 August 2024` is the settlement date, `Section 6.2` and `Sonnet 4.6` are cross-references. Each needs an allowlist row with a real reason, decided one at a time. Bulk-adding rows to turn a gate green is the failure this pipeline exists to prevent. |
| ESG's seven analysis scripts | Project is mid-analysis under its own staged plan; see above. |
| Remove the repair worktree (8.7 Step 4) | It is the ground this session runs on. Must be done from a shell rooted at the shared checkout. |
| ZotPilot fork PR (Task 6.4) | Pushes and merges on a shared remote. |
| Stage 7b's `~/Research` half | The shared `journal-profiles.md` still says `JHE` where the repo now says `JHousE`; the two disagree until renamed. |
| `/pipeline` driver, live | Never run. The largest single artifact built — a skill plus eleven references — and the abstract test exercised `/write`, not the driver. |
| `run_fixture.sh --live`, Tasks 5.6/5.7 | Still untested. |

**What the live run did and did not establish.** It proved the enforcement chain: the hooks
fire, the log shape is what `critic-ran` reads, the score gates the draft, staleness is
enforced. It did not exercise the driver, `pipeline.py post` in production, or five of the six
repos.
