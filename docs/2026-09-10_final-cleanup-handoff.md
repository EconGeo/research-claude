# Handoff — final cleanup after the pipeline repair

**Written:** 2026-09-10, at the end of the repair session, by a session that had become
worktree-isolated and could no longer reach git or write into the checkout.
**For:** a fresh session rooted at `/Users/andrew.mueller/Academic/research-claude`.

**First:** move this file into the repo and commit it, or delete it once acted on.

```bash
mv ~/pipeline-repair-handoff.md docs/2026-09-10_final-cleanup-handoff.md
```

---

## Where things stand

The pipeline repair is **merged, pushed, and live**. `main` is at `7268017`. The repair worktree
has been removed; `git worktree list` shows one checkout.

```
✓ check_fork:    PASS      56 criteria, 0 failures
✓ check_install: PASS      six repos
✓ run_fixture:   PASS      32 checks
  unittest                 59 tests
  audit_graph              dangling 0 · roster [] · never-invoked []
```

All six paper repos are on the repaired pipeline: linked to this checkout, lock at the merge
commit, `dispatch-log.py` and `critic-pairing.py` wired into each `settings.json`, manuscripts
declared (BRI excepted — it has no `.qmd` yet and correctly refuses to run).

**Read these before changing anything:**

| Document | What it is |
|---|---|
| `docs/decisions/2026-09-08_pipeline-repair-rulings.md` | R-1…R-136. The durable record. §1 explains why things that look wrong are deliberate; §2 lists permanent gate blind spots. **Read §1 and §2 before "improving" anything.** |
| `docs/audits/2026-09-08_repair-signoff.md` | What was done, what was not, and why. Includes the first live run and what it proved. |
| `docs/audits/2026-09-08_stage0-red.md` | Per-stage red-before-green record and sign-offs. |
| `docs/superpowers/plans/2026-09-08-pipeline-repair.md` | The plan. **Treat it as the argument as it stood before execution**, not as instructions — R-92…R-136 record where execution found it wrong. |

---

## 1. Immediate cleanup (this is the ask)

### 1a. Drop the stash

```bash
git stash list
```

Confirm the entry reads `On fix/critic-dispatch: WIP Task 2: /discover lit -> /lit-position
pointer`. **The stash stack is shared across every worktree and checkout on this machine**, so
`stash@{0}` is not guaranteed to be that entry — drop by the index that matches, not by position.

```bash
git stash drop stash@{N}
```

Nothing is lost: that work was folded into the tree as Task 6.1, and the diff is committed at
`docs/audits/2026-09-08_stash-discover-lit.patch`.

### 1b. Delete `fix/critic-dispatch`

```bash
git branch -D fix/critic-dispatch
```

`-D`, not `-d`: it carries one commit not in `main`, `cd1d47a test(check_fork): criteria 9a/9b —
no skill may name a deleted agent`.

**Be precise about what was verified.** The shipped `check_refs.py` has a `deleted-things`
criterion covering deleted-agent naming, and it passes. Nobody diffed `cd1d47a` against that
implementation, so it is not established that the branch's version is identical — only that the
capability exists and is green. If you want certainty, diff it first. After deletion the commit
stays reachable in the reflog for ~90 days: `git branch fix/critic-dispatch cd1d47a`.

---

## 2. Real work still outstanding

Ordered by how much judgment each needs. **None is mechanical.**

### 2a. Prose literals — 54 NAR, 41 zoning2026, 14 ESG

`prose_number_check.py` fails in three repos. The plan predicted 2 for NAR; there are 54, because
the manuscript grew.

**Most are not results and cannot become inline expressions.** `17 August 2024` is the settlement
date. `Section 6.2`, `Table 4`, `Sonnet 4.6` are cross-references and version strings. Each needs
an allowlist row **with a real reason**, decided one at a time against its context.

**Do not bulk-add rows to turn the gate green.** That is the exact failure this pipeline exists to
prevent, and the ruling log says so in several places. If a literal is a *result*, it becomes an
inline `` `r ` `` expression; if it is a fact about the world, it gets a row explaining why.

### 2b. ESG's seven analysis scripts — deliberately untouched

Stage 8.4 said to fold them into the manuscript. **This was not done, on purpose.** ESG's
manuscript is a 154-line skeleton whose abstract reads `PLACEHOLDER — rewritten at Stage G, after
the results set is frozen (plan F-3)`. The project is mid-analysis under its own staged plan.
Folding its scripts in now fights that plan rather than serving it.

