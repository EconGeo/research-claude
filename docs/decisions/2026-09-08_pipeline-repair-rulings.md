# Pipeline Repair — Ruling Log

**Date:** 2026-09-08 / 09 · **Status:** Live record of an in-progress repair
**Plan:** `docs/superpowers/plans/2026-09-08-pipeline-repair.md`
**Spec:** `docs/superpowers/specs/2026-09-08-pipeline-repair-design.md` (v2, approved)
**Branch:** `pipeline-repair`

## What this is, and why it exists

The pipeline repair was executed task-by-task with a fresh implementer per task and an
independent review after each. Wherever the plan was ambiguous, self-contradictory, or wrong,
a decision was made and recorded rather than the work stopping. This file is that record.

It was promoted here from the execution ledger because that ledger lives in
`.superpowers/sdd/`, which is git-ignored and **deleted when the plan finishes**. Everything
below would otherwise have been lost, and several of these decisions changed how the pipeline
behaves — not just how it was built.

**Read §1 before changing the pipeline.** Those rulings are load-bearing: they explain why
things that look wrong are deliberate, and why some obvious "improvements" would reopen defects
that took real work to find.

**Read §2 and §3 before trusting a gate.** Three checkers have known, permanent blind spots.
A green gate does not mean what you might assume in the specific cases named there.

Rulings are numbered R-1…R-58 in the order they were made. Where a later ruling reversed an
earlier one, both are shown — the reversal is usually the more interesting record.

---

## §1. Standing design decisions

These changed the pipeline's behaviour and outlive the repair.

### R-38 · Literature and data gate strategy on quality, not existence — *user decision*

`strategist` previously required only that `positioning.md` **or** `data_sources.md` exist. A
literature review that scored 40 did not block strategy work.

A tenth predicate type, `score-if-scored`, now gates it: a component that **has** been scored
must be ≥ 80; a component never scored is ignored. So literature 40 + data unscored **blocks**;
literature unscored + data 90 passes; literature 40 + data 90 **blocks**.

Chosen over two alternatives: a strict AND on both scores (would reverse plan decision P-16 and
block a legitimately single-track project), and an `any_of` over two score predicates (cheap,
but a bad literature review still passes when the data assessment scored well — the exact hole
being closed).

**Three hazards, each pinned by a uniquely diagnostic test.** Stub any one and exactly one test
reddens:
- The branch **requires the state file to exist**. Reusing the `score` branch's
  `{"components": {}}` default would make "no state file" indistinguishable from "not scored",
  and the gate would pass vacuously on any project that never ran `state init`.
- It tests `is None`, never truthiness. A genuine score of `0.0` is present in the state and
  must fail the gate.
- It reads `components` only, never `sections`.

### R-42, R-44, R-45 · A creator cannot close its stage on a stale critic score — *user decision*

`rules/lifecycle.md` promised that a creator cannot be marked complete without its critic's
completion **and its critic's score**. Only the first half was implemented.

The path to the fix is worth recording, because two intermediate positions were wrong:

- **R-42** added `{type: score, component: <own>, min: 0}` to seven creators' `produces`
  (`min: 0` reads as "has been scored at all"). It excluded `storyteller`, whose component is
  `none`.
- **R-44** — *the controller was wrong.* R-42 argued the shared `code` component was safe
  because `critic-ran` binds the ordering. It does not: `critic-ran` proves the **critic ran**
  after the creator, and `score min: 0` proves **a score exists**. Neither proves the score was
  **recorded** after the creator ran. A stale score from an earlier round satisfied `post` for
  all seven creators. Demonstrated, not argued.
- **R-45** — *superseded R-44's remedy.* Both halves now live in `critic-ran`, and the seven
  declared entries were **removed**. Keeping them would have rendered `code score ≥ 0` in
  `permissions.md` as a claim **weaker than the real gate**, while the real gate hid behind a
  line reading "paired critic completed after the creator". The implementer sharpened this:
  those entries were not merely decorative but *actively reassuring* — an auditor saw
  `ok code score ≥ 0 (have 85.0)` sitting green directly above a stale-score PASS.

  The decisive argument: **`critic-ran` is auto-appended for every agent with a critic, so it
  cannot be forgotten.** Seven hand-maintained entries can be, and forgetting one is the
  original defect's shape.

`critic-ran` now emits three distinct messages — critic never ran / ran but recorded no score /
score is from an earlier round — because collapsing them would have been a usability regression
on the clearest error in the system.

### R-47 · One limitation this does **not** close

