# Pipeline Repair — Ruling Log

**Date:** 2026-09-08 / 09 · **Status:** Live record of an in-progress repair — Stages 0–3b, 4
and Stage 5 Tasks 5.1/5.2 complete; Stage 5 Task 5.3 in flight at the time of this promotion
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

Rulings are numbered R-1…R-126 in the order they were made. Where a later ruling reversed an
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

### R-81–R86 · The submodule mechanism is gone; ai-audit is vendored; a stale shadowing rule was found on the way out — *user decision*

The user directed, mid-repair, that the git submodule mechanism be dropped entirely "unless
there is a reason to keep it." Investigation found none: `zotpilot-skills/` was already
vendored-not-submoduled on record, `clo-author` had already been de-submoduled into `agents/`,
and the fresh worktree's two submodules (`ai-audit`, `journal-digest`) were **empty** at session
start until `git submodule update --init` was run manually — the exact failure a submodule
creates for a coauthor who clones without knowing to run that command, in a repo whose stated
purpose is precisely that bootstrap.

`skills/obsidian-digest-sync/` and `submodules/journal-digest` were dropped outright
(journal-digest is a standalone tool, not part of this pipeline). `ai-audit` was vendored at the
top level (`ai-audit/`, mirroring `zotpilot-skills/`) rather than absorbed into
`agents/`/`skills/`/`rules/` — a hard technical constraint, not a style choice:
`test_roster_matches_agents_dir` and `registry-complete` compare `agents/*.md` against the
registry's `kind: agent` entries, and `claim-verifier`/`humanize-auditor` are audit tools with no
paired critic, no quality component and no business on that roster.

**The live defect found while scoping this.** `rules/ai-disclosure.md` existed in two places —
the repo's own copy and `submodules/ai-audit/rules/ai-disclosure.md` — and differed. `apply.sh`
links `ai-audit`'s `rules/` *after* the repo's own, so the submodule copy won every install. The
submodule copy was the **stale** one: it still described a retired dual LaTeX+Quarto pipeline.
Every one of the six paper repos had therefore been reading a disclosure rule this repair exists
to abolish, silently, because the repo's own correct copy was shadowed. Resolved by reconciling
into one file at `rules/ai-disclosure.md` and dropping `apply.sh`'s link to the ai-audit copy.

**Consequence, unresolved at commit `b8d26ff`:** removing five links (`ai-disclosure.md`,
`humanize`, `verify-claims`, `claim-verifier.md`, `humanize-auditor.md`) plus
`obsidian-digest-sync` leaves **36 broken symlinks across the six paper repos** the moment this
branch merges to `main` — a dangling symlink is not an error to a file-reading agent, it is
simply absent. `apply.sh --link` in each repo clears it; see §5.

### R-104–R107 · The scoring wiring: five of eight quality components could never be scored

The registry declares eight scored components (`literature`, `data`, `strategy`, `theory`,
`code`, `manuscript`, `referees`, `replication`). A tree-wide search for `record-score` across
every skill found it wired for only three: `code` (from `/analyze`), `literature` (from
`/lit-position`), `manuscript` (from `/write`) — 35 of 100 weight points. `data` (weight 10),
`strategy` (weight 25, the heaviest component in the pipeline), `referees` (weight 25) and
`replication` (weight 5) had **no skill anywhere that recorded them**; `theory` (weight 20) was
conditional and also unwired. 65 of the non-conditional weight points were structurally
unreachable.

This was invisible to every gate built earlier in the repair, because every one of them checks
whether an *already-recorded* score is fresh and binding (R-42/44/45) — none checks whether
anything ever calls `record-score` in the first place. The critics were being dispatched (D-15's
dispatch half was real); their judgment simply never reached the state file.

**The concrete cost, traced rather than asserted.** The `score-if-scored data min 80` gate added
at the user's own request in R-38 — specifically so a bad data assessment would block strategy
work — could never fire, because `data` could never be scored. A gate the user asked for, built
correctly, sat permanently inert for a reason three tasks upstream of where anyone would think
to look.

Fixed as controller-authored Task 4.7: a recording site added to every skill that lacked one.
Two design points worth keeping. The PAP mode and the strategy-memo mode both record the *same*
`strategy` component (R-105) — precedent already existed in `/analyze`, where both
`data-engineer` and `coder` record `code`. And two components stay deliberately unscored:
`/review --replicate` is a numeric tolerance diff, not a rubric score, and records nothing
(R-106); `storyteller-critic` carries `component: none, quality_weight: 0` by registry design, so
`/talk` scores are advisory only, also by design (R-106). Do not "fix" either of these — they are
not gaps.

### R-109 · Extends R-49: any future dispatch-log writer must match `pipeline.py`'s `now()` byte-for-byte — one nearly didn't

