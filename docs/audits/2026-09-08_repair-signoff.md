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

## Not done, and deliberately

| Item | Why |
|---|---|
| zoning2026: 21 `.tex` fragments into chunks, 41 prose literals | Substantive research refactoring; a wrong number changes a claim. Wants a human reading the diff. |
| ESG: 7 numbered analysis scripts into chunks, 14 literals | Same class. |
| POGM4: archive `scripts/R` (16 scripts), remove `.claude/WORKFLOW_QUICK_REF.md` and `commands/` | Held while a live session was mid-round in that project. |
| NAR_settlement: 54 prose literals | The plan anticipated 2. Most are not results — `17 August 2024` is the settlement date, `Section 6.2` and `Sonnet 4.6` are cross-references. Each needs an allowlist row with a real reason. Bulk-adding 54 rows to turn a gate green is the failure this pipeline exists to prevent. |
| ZotPilot fork PR (Task 6.4) | Pushes and merges on a shared remote. |
| Stage 7b's `~/Research` half | The shared `journal-profiles.md` still says `JHE` where the repo now says `JHousE`; the two disagree until renamed. |
| `/pipeline` driver, live | Never run. The largest single artifact built — a skill plus eleven references — and the abstract test exercised `/write`, not the driver. |
| `run_fixture.sh --live`, Tasks 5.6/5.7 | Still untested. |

**What the live run did and did not establish.** It proved the enforcement chain: the hooks
fire, the log shape is what `critic-ran` reads, the score gates the draft, staleness is
enforced. It did not exercise the driver, `pipeline.py post` in production, or five of the six
repos.