`data-engineer` and `coder` share component `code`. A single `coder-critic` score satisfies both
`post` calls when it postdates both creators, even though it reviewed only the coder's work.
The state entry records **who** scored and **when**, never **what** was scored, so no timestamp
comparison can recover it.

Closing it properly needs a `for: <creator>` field on the score entry, or a distinct component
for `data-engineer`. Documented in `rules/lifecycle.md` rather than left implicit.

### R-57 · Talks use `{{< embed >}}` via a symlink — *user decision*

Quarto's `{{< embed >}}` **works** on 1.9.37, but only when the talk and its source manuscript
resolve within the same directory. An earlier test concluded it was unusable; a seven-variation
investigation overturned that.

The condition, and the mechanism: `safeRemoveDirSync` compares the embed's freshly-created
`_files/mediabag` (created beside the **source**) against the **rendering** file's directory and
throws when they differ.

**The adopted pattern:**
- `talks/` holds a **relative** symlink named after the declared manuscript, pointing at
  `../<manuscript>`. Relative, so a coauthor's clone keeps working.
- Talks embed the **bare filename**. An embed with `../` fails — verified repeatedly.
- **`/talk` owns creating the symlink**, resolving the manuscript via `pipeline.py manuscript`.
  `apply.sh` cannot: the manuscript's name is per-project and the installer does not read the
  `CLAUDE.md` declaration.
- No conflict with `check_install.sh`'s committed-symlink check, which scans only the dirs in
  `LINKED`; `talks/` is not among them.

This keeps `talks/` exactly as the registry declares it **and** keeps figures automatically in
sync with the manuscript. The rejected fallback would have hardcoded
`manuscript_<project>_files/figure-pdf/<label>-1.pdf` into every talk — depending on the files
directory surviving, the figure format staying PDF, and Quarto's label-to-filename convention
holding.

### R-34 · A quality gate moved rather than vanished

The old `rules/agents.md` said "no artifact advances without its critic's score ≥ 80". The
rewrite drops it, and only `strategy`, `code`, `manuscript` and `overall` are score-gated in the
registry.

Accepted, because the ≥ 80 floor **moves** rather than disappearing: `quality.md` gates
submission on overall ≥ 95 **and every scored component ≥ 80**. The trade is per-handoff
blocking for a submission-time floor.

One sharp edge, found in review: submission gates every **scored** component. A component scored
low still blocks; a component **never scored at all** is excluded and the weights renormalise.
(R-38 closes this for literature and data specifically.)

### R-49 · Timestamps are UTC with an explicit offset

`critic-ran` now compares a timestamp in `pipeline_state.json` (**committed**, shared between
machines) against one in `agent_dispatch.jsonl` (**git-ignored**, local). Local-time ISO strings
would acquire a cross-machine failure mode and an annual DST fall-back window.

**Any future writer of the dispatch log must use the same format** — UTC, explicit offset,
millisecond precision. `hooks/dispatch-log.py` in particular.

### R-39 · Millisecond resolution is load-bearing, not cosmetic

`critic-ran` compared second-resolution timestamps, so a creator and critic logged in the same
second compared **equal** and the gate concluded the critic never ran. The covering test passed
only because an incidental 8.7-second render separated them; with the fixture pre-rendered it
failed 8 times in 10.

Fixed by raising resolution — **not** by relaxing the comparison to `>=`, which would let a
critic logged *before* its creator count as having run after.

### R-32 · A gate property was deliberately demoted

Criterion 9a's *dynamic roster* check (fail on any `*-critic` token naming no agent file) is not
subsumed by `deleted-things`, which is a fixed six-name blocklist — a future `data-critic` would
escape. The property survives in `audit_graph.py` and is a Task 8.7 sign-off criterion.
**Intentional demotion from per-commit gate to merge-time acceptance check.**

---

## §2. Permanent tooling limitations — read before trusting a gate

### R-18 · `check_paths.py` cannot see skill-relative references

Its `PATH_RE` only matches references beginning with one of the seven pipeline dirs. A reference
like `design-checklists/x.md` is **invisible** to it. `audit_graph.py` sees 12 such dangling refs
that `check_paths.py` misses.

**Consequence:** any worklist built from `check_paths.py --list` alone is incomplete. Use the
**union** with `audit_graph.py`'s dangling list.

### R-21 · `check_paths.py` invents false positives on globs and placeholders

Its `PATH_RE` tail cannot consume `{` or `*` and must end on a word character, so
`.claude/references/coding-standards-{lang}.md` backtracks to `…coding-standards` and is reported
as a missing file nobody wrote.