Task 5.1's own plan-supplied brief specified `dispatch-log.py`'s timestamp as naive local time at
second resolution — exactly the format R-39 had already proven broken, and exactly the
cross-machine/DST hazard R-49 exists to prevent. Transcribed as written, it would have silently
reopened both bugs in the one file the plan created specifically to feed `critic-ran`.

Fixed by importing `pipeline.now()` directly, with a guarded fallback to the byte-identical
inline expression if the import fails (the hook must still fail open — see R-115–R119). This is
the mechanism R-49 asked for in the abstract; R-109 is the concrete case where the plan's own
text would have violated it, caught only because the implementer checked the brief's code
against `pipeline.py`'s docstring instead of transcribing it.

### R-113 · A hook log line with no `session` key is unattributed, not foreign — it must be included, never filtered out

`pipeline.py`'s `append_log` writes `{"at", "agent", "source"}` — no `session` key, ever. Task
5.2's plan-supplied session filter was `if not sid or e.get("session") in ("", sid)`. Since
`e.get("session")` is always `None` for a `pipeline.py`-written line, and `None` is never
`in ("", sid)`, every line written by the standalone `pipeline.py log <agent>` path — which is
what every stage skill actually instructs (`/write` Step 4, `/lit-position` Step 7, `/analyze`
Steps 2–3) — was silently dropped whenever a session id was present, i.e. in every real session.

The hook whose entire purpose is catching a creator dispatched without its critic would have
been blind to precisely the creators dispatched outside the orchestrated loop — the ones
statistically most likely to skip a critic. Fixed by treating a missing `session` as unattributed
rather than foreign: `(e.get("session") or "") in ("", sid)`. **Standing principle, stated
because it will recur:** when a filter's failure mode is silence, fail toward noticing, not
toward quiet exclusion — an unattributed hit that produces one extra advisory nudge costs a
sentence; a real hit filtered out costs the gate.

### R-115–R119 · The critic-pairing hook is a nag, not a gate — deliberately — and a correction to how that was verified

`hooks/critic-pairing.py` blocks a session's Stop event once per session per unpaired creator,
then goes silent for the rest of that session (P-10). This is intentional, not a shortcut: a Stop
hook that blocks unconditionally can trap a session with no way out. **The real gate is
`pipeline.py post <creator>` refusing to advance without a fresh, correctly-scoped critic
score** — the mechanism R-42/44/45 built and tested. Nobody should read a "pairing-once" PASS in
the harness as evidence the pairing is enforced; it is evidence a session was *reminded* once.
The two together are the gate; neither alone is.

Getting the hook itself right took two fix rounds. Round 1 added `isinstance` guards against
malformed JSON (a valid-but-non-dict payload or log line raises `AttributeError`/`KeyError` if
ungated) and a rule that an empty `session_id` must always block and never write a sentinel —
writing one would key every future incident to the same `":coder"` string and permanently spend
the "once per session" budget on the first empty-sid event (R-116). It also caught that the test
harness had been testing an input that never occurs in practice (empty `session_id` payloads),
which is exactly how the bug had survived.

**R-118 — recorded here as a correction, not softened.** The controller asserted, from a `grep`
for `except Exception` that landed on the wrong function, that two remaining code paths
(`KeyError` on a log entry missing `at`; `OSError` from an unwritable home directory) were live,
user-visible crashes producing Claude Code's `<hook name> hook error` banner on every Stop event.
**This was wrong.** Round 1 had already wrapped the real entry point (`main()` calling `_run()`)
in a top-level `except Exception: return 0` — the controller read the file's `__main__` tail, saw
a bare `sys.exit(main())`, and concluded there was no backstop, without reading `main()` itself.
Both paths were already returning 0 through the real catch. This is the exact failure the global
rule "a grep locates, it does not establish" names, and it is recorded plainly per that rule
rather than smoothed over: what R-118 actually bought was a **second**, redundant layer at
`__main__`, matching the idiom five other hooks in this repo already use verbatim
(`context-monitor.py`, `log-reminder.py`, `post-compact-restore.py`, `pre-compact.py`,
`verify-reminder.py`) — worth having for consistency, and because the inner wrapper is a private
convention a future edit could remove without noticing, but not a fix to a live crash.

**R-119 — a deliberate scope extension, made visibly.** While adding that `__main__` wrapper to
`critic-pairing.py` and `dispatch-log.py`, the controller found `hooks/session-guard.py` had the
identical bare `sys.exit(main())` with no backstop at either level — a genuine hole, unlike its
two siblings. No Stage 5 task named this file. It was fixed anyway: the change is the same four
lines already being applied to its neighbours, and leaving one hook able to throw an error banner
while fixing the two next to it had no defensible justification. Recorded as a judgment call
rather than folded silently into the task's diff.

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