Revisit when ESG's own results set is frozen — not before.

### 2c. Three other plan instructions not followed

Each is recorded with its reasoning in the sign-off. Reverse any of them if you disagree, but read
the reason first:

- `ESG/scripts/generate_dashboard.py` kept. D-18 removed the dashboard from the *shipped
  pipeline*, not from a project's own tooling; it is documented in ESG's `CLAUDE.md` and preserves
  authored content in `dashboard_state.json`.
- POGM4's `.claude/commands/{zotero-notes,zotero-review}.md` kept. Usage could not be established,
  `obsidian-digest-sync` was dropped from the shipped tree, and nothing replaces them.
- POGM4's `scripts/acquire/lock_market_list.R` kept live rather than archived with the rest of
  `scripts/R`. The manuscript points at it in three comments and a `stopifnot` message; archiving
  it would have left an error telling a user to run a missing file.

### 2d. ZotPilot fork PR (Task 6.4)

`zotpilot-skills/seed-papers/SKILL.md` names the retired `librarian` seven times and `/discover
lit` four times. The fix belongs **upstream** in `EconGeo/ZotPilot`, then re-vendored via
`scripts/sync-zotpilot-skills.sh`.

`zotpilot-skills/` is vendored verbatim and never edited in place — a local patch is destroyed by
the next sync. This needs a push and a merge on a shared remote, which is why it was deferred.
Its residue is WARN-tier and blocks nothing.

### 2e. `JHE` / `JHousE` disagreement

`references/journal-profiles.md` in this repo now calls the housing journal `JHousE`, because
`JHE` was already taken by Journal of Health Economics. **The shared
`~/Research/.claude/references/journal-profiles.md` still says `JHE`.** The two files currently
disagree. Rename there too.

While in that file: check for the `ReStud` vs `REStud` casing bug that was found and fixed in this
repo's `discipline-cards.md` — a cross-reference that reads correctly and matches nothing.

### 2f. Live tier — `run_fixture.sh --live`, Tasks 5.6/5.7

Still never run. The harness's `--live` path invokes `claude -p '/pipeline run --until analyze
--yes' --permission-mode acceptEdits` against a fixture copy.

**`/pipeline` itself has never run.** It is the largest single artifact built — a skill plus eleven
per-stage reference files — and the only live exercise so far was `/write`, not the driver. The
cheapest first test is `/pipeline status` in a project with a declared manuscript.

---

## 3. What the live run established, and what it did not

`/write abstract` in POGM4 on 2026-09-10 was the first execution of any of this outside a test
harness. It proved the enforcement chain end to end:

- the SubagentStop hook fires and writes UTC millisecond timestamps (R-109);
- the score gates the draft — 76 recorded, below 80, strike 1, writer re-dispatched;
- the writer's next dispatch postdates the score, so `critic-ran` correctly treats that 76 as
  **stale** (R-44/R-45, the defect that took the most work to establish);
- `critic-pairing.py` blocked once then went advisory (R-116/R-117);
- the section score landed in `sections`, not on the `manuscript` component (R-101).

It also produced the clearest evidence for R-135: `prose_number_check.py` **passed**, and the
critic still caught a retyped `(1983--2024)` where `YEAR_START`/`YEAR_END` are live objects. The
gates are denylists of known-bad strings. They do not detect the properties they are named for.
**State results that way** — "no known violation is present" rather than "the tree has the
property."

**Two defects existed only because something finally ran:** `__pycache__` written into the linked
`.claude/scripts/`, and `is_fresh()` accepting a stale `.docx` because a newer `.html` sat beside
it. Both fixed. Expect more of this class as the live tier is exercised.

---

## 4. Two things that will bite

**Submodules live in six places.** Removing them properly means the index gitlink, `.gitmodules`,
the working directory, `.git/modules/submodules/`, `.git/config`, and each worktree's own
`.git/worktrees/<name>/modules/`. Deleting `.gitmodules` first strands the rest, because every
convenience command reads it to know what to clean. This cost four failed attempts at the end of
the repair session.

**`apply.sh`'s `copy_seed` never overwrites.** A new hook added to `seeds/settings.json` reaches
**no existing project** — each `.claude/settings.json` must be edited by hand. All six are wired
now; the next hook added will need the same pass. This is R-136.