**Do not "fix" these references.** Flattening a correct placeholder into a literal filename
creates a real dangling reference in order to satisfy a regex bug. R-18 yields false *negatives*;
R-21 yields false *positives*.

### R-33 · Gates name absent things on purpose

`check_fork.sh` cites `agents/orchestrator.md`, `rules/workflow.md` and five others **precisely
to assert they do not exist**. `check_paths.py` cites `templates/quarto-preamble.tex`, a
project-level path that never exists in the repo. Nine such references can never resolve.

A tool that counts dangling references must honour the repo's `residue:prohibition` /
`residue:historical` markers, or two stage-exit criteria (`dangling = 0`,
`agents named, not on roster: []`) are structurally unreachable.

A second, unrelated noise source: `audit_graph.py`'s `AGENT_RE` matches `five-critic` inside a
sentence describing *another tool's* feature, and `worker-critic`, a generic term already
exempted in `check_refs.py`.

### R-19, R-22 · `check_refs.py` gaps

- `deleted-things` misses a **bare** `guide/` reference (the regex requires a trailing slash) — a
  false *negative*, the dangerous kind, since it lets a real reference survive behind a green gate.
- `hooks-readme` over-matches a second, unrelated backticked table in the README.
- 13 of the 16 `SLASH_ALLOW` suppressions exist only because `SLASH`'s lookbehind omits `}` and
  `]`. They are global and permanent, and `results` / `assumptions` / `proofs` are generic enough
  that a future genuine `/results` skill reference would be silently accepted. **If that
  lookbehind is ever widened, remove those 13.**

### R-54 · BSD vs GNU: `sed` does not support `\s`

macOS `grep -E` honours `\s`; macOS `sed -E` **does not** and silently returns nothing. This made
`manuscript-declared` unable to ever PASS. Use POSIX classes (`[[:space:]]`) in `sed`.

Verified clean: `find`'s `-maxdepth`, `-not -path` and `-print -quit` are all BSD-portable.

### R-53 · `grep -c` prints output *and* signals failure

`decl="$(grep -c … || echo 0)"` yields `"0\n0"` when the file exists with zero matches, because
`grep -c` prints `0` **and** exits 1. Both numeric tests then throw an arithmetic error and fall
through, making a branch unreachable. `grep -c` is unusual this way — an audit found no siblings
in the same file.

### R-48 · Nothing catches a missing renderer branch

Remove an `elif` from `render_registry.pred()`, re-render, and the contract silently degrades to a
bare type string while **all five registry verdicts stay green** — `registry-rendered` only checks
the file matches the render. A test asserting "no predicate renders as its bare type string" closes
this.

### R-50 · What is enforced must also be rendered

`critic-ran` was **absent from `permissions.md` entirely**, because no agent declares it — it is
appended at evaluation time. Everyone had been checking that what *is* rendered is accurate;
nobody checked that what is *enforced* gets rendered. The one gate binding every creator was
invisible in the contract shipped to six repos.

---

## §3. Defects found and fixed

| # | Defect | Where it came from |
|---|---|---|
| R-39 | `critic-ran` broken at second resolution; its test passed on an incidental render | plan's code |
| R-40 | `test_post_strategist_sections` was a tautology — the `section` predicate had **no** coverage | plan's code |
| R-41 | Shipped prose promised score enforcement that did not exist | plan's code |
| R-30 | `scripts-manifest` printed a green `PASS` row *alongside* its own failures | plan's code |
| R-53 | `manuscript-declared`'s WARN branch unreachable | this session, Task 1b.1 |
| R-54 | `manuscript-declared`'s PASS branch unreachable on macOS | plan's code |
| R-52 | `rules/logging.md:42` named a deleted agent, with **no task owning the file** | plan inconsistency |
| R-25→R-27 | Private project names shipping in `scripts/prose_number_check.py` | pre-existing, newly exposed |
| R-15 | Fixture data untracked — the gate would fail on a fresh clone for the wrong reason | plan cross-ref |

### R-27 · The leak that was already shipping

Widening the identity scan to cover `scripts/` exposed **two private project names** in
`prose_number_check.py`'s docstring and rationale comments — a file symlinked into **all six**
paper repos, invisible because the old gate never scanned `scripts/`. (The names are deliberately
not repeated here; `git log -p scripts/prose_number_check.py` shows what was removed.)

