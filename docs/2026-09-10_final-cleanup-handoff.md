# Handoff — final cleanup after the pipeline repair

**Written:** 2026-09-10, at the end of the repair session, by a session that had become
worktree-isolated and could no longer reach git or write into the checkout.
**For:** a fresh session rooted at `/Users/andrew.mueller/Academic/research-claude`.

**First:** move this file into the repo and commit it, or delete it once acted on. **Done —
this file is that move.**

---

## Progress log (appended by later sessions; the sections below are as written)

**2026-09-10, session `01LyzZ`:**

- **§1 done.** Stash dropped (verified byte-identical to
  `docs/audits/2026-09-08_stash-discover-lit.patch` first); `fix/critic-dispatch` deleted
  after diffing `cd1d47a` — its 9a is subsumed by `audit_graph.py`'s
  `agents_named_not_on_roster` (7 dirs vs its 2) and its 9b by `check_refs.py`'s
  `deleted-things` (`orchestrator` is in `DELETED_AGENTS`, 8 dirs vs its 3); both ran green.
  The branch code was also stale — it globbed the removed `submodules/ai-audit/agents/`.
  Recover with `git branch fix/critic-dispatch cd1d47a` (~90 days). Commit `4cf76a8`.
- **§2f partially exercised.** `/pipeline status` run in POGM4 — the driver's first
  execution. `status` works end to end; `run` still untouched and `run_fixture.sh --live`
  still never run. **Do not run `/pipeline run` in a paper repo:** POGM4's state file is
  three days old, so every stage reads unstarted and the driver would start from
  `literature` and point `writer` at a 3,694-line manuscript already through three referee
  rounds. The fixture is the vehicle.
- **New defect found and fixed** by that run: an `any_of` swallowed its branches'
  `producer` hints, so `pre strategist` — the one stage a user reads `status` to unblock —
  named no skill to run. Red-first test, `producer_hint()` shared by both call sites.
  Commit `eeb21da`, merged `616d719`. Not in §6's blind-spot list.
- **§2e done.** `JHousE` now in all three real copies (repo, `~/Research/.claude/`, ESG's
  local). NAR's copy has no housing entry at all. **`JHE` deliberately kept** in the Health
  Economics entries and in `NAR_settlement/.claude/references/domain-profile.md:24`, whose
  neighbours are Health Affairs / AJHE / JHR / Medical Care — a global rename corrupts it.
  Consumer updated: `zoning2026/CLAUDE.md:134`. Backup of the unversioned shared file at
  `~/Research/.claude/journal-profiles.md.bak-2026-09-10`. Commits: ESG `ce7c32b`,
  zoning2026 `342e870`.
- **`ReStud` casing: no bug.** All copies already read `REStud`. §2e's second half is closed.
- **§2f live tier: BUILT AND EXERCISED.** `run_fixture.sh --live` now runs. Getting there
  took peeling apart six defects, listed here because the class recurs:
  1. the live tier ran in the mechanical tier's `$T`, so `live-dispatch-log` passed on
     residue — the false green: `run_fixture: PASS` with the pipeline never executed;
  2. that same residue ends on a deliberately unpaired `coder`, so `critic-pairing.py`
     blocked the live session at Stop;
  3. `claude -p` **exits 0 on an unknown command** (tested), so the exit code can never
     distinguish a real run from one that never started;
  4. the harness invoked `claude` without `cd`-ing into the project, and skills resolve from
     the cwd's `.claude/` — every `/skill` was then "Unknown command";
  5. a timeout was tested for AFTER emptiness, and a killed run has written nothing, so
     every timeout was misreported as "claude produced no output at all";
  6. `claude -p` text output is written only at the END, so SIGALRM discarded a whole
     30-minute transcript. Now `--output-format stream-json --verbose`.
  Fixed in `a70885b`, `d6f4a9e`, `12cbcee`; merged `dc293d7`.
- **The enforcement chain has now run for real, under the driver:**
  `strategist` (12 min) → `strategist-critic` (12 min), both `source: "hook"` with a real
  session id — dispatch-log.py on SubagentStop — then `strategy=61.0`,
  `strikes {strategist: 1}` (the below-80 path), `overall 68.71`. critic-pairing.py correctly
  did NOT block: the pair matched. **This is the first time any of it executed under
  `/pipeline`.**