### R-61, R-67–R70 · `audit_graph.py` gets the same treatment `check_paths.py` already needed

Three separate defects in `audit_graph.py`, found while trying to make `dangling = 0` achievable
at all (R-33's problem, one layer deeper):

- **No left anchor.** `PATH_RE` tail-matches, so `zotpilot-skills/VENDORED.md` registers as a
  reference to `skills/VENDORED.md` and `master_supporting_docs/x.tex` registers as `docs/...`.
  Fixed with a negative lookbehind (`(?<![A-Za-z0-9_.-])`) that still permits `/` immediately
  before the match, so R-18's skill-relative-reference detection is preserved. Verified to drop
  exactly the two false rows and add zero.
- **No exempt set.** Unlike `check_paths.py`'s `EXEMPT_PREFIX`/`EXEMPT_EXACT`, `audit_graph.py`
  had nothing to exclude project-level paths that legitimately never resolve in the repo
  (`templates/ai-use-log.md`, `templates/quarto-preamble.tex`,
  `scripts/acquire/01_download_*.py` — 7 rows). Added, mirroring `check_paths.py`'s mechanism
  exactly.
- **Unmarked self-reference.** `audit_graph.py:26`'s own `AGENT_RE` literal names
  `librarian|orchestrator|guide-writer` — the same "a gate that counts its own pattern
  definition" defect as R-25 Class A. One `# <!-- residue:prohibition -->` line closes it, and
  clears the self-reference edge for every one of the eighteen roster agents `AGENT_RE` lists,
  not only the three phantom ones — a broader, correct effect that changes no PASS/FAIL because
  no other agent's dispatch count was near zero.

**R-65 reverses R-60.** The controller initially argued the `worker-critic` exemption in
`check_refs.py`'s `AGENT_NOT_A_NAME` should be replaced by a marker, on the strength of a `grep`
that found the term used generically in four skills. That grep was case-sensitive; a
case-insensitive one found four *more* hits, all equally generic, confirming the original
hardcoded exemption was correct. The reviewer *tested* the recommendation — set
`AGENT_NOT_A_NAME` empty with the marker in place — and `worker-critic` came straight back onto
the roster's false-positive list. Acting on the initial recommendation would have been a
regression, not a fix. Kept as originally built.

### R-59, R-66, R-72 · A hardcoded blocklist that names deleted agents forever cannot be closed by marking it — only by finishing the cleanup it was pointing at

`check_refs.py`'s `DELETED_AGENTS` regex names `orchestrator`, `librarian`, `librarian-critic`,
`guide-writer`, `rmd-coder-critic` as permanent literals, so `audit_graph`'s roster check
(`agents named, not on roster`) lists all five forever unless those names stop appearing in the
tree. The first instinct — mark the two `check_refs.py` lines that define the pattern, the same
fix that worked for `check_fork.sh`'s and `audit_graph.py`'s self-references — **does not work
here**, and the reviewer proved it by applying exactly that fix in a scratch copy: the roster
list was completely unchanged, because the roster is populated by every *other* file in the tree
still naming those agents (orchestrator alone had 16 unmarked naming lines across
`agents/*-critic.md`, `skills/submit/SKILL.md`, `rules/registry-verification-gate.md`). **The
marker mechanism only ever suppresses a gate's own pattern definition — it cannot substitute for
the instruction-layer cleanup those names are a symptom of.** The roster only actually cleared
through Stage 3b's content work; the two `check_refs.py` marker lines were the *last* step,
applied after that cleanup, not instead of it — applying them first would have shown no change
and invited exactly the wrong conclusion, that markers don't work.

### R-74, R-87 · Markers are matched per physical line, end-anchored — a wrapped sentence or a table cell defeats them silently

`check_refs.py`'s `MARK` regex is end-of-line-anchored. A `<!-- residue:prohibition -->` placed
inside a **markdown table cell** does not satisfy it, because the cell is followed by a closing
`|` (R-74). A prohibition **sentence that wraps across two physical lines**, with a different
forbidden token on each line, needs a marker on **each** line — one end-of-block marker
suppresses only the line it sits on (R-87). Both were caught only by re-running `check_fork.sh`
itself; a hand-rolled approximating grep of the marker convention passed in both cases while the
real gate still failed. **Verify a marker against the real gate, never against a mental model of
its regex.**

### R-112 · The `produces`-path audit catches a missing declaration, not a contradicting one

Checking a skill's declared save path against its agent's registry `produces` glob (see R-108,
R-111, R-112 in §3) finds an artifact nobody declared. It does **not** find a skill naming the
*wrong* path when the agent file itself names the *right* one — `agents/strategist.md` was
correct while `skills/strategize/SKILL.md` pointed elsewhere, and the agent being right is what
let the contradiction pass an agent-only spot-check. Closing this needs the inverse check: flag
any `quality_reports/` path in a shipped file matching **no** registry glob, with an allow-list
for genuine unregistered convenience artifacts. Carried to Stage 7 as a new criterion,
`artifact-paths` (§5).

---

### R-122 · A retired skill's name can shadow a live one that extends it

`check_refs.py`'s `deleted-things` criterion flags references to retired skills. Its pattern
ended in `\b`, and `\b` matches between `t` and `-` because `-` is a non-word character — so
the retired `/new-project` matched the **live** `/new-project-ztp`.

The damage was not the false red. An implementer, told not to edit the checker, worked around it
by writing the live skill's name without its leading slash in
`skills/pipeline/references/setup.md` — so the driver's setup reference could not name the skill
in the form a session would type, and `audit_graph.py` went on listing `new-project-ztp` under
*skills never invoked*. A gate misfire had suppressed a real signal and degraded a shipped file.

Fixed by replacing the trailing `\b` with `(?![A-Za-z0-9_-])`, verified against four forms: it
still catches `the retired /new-project skill` and `/new-project.`, and no longer matches
`/new-project-ztp` in bare or backticked form. A sweep for other live names shadowed by a retired
prefix found none, so the class is closed rather than the instance.

**This is not a loosening.** The rule that a gate is never moved to make a red go away (R-93)
concerns a *genuine* hit. Here the hit was demonstrably false — the skill is live, on disk, and
dispatched. Correcting a proven false positive is what keeps a gate worth obeying; a gate that
forces a workaround gets worked around next time, without anyone asking.

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
| R-84 | Two `ai-disclosure.md` copies; the stale submoduled one shadowed the correct one in all six repos | pre-existing |
| R-104 | Five of eight quality components had no `record-score` call anywhere in the tree | pre-existing, newly exposed |
| R-108, R-111 | Two skills wrote artifacts under paths contradicting their own agent's registry `produces` | pre-existing |
| R-110 | `registry-authority` green while ten creator→critic pair declarations sat outside the registry (case-blind regex) | pre-existing gate defect |
| R-78 | Five agent files had no owning task anywhere in the 4263-line plan | plan gap |
| R-101 | `/write humanize` asserted a critic gate no code path reached | plan's code |
| R-103 | `/strategize pap` made its own critic optional | plan's code |
| R-113 | Hook silently dropped every dispatch-log line with no `session` key | plan's code |

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

### R-78 · Five agent files with no owning task in the entire plan

Task 3b.4's own inventory carried 24 rows tagged `[3b.4]`; only 8 targeted its nine named files.
The other 14 targeted `agents/writer.md`, `strategist.md`, `explorer-critic.md`,
`storyteller-critic.md` and `theorist-critic.md` — files with **zero** mentions anywhere in the
plan's 4263 lines, except `writer.md`, cited exactly once, in Task 0.1, as an *example of a file
the sweep marked clean*. It was not clean: `agents/writer.md:44` was the very first sweep gap
this repair found (Task 0.1), and it stayed unowned for three stages. It instructed the writer
agent — the one that drafts the paper — to read `quality_reports/results_summary.md`, a file
`/analyze` no longer produces because Task 3b.1 had already deleted it. Stage 3b's own title is
"every agent ... describes the one-manuscript path only"; a stage cannot meet that criterion
while a fifth of its target files sit outside every task's writable set. Closed by extending Task
3b.4 to cover all five, on the grounds that leaving a live agent file instructing a dead handoff
was not a defensible reading of "outside scope."

### R-108, R-111, R-112 · Three skill-versus-registry contradictions, and the blind spot in the method that found them

Three separate skills instructed writing an artifact under a path that did not match what the
registry's `produces` declared for that agent, each catching a different downstream consumer:

- `/discover data` saved one file (`quality_reports/data_exploration_[topic].md`); the registry
  declares `explorer.produces` as three files under `quality_reports/data-assessment/*/`
  (`data_sources.md`, `data_dictionary.md`, `access_instructions.md`). Consequence: `post
  explorer` could never close, and — the one that mattered most — `strategist.requires`'s data
  branch, the exact gate the user asked for in R-38, keys on `data_sources.md` at that path and
  could never be satisfied either (R-108).
- `/strategize`'s memo step saved to `quality_reports/strategy_memo_[topic].md`; the registry
  (and the agent file itself, correctly) declare `quality_reports/strategy/*/strategy_memo.md`
  with five section predicates keyed to it. `strategy` is the heaviest-weighted component in the
  pipeline (R-111).
- `/talk` saved its critic's report to `quality_reports/[format]_talk_review.md`, contradicting
  the registered `quality_reports/reviews/storyteller-critic_*.md` (R-112).

All three were found the same way each time: read the skill, extract every `type: path` glob
from the corresponding agent's `produces`, and check the prefix against the shipped tree.
Auditing the *whole class* this way — rather than fixing instances as they turned up — bounded it
at exactly three, plus one legitimate unregistered convenience artifact (`/discover ideate`'s
`research_ideas_*.md`, which is not a mismatch because nothing declares it as a `produces` entry,
so nothing depends on it).

**The audit method's own blind spot, worth keeping because it will recur:** checking a skill's
declared save path against the registry glob finds a *missing* path, not a *contradicting* one.
The `/strategize` case passed a first look because `agents/strategist.md` names the correct
directory even while `skills/strategize/SKILL.md` names a different, wrong one — the agent file
being right is what let the contradiction hide. Closing this properly needs the *inverse* check:
flag any `quality_reports/` path appearing in a shipped file that matches *no* registry glob at
all, which in turn needs an allow-list for genuine unregistered convenience artifacts
(`research_ideas_`, `journal_recommendations_`, `referee_response_tracker`, and similar). That is
real gate-authoring work, deliberately not bolted onto Stage 4 where it was found; it is carried
to Stage 7 as a new criterion, `artifact-paths` (§2, §5).

### R-110 · `registry-authority` reported green while ten creator→critic pair declarations sat outside the registry — the gate was case-blind

`AUTH_ARROW`, the regex `registry-authority` uses to catch a skill or rule *declaring* a
creator→critic pairing outside `rules/registry.yaml` (the single source of truth D-2 exists to
protect), is compiled without `re.I`, and its creator-name alternation is written all-lowercase.
Ten genuine pair declarations evaded it purely by capitalization —
`**Agents:** Explorer (finder) → explorer-critic (assessor)`, `Strategist → strategist-critic`,
`Theorist → theorist-critic`, `Storyteller (creator) → storyteller-critic (reviewer)`, and a
three-row routing table plus an ASCII decision tree in `rules/revision.md` naming the same pairs
twice more. `rules/revision.md`'s table and tree are the substantive case: a routing table of
creator→critic pairs *is* a second source of truth for the pairing, in the exact shape D-2
forbids.

**This is the third time in this repair that a gate's own regex, not the property it names, was
the thing at fault** — after `audit_graph.py`'s unanchored `PATH_RE` (§2) and `check_refs.py`'s
end-anchored `MARK` failing inside a table cell (§2). Fixed by strengthening `AUTH_ARROW`
(case-insensitive, tolerant of a short parenthetical between the creator name and the arrow), and
— the discipline worth keeping — by first *demonstrating* the strengthened regex catching all
ten as RED, before touching a single line of the content it flags, so the fix could be shown to
fail the ten it was meant to fail before it was trusted to pass everything else. This does not
conflict with R-93 (which forbade *loosening* `AUTH_PAIR` to excuse a false positive): tightening
a regex to expose a false negative, and refusing to loosen one to hide a false positive, are the
same principle — never move a gate to make a red go away — applied in the two directions it can
be violated.

### R-101, R-103 · Two creator modes with no gate at all, each asserted by a sentence the code path never reached

- **`/write humanize`** (R-101). `skills/write/SKILL.md`'s Steps 4–6, which dispatch
  writer-critic and record the score, are nested under the `### /write [section]` mode. `### /write
  humanize [file]` is a separate, sibling mode section whose entire body ran
  `**Agent:** Writer (cleanup mode)` → `**Output:** Edited file...` and stopped — unreachable from
  Steps 4–6 no matter what those steps said. A sentence claiming the gate applied had been added to
  Step 5 without checking whether Step 5 was ever executed on this path. Fixed by dispatching
  writer-critic **in proofread mode** (its declared mode, covering categories 4/5/6/8 — the right
  set for a cleanup pass) and recording with `--scope section:<name>`. The scope prefix is
  load-bearing, not decorative: only a `--scope section:` value writes to `state["sections"]`; any
  other scope, or none, overwrites the `manuscript` component score — and a proofread reviewing
  four of eight categories must never be recorded as a full manuscript review.
- **`/strategize pap`** (R-103). The skill stated "Strategist (in PAP mode), **optionally**
  strategist-critic," with a whole section headed "Optional strategist-critic Review" — a direct
  contradiction of `rules/agents.md` §1 ("the dispatching skill dispatches the critic after the
  creator, every time, in every mode"). A pre-analysis plan is the one artifact whose entire value
  is that it was committed to *before* seeing results; skipping its adversarial review because a
  skill called it optional defeats the artifact's purpose. Fixed by removing "optional" in both
  places and making the critic a mandatory step.

Both were found only by reading the skill files directly rather than trusting a gate — no
checker in this repair asserts "every mode dispatches its critic"; `registry-authority` and
`critic-ran` both operate one level below that, on pairings and score freshness, not on whether a
given *mode* of a multi-mode skill reaches the dispatch code at all.

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
- **R-91.** Verify a checker's hit before suppressing it as a false positive, never accept the
  pattern-match. A triage classed four `/learn` hits as false positives (the string appears in a
  hook's nudge text, matching no real skill) with the one-line fix being to add it to
  `SLASH_ALLOW`. Checked instead of applied: `skills/tools/SKILL.md:98` documents a real
  `/tools learn` subcommand, so the hook had been telling users to run a command, `/learn`, that
  does not exist, at every context-budget threshold. Fixing the hook's text closed a live UX
  defect that suppressing the hit would have hidden forever — a wrongly-suppressed true positive
  is invisible from that point on, unlike a wrongly-flagged false positive, which stays visible
  and annoying until someone looks again.
- **R-73.** "Writing prose *about* a forbidden pattern reintroduces the pattern" recurred five
  separate times in this repair (the `references/` project-noun rationale spelling out the banned
  tokens; the identity-scan self-match; a `PATH_RE` explanatory comment containing a literal
  example path; a `check_refs.py` self-scan on its own pattern definitions; a controller's own
  comment about the `/learn` investigation containing a bare `/learn`). Caught every time only by
  re-running the real gate, never by inspecting the diff — and once only by per-step add/remove
  row accounting, since a net-count check showed no change (one row added, one removed, in the
  same commit). Recorded as a mechanism, not bad luck: **when editing prose near a gate's own
  trigger pattern, re-run the gate, don't proofread the sentence.**
- **R-120.** Do not commit a fixture copy of a file `apply.sh`'s `copy_seed` seeds — it never
  overwrites an existing destination, so a committed copy wins over the seed forever and the
  harness tests a frozen duplicate instead of what projects actually receive. Confirmed against
  `tests/fixture-project/.claude/settings.json`: left uncommitted, seeded fresh by `apply.sh
  --link` on every harness run, with a `settings-seeded` check asserting the seeded copy names
  both new hooks. Same principle as R-15's negation, opposite direction: R-15 keeps a file
  committed that a seed refresh must not clobber; R-120 keeps a file *un*committed so a seed
  refresh is what the harness actually exercises.

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
| Fleet re-link after this branch merges: `apply.sh --link` + `check_install.sh --all` in each of the six repos — 36 broken symlinks (5 ai-audit links + `obsidian-digest-sync`, ×6) go dangling the moment the submodule removal merges | R-85 |
| `git submodule deinit -f submodules/ai-audit submodules/journal-digest` and a `.git/modules` clean on `main` (not done from the worktree — shared `.git/config`/`.git/modules`, see R-1) | Submodule removal task |
| Reword `rules/registry.yaml`'s 8-row self-documentation header and the 6 dual-context docstring rows in `pipeline.py`/`registry_lib.py` so `path-resolves` reaches green without a new exempt set | Task 3b.8 |
| Add the `artifact-paths` gate: flag any `quality_reports/` path matching no registry glob, with an allow-list for genuine convenience artifacts | R-112 |
| ~~Resolve the `.claude/references/coding-standards` double-reference left dangling by deleting `references/coding-standards-rmd.md`~~ — **withdrawn (R-125): the premise was false.** `coding-standards-{r,python,julia}.md` all exist; only the Rmd file was deleted, correctly. The two hits are R-21's documented truncation of `-{lang}` and `-*`, four sections above. Fixed in `PATH_RE` at Task 7.3, not by editing the references. | R-125 |
| Implement the enumerated (but not yet applied) `SKILL.md` "Replaces /X" frontmatter rewordings for the 18 genuine `skill-refs` hits | Task 3b.8 |

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
- `registry-check`'s exit code ORs `registry-complete | registry-authority | registry-rendered`
  into one line; a single red can mean any of three things, and one plan checklist expected it to
  flip at the wrong task (R-99). Left as designed — splitting it would hide the coupling that
  makes "the registry contract is not yet whole" a single fact.
- `check_refs.py`'s `DELETED_AGENTS`/`AGENT_NOT_A_NAME` exemptions are markers on the checker's
  *own* source; a marker suppresses whatever line it sits on, so a genuinely new naming defect
  introduced on an already-marked line would be invisible. Inherent to line-level markers, same
  class as the existing minor on `check_paths.py`'s `EXEMPT_EXACT`.
- The `AUTH_ARROW` rewrites in `rules/revision.md` (R-110) keep its routing table and decision
  tree as structures, adding one line to each saying the pairing is declared in the registry — a
  future editor adding a new row to that table without a corresponding registry entry would not
  be caught by anything.
- **R-121:** `post-compact-restore.py`'s `last_component` is *derived*, not read — the state file
  has no such key. It is the `components` entry whose `at` sorts greatest, which is only valid
  because `now()` emits fixed-width UTC timestamps so lexicographic order equals chronological
  order (R-49). Relaxing that format would break this silently. The reasoning is in the
  function's own docstring as well as here.
- `hooks-readme`'s 10 remaining hits, itemised for whoever closes them: six hooks carry no
  `Hook Event:` line (`post-edit-lint.sh`, `lint-scripts.sh`, `protect-files.sh`,
  `post-merge.sh`, `log-reminder.py`, `notify.sh`); two table rows name a stale event
  (`session-guard.py` says SessionStart, the hook says PreToolUse; `post-compact-restore.py`
  says PostCompact, the hook says SessionStart); and three are a **checker defect** — the row
  regex reads any first backticked cell as a filename, so the second "how to block" table, whose
  first column is an event name, is scanned as if `hooks/PreToolUse` were a file.
- `hooks/README.md`'s "how to block" table states that `PreCompact, Stop` block only by exit 2.
  A Stop hook also honours a top-level `{"decision":"block","reason":...}` — which is what
  `hooks/critic-pairing.py` emits. Verified against the current hooks documentation, fetched
  rather than recalled. Until corrected, the README contradicts a shipped hook.

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
| R-59 | `DELETED_AGENTS` names deleted agents forever; roster never clears by marking alone *(prescription corrected by R-66)* |
| R-60 | *(superseded by R-65)* worker-critic exemption should become a marker |
| R-61 | `audit_graph.py`'s `PATH_RE` has no left anchor; tail-matches produce false dangling rows |
| R-62 | `audit_graph.py` has no exempt set for legitimate project-level paths |
| R-63 | Two orphaned sweep gaps (hooks/README.md, rules/data-manifest.md) plus the permissions.md render trap |
| R-64 | Never-resolving scripts-row count corrected 9→10; new `pending` inventory class added |
| R-65 | **Reverses R-60:** the hardcoded `worker-critic` exemption is correct; a case-sensitive grep misled the first call |
| R-66 | R-59's prescription is false: marking two lines changes nothing; the roster clears only through Stage 3b's content cleanup |
| R-67 | `audit_graph.py:26`'s own `AGENT_RE` is an unmarked self-reference |
| R-68 | The lookbehind fix applied and reproduced exactly: −2 rows, 0 added |
| R-69 | Exempt set added to `audit_graph.py`, exactly 7 rows |
| R-70 | The inventory undercounted the exempt residual as zero; it is six (`pending` class) |
| R-71 | Task 3b.8's `dangling = 0` exit criterion is unreachable at that point; expect 6, enumerated, until Task 4.3 + Stage 5 hooks land |
| R-72 | `check_refs.py:29`'s marker must be applied *after* Stage 3b's content cleanup, not instead of it |
| R-73 | General guard: prose describing a forbidden pattern reintroduces it — recurred 5 times |
| R-74 | Markers inside a markdown table cell do not satisfy the end-anchored `MARK` regex |
| R-75 | `registry-authority` gained 3 hits from brief-mandated verbatim arrow text; scheduled for Task 4.5 |
| R-76 | Real content loss on deleting `replication-tolerances.json`; exact values restored in Task 3b.3 |
| R-77 | Plan cross-reference defect: Lit-Critic rubric section attributed to Task 4.4, actually Task 4.3 |
| R-78 | Five agent files had no owning task anywhere in the plan; Task 3b.4 extended to cover them |
| R-79 | One added dangling row is a legitimate forward reference (`pending` class), not a regression |
| R-80 | Task 4.5 Step 1's "six severity lines" expectation corrected to four *(later superseded: 3b.8 found all four already done)* |
| R-81 | **User:** drop the submodule mechanism entirely; vendor ai-audit, drop obsidian-digest-sync/journal-digest |
| R-82 | ai-audit vendored top-level, not absorbed into agents/skills/rules (registry roster constraint) |
| R-83 | Handoff: removing obsidian-digest-sync leaves a dangling symlink in all six repos until re-link |
| R-84 | Live defect: two `ai-disclosure.md` copies, the stale submoduled one shadowing the correct one |
| R-85 | Handoff: 36 broken symlinks across six repos at merge; membership does not propagate through links |
| R-86 | `obsidian-digest-sync` added to `check_refs.py`'s `ABSENT_SKILLS` |
| R-87 | Extends R-74: a prohibition sentence wrapping two lines needs a marker on each line |
| R-88 | Stage 3b's remaining 16 hits decomposed: 6 self-scan, 10 genuine unmarked prohibitions — none a real violation |
| R-89 | `skill-refs`' 32 hits triaged: false positives, one genuinely pending (`/pipeline`, Task 5.4), rest genuine |
| R-90 | `path-resolves`' 25 rows include the permissions.md generation trap (R-63) plus self-documentation rows |
| R-91 | The `/learn` catch: verified before suppressing, found a real UX defect instead of a false positive |
| R-92 | Task 4.5 Steps 2 and 3 both stand; rewrite the arrow, keep the imperative naming the critic |
| R-93 | Do not loosen `AUTH_PAIR`; it is not producing the false positive it was floated to fix |
| R-94 | Task 4.1's deleted 14-item Quality Self-Check is substitution, not loss (verified against writer/writer-critic) |
| R-95 | Carries R-77 into the Stage 4 dispatch |
| R-96 | Task 4.3's insertion anchor (`## Librarian-Critic`) doesn't exist; ruled where to insert instead |
| R-97 | Task 4.4's Claim–Evidence insertion anchor is real and verified |
| R-98 | Task 4.4's second edit target text already deleted by an earlier stage; treated as an insertion |
| R-99 | `registry-check` cannot flip green before Task 4.5; the plan's checklist is mis-sequenced, not the harness |
| R-100 | Task 4.1's own verify command is miscounted (`grep -c` counts lines, not occurrences); text stands |
| R-101 | `/write humanize` asserted a critic gate no code path reached; fixed in proofread mode with `--scope section:` |
| R-102 | Equation numbering had no deduction row; added once, to the format table only (no double-count) |
| R-103 | `/strategize pap` made its critic optional, contradicting `rules/agents.md` §1; fixed |
| R-104 | Five of eight quality components had no `record-score` call anywhere; the user's own `score-if-scored data` gate was a structural no-op as a result |
| R-105 | PAP mode and memo mode both record the same `strategy` component |
| R-106 | `/review --replicate` and `/talk` stay unscored, deliberately |
| R-107 | The runtime backstop for R-104's gap is correctly Stage 5's job, not Stage 4's |
| R-108 | `/discover data`'s save path contradicted `explorer.produces`; blocked the user's own data-quality gate |
| R-109 | Extends R-49: `dispatch-log.py` must match `pipeline.py`'s `now()` exactly; the plan's brief did not |
| R-110 | `registry-authority` case-blind: 10 pair declarations evaded it by capitalization alone |
| R-111 | `/strategize`'s memo path contradicted the registry and its own agent file |
| R-112 | Audited the whole artifact-path-contradiction class; found the audit method's own blind spot (misses contradictions, only catches omissions) |
| R-113 | Hook silently dropped every dispatch-log line with no `session` key — the standalone-dispatch path most likely to skip a critic |
| R-114 | Piped-payload tests must not write into the real `~/.claude/sessions/`; use a temp `HOME` |
| R-115 | Fail-open guards added for malformed JSON payloads and log lines |
| R-116 | An empty `session_id` must always block and never write a sentinel |
| R-117 | The critic-pairing hook is a nag (once per session), not a gate, by design (P-10); `post <creator>` is the real gate |
| R-118 | **Corrected:** two code paths believed to be live user-visible crashes were already caught by an existing `main()` wrapper; the added `__main__` guard is redundant-but-good, not a crash fix |
| R-119 | Deliberate scope extension: `hooks/session-guard.py` had the same unguarded hole as its two siblings and was fixed alongside them |
| R-120 | Fixture `settings.json` must NOT be committed — `apply.sh`'s `copy_seed` never overwrites, so a committed copy would test a permanently stale seed |
| R-121 | `last_component` is derived from timestamp order, valid only while R-49's format holds |
| R-122 | A retired skill's name shadowed a live one extending it; the gate misfire degraded a shipped file before it was fixed |
| R-123 | Task 6.4 (ZotPilot fork PR) deferred to the maintainer — it pushes and merges on a shared remote. Nothing is blocked: its residue is WARN-tier vendored-tree text |
| R-124 | `skills/dashboard/` deleted only after confirming every other `dashboard` hit refers to the Obsidian `Home.md` note, a different artifact |
| R-125 | **Withdraws a §5 deferred item.** The `coding-standards` "dangling refs" were R-21 truncation false positives; the three real files exist. Fixed in `PATH_RE`, not in the references |
| R-126 | Task 7.5's six-repo wiring and Task 7b.1's `~/Research` work deferred — that tree is read-only for this session. The in-tree halves (`hooks-wired`, `seeds/settings.json`, the profile/card files) still ship |