The first remedy (mark them `residue:historical`, by analogy with the plan's clo-author credits)
was **overturned in review**: those credits name a *public* upstream project, so there is no
disclosure interest. These are the user's *private, unpublished* projects, and `research-claude`
is a **public repo** whose stated purpose is that a coauthor can clone it without an access grant.
The corrected fix keeps every word of rationale and deletes only the identifiers.

**R-28** found a sibling the controller missed: `cc-pogm-half`, a criterion *label* embedding a
project noun, escaping only because grep is case-sensitive. Renamed — "leaving the latent one
turns an accident into a precedent".

---

## §4. Process rulings

- **R-1 (scope).** Execution covers Stages 0–7b, worktree-only. Every write to the shared
  checkout, to `~/Research/*`, or to a remote is deferred to the user. Read-only inspection of
  those paths is permitted and was used.
- **R-2.** The live tier (driving a `claude` session) is not executed; hooks are proved by
  piped-payload tests, the mechanical tier the plan itself defines.
- **R-10.** Every edit locates its target by **quoted text**, never by the plan's line numbers —
  the plan declares its own agent line numbers stale.
- **R-11, R-23, R-26, R-20.** The plan's *prose estimates* were wrong in every instance measured
  (residue 250–350 → **109**; paths ~150/~66/~44 → **203/8/109**; dangling 66 → **75**;
  `d1-restored` 15 → **14**). Its *code* was accurate throughout. Measure, don't trust.
- **R-12.** A residue hit inside a **partial line-range** clean mark in the sweep still counts as
  "a file the sweep lists as clean" and needs an Addendum row.
- **R-13.** A red gate during Stage 0 is the design, not a defect. Only `project-identity` and
  `project-nouns` must be green at every commit.
- **R-24.** The workspace is deleted at plan end. **Anything recorded only there is lost** — which
  is why this file exists.
- **R-37.** `__pycache__/` and `*.pyc` added to `.gitignore`; the suites generate bytecode and a
  `git add tests/` would have committed it.
- **R-17.** Fix rounds land as new commits, never as amends of a reviewed commit.

---

## §5. Deferred — outstanding for the maintainer

Everything here was deliberately **not** executed under R-1. None of it is blocked; all of it is
outward-facing.

| Item | Source |
|---|---|
| `.gitignore` edits in all six paper repos (`gitignore-covers` FAIL ×6 until done) | Task 2.3 Step 3 |
| Declare `manuscript:` in `~/Research/POGM4/CLAUDE.md` | Task 1b.1 Step 2 |
| Re-link POGM4 to the worktree as the canary | Task 2.5 |
| ZotPilot fork: fix `seed-papers/SKILL.md`, PR, re-vendor | Task 6.4 |
| Wire hooks in the six repos' `settings.json` | Task 7.5 Step 3 |
| Stage 8 entirely — legacy migration, merge, re-link, lock bump, push | Stage 8 |
| `stash@{0}` and branch `fix/critic-dispatch` still exist (content preserved as a patch and a cherry-pick) | R-5 |
| The `detached at the lock SHA` branch of the `branch` check is untested | Task 0.8 |

---

## §6. Deferred minors

Recorded, judged non-blocking, and left for triage:

- `critic-ran` now understates its own name (it checks the score too); not renamed because the
  name reaches `rules/agents.md`.
- `any_of` evaluates all branches with no short-circuit — an `any_of` containing a `render` would
  render per branch. Not currently exercised.
- A failing `pre` still runs `quarto render` and writes the PDF: a refused pre-dispatch check
  mutates the working tree.
- `registry-parse-agree` degrades to `SKIP` under a 3.9 `python3` without PyYAML, and the exit
  code is untouched — silently non-enforcing on such a machine. It reads PASS today only because
  `check_fork` invokes 3.12.
- `post writer` after a section-only draft fails with a message that reads like a corrupt state
  file. `lifecycle.md` explains it; the runtime message does not.
- Strict `>` on millisecond timestamps fails closed on a same-millisecond tie — unreachable via
  the CLI, but the message would confuse.
- `latex-residue`'s old `Emory` institution-name pattern has no successor. Zero hits today, but
  the institution-name class is now uncovered.
- Most of `check_paths.py`'s `EXEMPT_PREFIX` is unreachable by construction; only
  `scripts/acquire/` is live. Do not read the exempt set as evidence those classes were tested.
- **R-58:** `tests/run_fixture.sh` does not render `talks/`, so the embed pattern the talk path
  now depends on is **not exercised by the gate at all**. The check must assert exit 0, an
  `img`/`svg` whose target exists above a size floor, a real coefficient inside the table region,
  and must run once warm and once from a clean tree.

---

## Appendix — full index

Superseded rulings are marked; both halves are kept because the reversal is usually the record
worth having.

| # | One line |
|---|---|
| R-1 | Scope: worktree-only; writes outside it deferred to the user |
| R-2 | Live tier not executed; hooks proved by piped-payload tests |
| R-3 | Worktree identity differs from the plan's path and branch name |
| R-4 | Baseline recorded in the worktree, not on `main` |
| R-5 | Cherry-pick executed; destructive stash/branch deletions deferred |
| R-6 | Task 2.3's heading says three checks, its body specifies two — follow the body |
| R-7 | `coder-critic.md` must retain `Correctness Layer` and `INV-23` |
| R-8 | Fixture `.gitignore` refresh belongs to Task 2.1, not 2.4 |
| R-9 | Fixture `settings.json` is created in Task 5.3, not 0.3 |
| R-10 | Locate by quoted text, never line number |
| R-11 | Residue baseline is 109, not the estimated 250–350 |
| R-12 | Partial line-range clean marks count for the Addendum rule |
| R-13 | A red gate in Stage 0 is the design |
| R-14 | Fixture chunk order: `build-panel` moves above `# Introduction` |
| R-15 | Fixture `panel.csv` must be tracked |
| R-16 | `.here` sentinel kept, with a README sentence |
| R-17 | Fix rounds are new commits, never amends |
| R-18 | `check_paths.py` cannot see skill-relative refs |
| R-19 | Two `check_refs.py` regex gaps, each tied to the task where it comes due |
| R-20 | The brief's `inv-refs` prediction was wrong; the checker was right |
| R-21 | `check_paths.py` invents false positives on globs/placeholders |
| R-22 | 13 `SLASH_ALLOW` tokens are lookbehind workarounds; remove if it widens |
| R-23 | `tail -1` does not show `check_paths.py`'s totals |
| R-24 | The workspace is deleted at plan end; durable records go in `docs/` |
| R-25 | *(superseded by R-27/R-28)* Mark the identity-scan hits |
| R-26 | `d1-restored` is 14 of 15, not 15 |
| R-27 | **Supersedes R-25 B/C:** delete private project names, don't mark them |
| R-28 | **Supersedes R-25 A:** rename criterion labels embedding project nouns |
| R-29 | `scan()` honours `residue:prohibition`; the marker must follow a `#` in bash |
| R-30 | `scripts-manifest` printed a false PASS |
| R-31 | Repo-maintenance scripts must be exempt from `path-resolves` |
| R-32 | 9a's dynamic-roster property intentionally demoted to a sign-off check |
| R-33 | Gates name absent things on purpose; the graph tool must honour markers *(amended twice)* |
| R-34 | The ≥ 80 floor moved to submission rather than vanishing |
| R-35 | A scheduled `registry-authority` hit, recorded so Task 4.5 need not rediscover it |
| R-36 | Three CLI errors in `lifecycle.md` corrected |
| R-37 | `__pycache__/` gitignored |
| R-38 | **User:** literature and data gate strategy on quality |
| R-39 | `critic-ran` broken at second resolution |
| R-40 | A tautological test left the `section` predicate uncovered |
| R-41 | Shipped prose promised enforcement that did not exist |
| R-42 | **User:** enforce the critic-score half |
| R-43 | `lifecycle.md` corrections moved into the task already rewriting it |
| R-44 | **Controller was wrong:** the staleness hole is real |
| R-45 | **Supersedes R-44's remedy:** fold both halves into `critic-ran`, drop the seven entries |
| R-46 | The conceded-false claim was already shipped; prose fixed with the code |
| R-47 | The shared-component hole survives; documented, not hidden |
| R-48 | Nothing catches a missing renderer branch; add the guard test |
| R-49 | Timestamps go UTC with an explicit offset |
| R-50 | **Controller's instruction was unworkable:** `critic-ran` was unrendered entirely |
| R-51 | The harness reorder was incomplete; a second step had to move |
| R-52 | A plan inconsistency with no owning task |
| R-53 | `grep -c` prints *and* fails; a branch was unreachable |
| R-54 | BSD `sed` lacks `\s`; a criterion could never pass |
| R-55 | Don't accept the embed fallback without probing the failure |
| R-56 | The embed record must be corrected regardless of layout |
| R-57 | **User:** keep `talks/`, embed via a relative symlink |
| R-58 | The harness does not exercise the embed pattern |