- **Live-tier facts worth keeping.** literature is the only creator with `kind: skill`; it
  delegates to ZotPilot against a real Zotero library, which a `mktemp -d` has none of, so
  `--until <anything>` could never get past it. The live copy seeds literature's output
  (artifact + score, **never the dispatch log**) so `strategy` onward runs for real.
  Budget ~12 min per agent; one stage that strikes wants ~50 min. Hence
  `LIVE_UNTIL=strategy`, `LIVE_TIMEOUT=3600`, both overridable.
- **Do not assert outcomes in the live tier.** strategy scored 61 on round one. Any assertion
  that the run *reaches* a stage depends on an LLM clearing 80 on a synthetic fixture, which
  is not a property of the pipeline. Assert mechanism — dispatched, critic followed, score
  recorded, hook wrote it — as `live-critic-ran` does.
- **`check_install --all` had been red since 06:22 today** and nobody had run it: membership
  counted `hooks/__pycache__` as an unlinked upstream item. `bf79fd1` gave the residue `find`
  that exclusion and missed the membership loop above it. Fixed, merged `1513246`.
- **New defect, NOT yet fixed — `session_logs/` has no authority.**
  `hooks/log-reminder.py` tells sessions to create `quality_reports/session_logs/<date>_*.md`,
  and `hooks/pre-compact.py` (×2) and `hooks/post-compact-restore.py` READ that directory for
  context recovery — but `rules/logging.md`, read in full, defines exactly four artifacts and
  never mentions it. So compaction recovery reads a directory nothing is instructed to write.
  Two independent nested sessions flagged it before it was verified. Decide whether
  `logging.md` gains a fifth artifact or the hooks point at `SESSION_REPORT.md`.
- Verified green on main after all of the above: `check_fork` PASS · 62 tests OK ·
  `run_fixture` (mechanical) PASS · `check_install --all` PASS six repos ·
  `audit_graph` dangling 0 · roster [] · never-invoked [].
- Still open: §2a (109 prose literals), §2d (upstream ZotPilot), the `session_logs/` question
  above, and a full green `--live` run (the last one proved the mechanism, then hit the wall
  clock mid-round-2).

---

## Where things stand

> **Updated 2026-09-10 by session `01LyzZ`.** The block below originally read "merged,
> **pushed**, and live … `main` is at `7268017`" with 59 tests. All three had gone stale.
> The progress log above is authoritative where the numbered sections below disagree with it.

The pipeline repair is merged and live. `main` is at `cb15122`. The repair worktree has been
removed; `git worktree list` shows one checkout.

**`main` is NOT pushed — 11 commits ahead of `origin/main`.** This matters more here than in a
private repo: research-claude is public precisely so a coauthor can bootstrap with a clone and
no access grant, and a clone today gets none of this. `./bootstrap-pipeline.sh` in each paper
repo checks out the lock SHA from the REMOTE, so an unpushed lock SHA is unresolvable for
anyone but this machine. Push before relying on any of it elsewhere.

```
✓ check_fork:    PASS      56 criteria, 0 failures
✓ check_install: PASS      six repos      (was red all morning — see the progress log)
✓ run_fixture:   PASS      32 checks      (mechanical tier; --live is separate and on demand)
  unittest                 62 tests       (59 + 3 for the any_of producer hints)
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

## 1. Immediate cleanup — ✅ DONE 2026-09-10 (`4cf76a8`). Kept for its reasoning; do not re-run.

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

### 2e. `JHE` / `JHousE` disagreement — ✅ DONE (ESG `ce7c32b`, zoning2026 `342e870`)

`references/journal-profiles.md` in this repo now calls the housing journal `JHousE`, because
`JHE` was already taken by Journal of Health Economics. **The shared
`~/Research/.claude/references/journal-profiles.md` still says `JHE`.** The two files currently
disagree. Rename there too.

While in that file: check for the `ReStud` vs `REStud` casing bug that was found and fixed in this
repo's `discipline-cards.md` — a cross-reference that reads correctly and matches nothing.

### 2f. Live tier — ✅ BUILT AND EXERCISED (merged `dc293d7`). Text below predates it.

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
