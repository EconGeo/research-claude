# Skill Token Optimization — Implementation Plan

**Status:** complete (2026-09-24)

**Goal:** Cut the SKILL.md body text that loads on every skill invocation by ~40%, bind every
bundled reference file to the step that needs it, and close the correctness defects found in
`docs/audits/2026-09-15_skill-best-practices-audit.md` — without changing any pipeline behaviour.

**Source audit:** `docs/audits/2026-09-15_skill-best-practices-audit.md` (read §3 P1 and §3 P3;
the correction block at the top of that file is binding — the ztp version-skew findings are
withdrawn and must not be acted on).

**Architecture:** Three levels load at different times. Level 1 (frontmatter `description`, all
18 skills, ~1.7k tokens) is always in context and is already fine — **do not touch it**. Level 2
(SKILL.md body) loads in full on every invocation and is where the cost is. Level 3 (76 bundled
files) loads only when read. The work is: move Level 2 content that is only needed at one step,
or only needed by a subagent, down to Level 3; name each Level 3 file *inside the step that uses
it*; delete the inline duplicate that has drifted from it.

**Measured baseline (2026-09-16, `skills/` only):**

| | chars | ~tokens |
|---|---|---|
| Level 1 — all 18 descriptions, always in context | 6,893 | 1,723 |
| Level 2 — all 18 SKILL.md bodies | 121,621 | 30,399 |
| Level 2 — the 8 skills one `/pipeline run` invokes | 73,176 | 18,294 |
| Level 3 — 76 bundled files, on demand | 220,909 | 55,227 |

The five skills this plan refactors are 63,573 chars of Level 2. Target is 38,000. That takes a
full `/pipeline run` from ~18.3k to ~11.9k tokens of skill text before a single reference file,
agent report, or line of manuscript is read.

**Explicitly out of scope** (audit practices deliberately NOT adopted — do not implement them):

- **P2 `disable-model-invocation: true`.** `skills/pipeline/references/*.md` invoke the stage
  skills by name; setting the flag breaks `/pipeline`. The practice assumes standalone skills.
- **P4 "5–10 options at every decision point."** Adds turns and text to 15 skills, directly
  against this plan's goal.
- **P6 "one closing step per skill."** 18 new instruction blocks read on every invocation, also
  against the goal. Task 8 wires the existing `/checkpoint` → `/promote` loop instead.
- **P7 eval suite.** Needs a mock ZotPilot MCP server. Separate project; not blocked by this one.

---

## Global constraints

Every task inherits these. Re-read this section at the start of every task.

1. **Edits under `skills/`, `agents/`, `rules/` and `hooks/` are live in every linked paper the
   moment you save.** Branch before the first edit of every task. Never work on `main`.
2. **`./scripts/check_fork.sh` must exit 0** before any commit that touches the shipped tree.
3. **Never remove a `record-score` or `pipeline.py log` call site** (R-104–R-107, R-113). Moving
   its surrounding prose to a reference file is fine; the command line stays in SKILL.md.
4. **Never replace a numeric critic gate with a user choice** (R-42, R-44, R-132).
5. **Every mode must still reach its own critic dispatch** (R-101). Slimming must not orphan a
   dispatch the way `/write humanize` and `/strategize pap` were once orphaned.
6. **Two things that look like gaps are deliberate — do not "fix" them** (R-106): `/review
   --replicate` records no score, and `/talk` scores are advisory (`component: none,
   quality_weight: 0`).
7. **Three strings are pinned by `tests/test_review_contracts.py`** and must survive in
   `skills/review/SKILL.md`: the `## Verifier Pass/Fail Definition` heading, the literal
   `.claude/agents/verifier.md` inside that section, and the literal `git status --porcelain`
   anywhere in the file. That section must **not** contain `prose_number_check`,
   `references.bib`, `quarto render`, or `absolute paths`.
8. **`scripts/check_paths.py` resolves every `.claude/`-prefixed pipeline path in the shipped
   tree.** This is a safety net for this refactor: a step-binding that names a file which does
   not exist will fail the gate. Use it — write the binding, run the gate.
9. **Nothing project-specific may ship.** No journal name, dataset name or project noun in
   `agents/`, `skills/`, `rules/`, `hooks/`, `templates/`.
10. **Read before asserting.** Before deleting a block as "a duplicate of file X", read file X to
    end-of-file. Several audit findings are drift between two copies — you need to know which
    copy is right, and it is not always the template.

---

## How to execute this plan across cleared contexts

Each task is a complete unit of work sized for one session. At the end of every task you commit,
update the Progress Log below, and **clear the context window**. The next session starts cold and
reads only what its task's **Cold start** block names.

**Every session begins with exactly this:**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short && git branch --show-current
```

Then read, in order:
1. This plan's **Global constraints** section (above).
2. This plan's **Progress Log** (below) — it is the record of what is actually done.
3. The **Cold start** block of the task you are picking up.

Do not read the other tasks. They are written to be self-contained on purpose.

**Every session ends with:** verification green → commit → merge → update the Progress Log →
report what changed → stop.

---

## Progress Log

The executor appends one row per completed task. This is the authoritative record of state — the
checkboxes inside a task are working notes, this table is the handoff.

| Task | Status | Branch | Merged | Notes |
|---|---|---|---|---|
| 0 — Baseline & branch hygiene | done | — (no commit) | — | 2026-09-16: tree clean (only pre-existing `M skills/new-project-ztp/SKILL.md`), `check_fork.sh` PASS exit=0, pytest **142 passed, 3 subtests** in 103s. Level-2 baseline confirmed = plan figure (121,621 chars). Five targets: review 18,058 / strategize 15,966 / write 11,290 / discover 9,733 / checkpoint 8,526 = 63,573 chars. |
| 1 — Session guards (careful/freeze) | done | `fix/session-guards` | yes (786379e) | Hook: per-pattern compilation (only SQL is case-insensitive), refspec force-push, `find -delete`/`-exec rm`, `rm` flags-before-`-rf`, `--force`/`--recursive`; deny text no longer tells the model to rephrase or to run the off switch. Both guard skills now read-modify-write the guard file via Bash (preserves the other key; the hook denies Edit on it by design) and the false "session-scoped" gotchas are corrected. `careful` Blocked-Patterns table re-synced to the hook, incl. `git branch -d` explicitly allowed. New `tests/test_session_guard.py` (12 cases): 9 failed before the fix, all pass after. Suite 142 → **154 passed**, `check_fork` PASS. One gate catch: `check_paths.py` rejected a bare `hooks/session-guard.py` cross-reference — written as `.claude/hooks/session-guard.py`. |
| 2 — Scoring correctness (submit; strategize decision) | done | `fix/submit-coverage-check` | yes (fdf17a3) | Part A: R-133 coverage check inserted as step 3.5 of `/submit final`, so the workflow that runs the gate executes the rule instead of only stating it in Principles. New `tests/test_submit_gate.py` (2 cases), 1 failed before / all pass after. Suite **156 passed**, `check_fork` PASS. Part B: D1 put to the user and answered — **(b)**. Not implemented here; Task 4 carries it out. |
| 3 — `review` refactor + step-binding test | done | `refactor/review-skill` | yes (745794f) | **18,058 → 10,878 chars** (budget 11,000). New `tests/test_skill_contracts.py` (step-binding + budget ratchets); `review` is out of the budget failure list, `test_every_bundled_file_is_bound_to_a_step_or_an_agent` now passes tree-wide. `test_review_contracts.py` 9/9 — all three pinned strings survived; `git diff main` deleted **0** `record-score` call sites. Contradictions resolved by reading both sides in full: **editor.md wins** the 0-FATAL case (0 FATAL + 4+ ADDRESSABLE = Major), so `disposition-pool.md` was reduced to the six disposition definitions — the only content it uniquely owned — and its drifted duplicates of the peeve pools / decision rule / report formats deleted rather than corrected. Found in passing: `references/journal-profiles.md:23` pointed at `editor.md` for those definitions and editor.md never had them — repointed. `referee-report-template.md` **deleted** (both referee agents own a richer weighted 5-dimension format; nothing but the resources table referenced it). Two extra template moves were needed to reach budget: `peer-review-prompts.md` and `replication-comparison.md`. **Plan text corrected:** the plan's replacement wording said strategic alignment is "categories 1–3"; the template and `coder-critic.md` both say **1–4 / 5–16**, and the routing line's "categories 4-12" was wrong too — both fixed to match the authoritative sources. Suite 156 → **158 passed**, 1 expected failure (budget, naming strategize/write/discover/checkpoint only). `check_fork` PASS after fixing a provenance line I added that used an unprefixed path and the name of a deleted agent. |
| 4 — `strategize` refactor | done | `refactor/strategize-skill` | yes (ea89319) | **15,966 → 7,967 chars** (budget 8,000). Every template read to EOF before its inline copy was deleted; `pap-templates/osf.md` §6 genuinely lacked the endogeneity-threats bullet, so that was added to the template *before* the deletion. New: `templates/pap-safety.md` (ASSUMED rules + PAP-specific critic criteria), `templates/pre-theory-report.md` (the Pre-Theory Report moved **verbatim**, structure untouched per the plan). Also collapsed both critics' 4-phase protocol lists — strategist-critic and theorist-critic each read their own. Design-checklist binding added; iterate rule unified on `<80` (strategy mode had said "CRITICAL", which no gate computes). **D1 (b) implemented:** PAP records with `--scope section:pre-analysis-plan`; `git diff main` shows exactly 1 `record-score` line removed and 1 scoped line added, as the plan specified for (b). The mandatory PAP critic dispatch (R-103) is intact and now stated explicitly. Rationale + the accepted `pipeline.py next` consequence moved to `gotchas.md` so it is not later "fixed". Suite **158 passed**, 1 expected budget failure (write/discover/checkpoint only). `check_fork` PASS. |
| 5 — `write` refactor | done | `refactor/write-skill` | yes (4e765ce) | **11,290 → 7,482 chars** (budget 7,500). Pointer bug confirmed and fixed: `agents/writer.md` does **not** hold the section templates — it points at `templates/section-templates.md`, which is also where the duplicated "Section Length Summary" table already lived. `cleanup-patterns.md` bound as new **Step 4b** between writer and writer-critic — the pass the skill description promised and no step performed. Style-guide mode now dispatches against `style-extraction-protocol.md`; the inline copy was 5 steps to the protocol's 6, and **the omitted step was the self-citation check**, so missing self-citation bib keys went unreported. Both `--scope section:` `record-score` lines untouched (R-101) — `git diff main` deleted 0 after I caught and restored a step-5 body I had dropped while inserting 4b. Suite **158 passed**, 1 expected budget failure (discover/checkpoint only). `check_fork` PASS after prefixing the one `agents/writer.md` reference I wrote unprefixed. |
| 6 — `discover` refactor | done | `refactor/discover-skill` | yes (4333ec2) | **9,733 → 5,934 chars** (budget 6,000). All five `KNOWN_UNBOUND` discover entries removed and both ratchet tests pass, so the bindings are real. **Grade scale reconciled** using the plan's tie-breaker: the explorer-critic's six categories separate *practical feasibility* from the four *fit* categories, so the grade measures **access effort** (the skill's A–D semantics), extended with the template's **F** = not obtainable (a state A–D could not express; F routes to the rejection table). Both copies now agree and state why. Same drift class also fixed: the skill said "5-point assessment" where the agent and `data-review-6-categories.md` both say six. `lit-review-entry.md` deleted (unreferenced). `pdf-processing.md` deleted — `rules/content-standards.md` §3 is a near-verbatim authoritative copy; its one unique item (the Read tool page-range limit) was moved into the rule **before** the deletion. `WebSearch`/`WebFetch` dropped from `allowed-tools` (no step uses them; the Explorer agent carries its own). Suite **158 passed**, 1 expected budget failure (checkpoint only). `check_fork` PASS. |
| 7 — `checkpoint` refactor | done | `refactor/checkpoint-skill` | yes (52a3267) | **8,526 → 5,459 chars** (budget 5,500). All three templates bound; last three `KNOWN_UNBOUND` entries in scope removed and **the whole suite is green — 159 passed, 0 failures**. Added the three requirements the rules mandate and the skill never performed: plan staleness sweep (`session-handoff.md` R1), handoff reference dry-run (R3), `ai_use_log.md` confirmation (`ai-disclosure.md` Enforcement) — all as **report lines, not prompts**. Obsidian setup *and* sync both moved to `references/obsidian.md`; the sync procedure was loading on every checkpoint even with no vault configured. **Beyond the plan's table, one contradiction fixed:** Step 3 told the skill to ask "Look right? I'll save all of this. Wait for confirmation" and the Rules said "one confirmation prompt" — the user's global `CLAUDE.md` makes every `/checkpoint` behave as `--auto`, so the skill shipped a blocking question the user has standing instructions against. Removed; `--auto` documented as the default. Precedence section deleted after verifying `ls ~/.claude/skills/ \| grep -c checkpoint` = 0. `check_fork` PASS. |
| 8 — Improvement loop + close out | done | `feat/checkpoint-improvement-candidates` | yes (35f82d5) | `/checkpoint` now names pipeline-skill corrections as **improvement candidates** in its Step 5 report and `/tools learn` is repointed at `meta-governance.md` (its "auto-memory handles corrections automatically" claim — silent self-modification — deleted). P6 deliberately not built. **Final: five skills 63,573 → 37,756 (−41%, target ≤38,000 ✓); all 18 121,621 → 98,672; one `/pipeline run` 73,176 → 50,819 (~18.3k → ~12.7k tok, −31%).** Suite **159 passed, 0 failures**; `check_fork` PASS. Budgets not lowered: each file already sits within 122 chars of its cap, so rounding achieved sizes up to the next 500 reproduces them — annotated in the test. **Step 4 correction: no re-link was needed and the plan's command is wrong** (`apply.sh --link` requires `--project-dir`); each skill is a *directory* symlink, so file/subdirectory membership propagates on save — verified in NAR_settlement, and `check_install`'s `membership` check passes in all six projects. **Step 9 correction: `CLAUDE.md` "Start here" deliberately NOT repointed** — the 2026-09-10 handoff's §2a/§2b/§2c/§4 are still open and untouched by this plan, so this is a parallel track, not a successor; the handoff now cross-links the new entry instead. Found in passing: ESG also fails `clone-links`, which the handoff records as fixed — its fix `9349a8e` is on `main` and is not an ancestor of the checked-out `pipeline-adoption` branch. |

**Open decisions** (Task 2 raises the first one; record the answer here when the user gives it):

| # | Decision | Answer |
|---|---|---|
| D1 | `/strategize pap` score scope — keep R-105 as ruled, or divert to `--scope section:`? | **(b) Divert to `--scope section:pre-analysis-plan`** (user, 2026-09-16). Mechanism confirmed by reading `scripts/pipeline.py:483` in full: only a `section:`-prefixed scope writes `state["sections"]`; any other value (incl. a bare `--scope pap`) still overwrites the component. Task 4 implements it: the PAP keeps a mandatory critic and a recorded score, but stops holding the `strategy` gate. Accepted consequence: `pipeline.py next` reports `strategy` as unscored for a PAP-only project. |

---

## Task 0: Baseline and branch hygiene

**Cold start:** nothing beyond the Global constraints. This task reads no skill files.

**Files:** none modified. This task records numbers and confirms the tree is green.

- [ ] **Step 1: Confirm a clean starting tree**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short
```

Expected: only `M skills/new-project-ztp/SKILL.md` (a pre-existing edit) or nothing. If anything
else is modified, stop and ask the user before continuing — this plan assumes a clean base.

- [ ] **Step 2: Confirm the gate is green before you change anything**

```bash
cd /Users/andrew.mueller/Academic/research-claude && ./scripts/check_fork.sh; echo "exit=$?"
```

Expected: `✓ check_fork: PASS`, `exit=0`. If it is already red, stop — fix or report that first.
A refactor started on a red gate cannot prove it did no harm.

- [ ] **Step 3: Confirm the test suite is green**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q
```

Expected: all pass. Record the count in the Progress Log.

- [ ] **Step 4: Record the Level-2 baseline**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 - <<'PY'
import re, glob
tot = 0
for f in sorted(glob.glob('skills/*/SKILL.md')):
    body = re.sub(r'^---\n.*?\n---\n', '', open(f).read(), count=1, flags=re.S)
    tot += len(body)
    print(f"{f.split('/')[1]:18} {len(body):7} chars  ~{len(body)//4:5} tok")
print(f"{'TOTAL':18} {tot:7} chars  ~{tot//4:5} tok")
PY
```

Paste the five target rows (review, strategize, write, discover, checkpoint) into the Progress
Log notes for Task 0. Task 8 re-runs this and compares.

- [ ] **Step 5: Update the Progress Log and stop**

Set Task 0 to `done`, note the pytest count and the five baseline sizes. No commit is needed —
nothing changed.

**STOP. Clear the context window.**

---

## Task 1: Session guards — `careful` and `freeze`

**Cold start:** read these four files to end-of-file before editing anything.

- `hooks/session-guard.py`
- `skills/careful/SKILL.md`
- `skills/freeze/SKILL.md`
- `skills/careful/gotchas.md` and `skills/freeze/gotchas.md`

**What is wrong** (each verified against the hook source, 2026-09-15):

1. `DESTRUCTIVE_PATTERNS` uses `\bgit\s+push\s+--force\b`, which does not match
   `git push origin main --force` — the form anyone actually types.
2. `find . -delete` matches no pattern at all.
3. `re.search(..., re.IGNORECASE)` is applied to every pattern, so `\bgit\s+branch\s+-D\b` also
   blocks the safe `git branch -d`.
4. `check_freeze` denies Edit/Write on `.claude/state/session-guards.json` (hook line 55). **This
   is deliberate** — the code comment says a blanket `.claude/` exemption would let a frozen
   session unfreeze itself. Do not change the hook here. The defect is that
   `skills/freeze/SKILL.md` documents `/freeze off` as an Edit, which the hook denies.
5. `skills/freeze/SKILL.md:56` claims "`.claude/` is always editable" — false for that one file.
6. Both skills' gotchas claim "session-scoped — resets when the conversation ends". False: the
   guard file persists on disk, as the very next gotcha line in `freeze` admits.
7. Both skills' Activation steps show a JSON object containing only their own key. Writing that
   literally clobbers the other guard.
8. The `careful` deny text ends "or rephrase the command", which invites evasion.

**Files:**
- Modify: `hooks/session-guard.py` (the `DESTRUCTIVE_PATTERNS` list, `check_careful`, both deny
  messages)
- Modify: `skills/careful/SKILL.md`, `skills/freeze/SKILL.md`
- Modify: `skills/careful/gotchas.md`, `skills/freeze/gotchas.md`
- Create: `tests/test_session_guard.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/session-guards
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_session_guard.py`:

```python
"""Contracts for hooks/session-guard.py.

Each case below is a command the careful guard claimed to block and did not, or blocked
and should not have. The guard is a safety net the user turns on deliberately; a pattern
that misses the form people actually type is worse than no pattern, because it reports
itself as active.
"""
import json, pathlib, subprocess, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "session-guard.py"


def run(tool_name, tool_input, guards, tmp):
    """Invoke the hook with a project dir whose session-guards.json is `guards`."""
    state = tmp / ".claude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "session-guards.json").write_text(json.dumps(guards))
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    p = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                       text=True, env={"CLAUDE_PROJECT_DIR": str(tmp), "PATH": "/usr/bin:/bin"})
    if not p.stdout.strip():
        return None
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]


CAREFUL_ON = {"careful": {"active": True}}


class TestCarefulBlocks(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def assertBlocked(self, cmd):
        self.assertEqual(run("Bash", {"command": cmd}, CAREFUL_ON, self.tmp), "deny", cmd)

    def assertAllowed(self, cmd):
        self.assertIsNone(run("Bash", {"command": cmd}, CAREFUL_ON, self.tmp), cmd)

    def test_force_push_with_a_refspec_is_blocked(self):
        """The plain `git push --force` form was the only one matched; nobody types it."""
        self.assertBlocked("git push origin main --force")
        self.assertBlocked("git push --force")
        self.assertBlocked("git push origin main -f")
        self.assertBlocked("git push origin main --force-with-lease")

    def test_find_delete_is_blocked(self):
        self.assertBlocked("find . -name '*.rds' -delete")
        self.assertBlocked("find . -type f -exec rm {} +")

    def test_rm_with_flags_before_the_recursive_flag_is_blocked(self):
        self.assertBlocked("rm -rf _cache")
        self.assertBlocked("rm -v -rf _cache")
        self.assertBlocked("rm --recursive _cache")

    def test_lowercase_branch_delete_is_allowed(self):
        """`git branch -d` refuses to delete an unmerged branch. IGNORECASE made it a denial."""
        self.assertAllowed("git branch -d feature/done")

    def test_ordinary_commands_are_allowed(self):
        self.assertAllowed("rm stale.log")
        self.assertAllowed("git push origin feature/x")
        self.assertAllowed("find . -name '*.qmd'")

    def test_sql_drops_stay_case_insensitive(self):
        self.assertBlocked("psql -c 'drop table users'")

    def test_deny_text_does_not_invite_a_workaround(self):
        text = HOOK.read_text()
        self.assertNotIn("rephrase the command", text)

    def test_hook_messages_address_the_user_not_the_model(self):
        """A hook that tells the model to run /freeze off is telling it to evade the guard."""
        text = HOOK.read_text()
        self.assertNotIn("Run /freeze off", text)
        self.assertNotIn("Run /careful off", text)


class TestFreezeDocumentedPathWorks(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_guard_file_is_not_editable_while_frozen(self):
        """Deliberate (hook line 55). Pinned so nobody 'fixes' it into a self-unfreeze hole."""
        guards = {"freeze": {"active": True, "allowed_paths": ["explorations/"]}}
        target = str(self.tmp / ".claude" / "state" / "session-guards.json")
        self.assertEqual(run("Edit", {"file_path": target}, guards, self.tmp), "deny")

    def test_freeze_skill_does_not_document_an_edit_to_deactivate(self):
        """Because the Edit above is denied, /freeze off must be documented as a Bash write."""
        skill = (ROOT / "skills" / "freeze" / "SKILL.md").read_text()
        self.assertIn("session-guards.json", skill)
        self.assertIn("python3", skill, "/freeze off must be documented as a Bash write")

    def test_both_guard_skills_preserve_the_other_key(self):
        for name in ("freeze", "careful"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text()
            self.assertIn("json.loads", text,
                          f"/{name} must read-modify-write session-guards.json, not overwrite it")

    def test_neither_skill_claims_the_guard_resets_itself(self):
        for name in ("freeze", "careful"):
            for f in (ROOT / "skills" / name / "SKILL.md",
                      ROOT / "skills" / name / "gotchas.md"):
                if f.exists():
                    self.assertNotIn("resets when the conversation ends", f.read_text(), str(f))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and watch it fail**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_session_guard.py -q
```

Expected: failures in `test_force_push_with_a_refspec_is_blocked`, `test_find_delete_is_blocked`,
`test_rm_with_flags_before_the_recursive_flag_is_blocked`,
`test_lowercase_branch_delete_is_allowed`, `test_deny_text_does_not_invite_a_workaround`,
`test_hook_messages_address_the_user_not_the_model`,
`test_freeze_skill_does_not_document_an_edit_to_deactivate`,
`test_both_guard_skills_preserve_the_other_key`,
`test_neither_skill_claims_the_guard_resets_itself`.

- [ ] **Step 4: Fix the hook**

In `hooks/session-guard.py`, replace the `DESTRUCTIVE_PATTERNS` list with pre-compiled patterns
so case sensitivity is per-pattern rather than global:

```python
# Compiled per pattern: only the SQL forms are case-insensitive. A global re.IGNORECASE
# made `git branch -d` (which refuses to delete an unmerged branch) as blocked as
# `git branch -D`, so the guard denied a safe command and taught the user to turn it off.
DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\brm\s+(-\S+\s+)*(-[a-zA-Z]*[rf]|--force\b|--recursive\b)"),
     "rm with recursive/force flags"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    # The refspec form is the one people type. `\bgit\s+push\s+--force\b` matched only the
    # bare form and let `git push origin main --force` straight through.
    (re.compile(r"\bgit\s+push\b[^\n]*?(\s--force(-with-lease)?\b|\s-f\b)"), "git push --force"),
    (re.compile(r"\bgit\s+clean\s+-[a-z]*f"), "git clean -f"),
    (re.compile(r"\bgit\s+checkout\s+--\s+\."), "git checkout -- ."),
    (re.compile(r"\bgit\s+branch\s+-D\b"), "git branch -D"),
    (re.compile(r"\bfind\b[^\n]*\s-delete\b"), "find -delete"),
    (re.compile(r"\bfind\b[^\n]*-exec\s+rm\b"), "find -exec rm"),
    (re.compile(r"\bDROP\s+TABLE\b", re.I), "DROP TABLE"),
    (re.compile(r"\bDROP\s+DATABASE\b", re.I), "DROP DATABASE"),
    (re.compile(r"\bchmod\s+777\b"), "chmod 777"),
]
```

In `check_careful`, change the loop to use the compiled pattern and reword the deny text:

```python
    for pattern, description in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return False, (
                f"CAREFUL MODE: Blocked '{description}'. "
                f"Ask the user to run /careful off if this command is intended."
            )
```

In `check_freeze`, reword the deny text the same way:

```python
    return False, (
        f"FREEZE ACTIVE: Edit blocked. File '{os.path.basename(file_path)}' "
        f"is outside allowed paths: {allowed}. Ask the user to run /freeze off."
    )
```

- [ ] **Step 5: Rewrite `skills/freeze/SKILL.md` Activation and Deactivation**

Replace the `## Activation` and `## Deactivation` sections with these. The Bash write is
load-bearing twice over: it preserves the `careful` key, and it is the only route that works
while freeze is active (the hook denies Edit/Write on the guard file by design).

````markdown
## Activation

When the user invokes `/freeze [dirs]`:

**If no directories are given, stop and ask which directories should stay editable.** An empty
`allowed_paths` blocks every edit outside `.claude/`, which is almost never what the user meant.

Write the guard with Bash — never Edit or Write. The hook denies Edit/Write on the guard file
while freeze is active, and a read-modify-write is what preserves an active `careful` guard:

```bash
python3 - <<'PY'
import json, pathlib, datetime
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g["freeze"] = {"active": True,
               "allowed_paths": ["explorations/"],
               "activated_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "reason": "User invoked /freeze"}
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Freeze active. Edits allowed only in: [dirs]. Run `/freeze off` to deactivate."

## Deactivation

When the user invokes `/freeze off`, again with Bash:

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/state/session-guards.json")
g = json.loads(p.read_text()) if p.exists() else {}
g.setdefault("freeze", {})["active"] = False
p.write_text(json.dumps(g, indent=2) + "\n")
PY
```

Confirm: "Freeze deactivated. All paths editable."
````

- [ ] **Step 6: Fix the false gotchas in `skills/freeze/SKILL.md`**

Replace the `## Gotchas` list with:

```markdown
## Gotchas

- **Not session-scoped.** The guard file persists on disk; the hook reads
  `.claude/state/session-guards.json` on every PreToolUse. A new session inherits an active
  freeze. `/freeze off` is what ends it.
- `.claude/` is editable **except** `.claude/state/session-guards.json` itself — otherwise a
  frozen session could unfreeze itself. This is why activation and deactivation use Bash.
- Paths are relative to the project root.
- `/freeze` with no directories would block every edit. The skill refuses instead.
```

- [ ] **Step 7: Apply the same two fixes to `skills/careful/SKILL.md`**

Rewrite Activation/Deactivation to the same read-modify-write Bash form (with `g["careful"] =
{"active": True, ...}` and `g.setdefault("careful", {})["active"] = False`), and replace the
first gotcha bullet:

```markdown
- **Not session-scoped.** The guard file persists on disk. A new session inherits an active
  careful guard; `/careful off` is what ends it.
```

Update the `## Blocked Patterns` table so it matches the hook exactly — add rows for
`git push <remote> <branch> --force`, `--force-with-lease`, `find -delete`, `find -exec rm`, and
`rm --force` / `rm --recursive`; and correct the `git branch -D` row to say that the lowercase
`-d` is **not** blocked.

- [ ] **Step 8: Run the tests**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_session_guard.py -q
```

Expected: all pass.

- [ ] **Step 9: Run the full suite and the gate**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh
```

Expected: all tests pass, `✓ check_fork: PASS`.

- [ ] **Step 10: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add hooks/session-guard.py skills/careful skills/freeze tests/test_session_guard.py && git commit -m "$(cat <<'EOF'
fix(guards): block the force-push form people type, stop blocking safe branch -d

- git push origin main --force matched no pattern; find -delete matched none either
- a global re.IGNORECASE made `git branch -d` as blocked as `-D`
- /freeze off was documented as an Edit, which the hook denies by design; both guard
  skills now read-modify-write the guard file with Bash, preserving the other key
- deny text no longer invites the model to rephrase or to run the off switch itself

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/session-guards -m "Merge fix/session-guards"
```

- [ ] **Step 11: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 2: Scoring correctness — `submit`, and the `strategize` decision

**Cold start:** read these to end-of-file before editing.

- `skills/submit/SKILL.md`
- `docs/decisions/2026-09-08_pipeline-repair-rulings.md` — the sections headed **R-104–R107**,
  **R-133**, and **R-101, R-103**. Read each section in full, not the summary table rows.
- `scripts/pipeline.py`, the `record-score` branch (search for `if a.op == "record-score"`) —
  read the whole branch to end of function.

**Part A — `submit final` coverage check (safe, do it).**

R-133 established that `compute_overall` weights only components that *carry* a score, so a
paper with `code=100` and seven unscored components reads `overall=100.0` and passes
`score --gate submission`. The correction landed in `skills/submit/SKILL.md`'s **Principles**
bullet — but the `### /submit final [journal]` **workflow** never tells anyone to run the check.
A principle the workflow does not execute is documentation, not a gate.

**Part B — `/strategize pap` score scope (DECISION REQUIRED — do not fix unilaterally).**

The audit rates this High: `/strategize pap` records `record-score strategy`, the same component
`/strategize strategy` records, so a PAP critic score can overwrite the strategy-memo score that
`coder` and `data-engineer` gate on.

**But R-105 ruled that this is deliberate:** *"The PAP mode and the strategy-memo mode both
record the same `strategy` component (R-105) — precedent already existed in `/analyze`, where
both `data-engineer` and `coder` record `code`."*

The audit's concern is still narrowly real — `data-engineer` and `coder` write different chunks
of the *same* manuscript, whereas a PAP and a strategy memo are *alternative* artifacts — so a
PAP scored 72 can close a gate a memo scored 88 had opened, and a PAP scored 95 can open the
`strategy` gate with no strategy memo in existence. But R-105 is a ruling the user made, and the
repo's own `CLAUDE.md` warns that §1 of the rulings exists to explain why things that look wrong
are deliberate. **Do not change it without the user's answer.**

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/submit-coverage-check
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_submit_gate.py`:

```python
"""The submission gate renormalises (R-133): `compute_overall` weights only components that
carry a score, so `score --gate submission` can pass on one scored component out of eight.
The skill's Principles section says to check for that. This pins the check into the workflow
the skill actually executes — a principle the workflow never reaches is documentation.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUBMIT = ROOT / "skills" / "submit" / "SKILL.md"


def mode_body(text, heading_re):
    m = re.search(rf"^### {heading_re}.*$", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^(### |## )", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]


class TestFinalGateChecksCoverage(unittest.TestCase):
    def test_final_workflow_runs_state_show_before_trusting_a_pass(self):
        body = mode_body(SUBMIT.read_text(), re.escape("`/submit final"))
        self.assertIsNotNone(body, "submit has no `/submit final` mode section")
        self.assertIn("state show", body,
                      "the final workflow must list every scored component before trusting a PASS")

    def test_the_coverage_rule_is_still_stated(self):
        self.assertIn("scored", SUBMIT.read_text())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and watch it fail**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_submit_gate.py -q
```

Expected: `test_final_workflow_runs_state_show_before_trusting_a_pass` fails.

- [ ] **Step 4: Add the check to the `final` workflow**

In `skills/submit/SKILL.md`, inside `### /submit final [journal]`, insert a new step between the
current step 3 and step 4:

```markdown
3.5. **Coverage check (R-133).** `pipeline.py score` weights only components that carry a
   score, so a PASS can rest on one scored component out of eight. Run
   `python3 .claude/scripts/pipeline.py state show` and list every component the paper
   actually has. If any of them is unscored, report it by name and treat the gate as
   **not met** — an unscored component is not counted at all, it does not fail.
```

- [ ] **Step 5: Run the tests and the gate**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh
```

Expected: all pass, `✓ check_fork: PASS`.

- [ ] **Step 6: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/submit/SKILL.md tests/test_submit_gate.py && git commit -m "$(cat <<'EOF'
fix(submit): put the R-133 coverage check in the final workflow, not just the principles

`score --gate submission` renormalises over scored components only, so a PASS can rest on
one component out of eight. The rule was stated in Principles and never executed by the
workflow that runs the gate.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/submit-coverage-check -m "Merge fix/submit-coverage-check"
```

- [ ] **Step 7: Put decision D1 to the user, then stop**

Ask exactly this, and record the answer in the **Open decisions** table:

> `/strategize pap` records its critic score into the `strategy` component — the same component
> `/strategize strategy` records. R-105 ruled that deliberate, citing `/analyze` (where
> `data-engineer` and `coder` both record `code`) as precedent. The 2026-09-15 audit rates it
> High severity, because a PAP and a strategy memo are alternative artifacts rather than two
> passes over one artifact: a PAP scored 72 overwrites a memo scored 88 that `coder` and
> `data-engineer` gate on, and a PAP scored 95 opens the `strategy` gate with no memo at all.
>
> Three options:
> - **(a) Keep R-105 as ruled.** Change nothing. Add one sentence to `skills/strategize/SKILL.md`
>   saying the overwrite is intended, so the next audit does not re-raise it.
> - **(b) Divert the PAP score** to `--scope section:pre-analysis-plan`. Verified against
>   `scripts/pipeline.py`: only a `section:`-prefixed scope writes to `state["sections"]`; any
>   other value (including a bare `--scope pap`) still overwrites the component. This is the same
>   mechanism R-101 used for `/write humanize`. The PAP still gets a mandatory critic and a
>   recorded score; it stops holding the `strategy` gate.
> - **(c) Something else** — e.g. record `strategy` only when no memo score exists.
>
> Note that (b) changes what `pipeline.py next` reports for a PAP-only project, so `/pipeline`
> would treat `strategy` as unscored until a memo is written. That may be correct, or may be
> exactly what you do not want.

Do **not** implement any option in this session. Record the answer and let the next session that
touches `strategize` (Task 4) carry it out.

- [ ] **Step 8: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 3: `review` — the biggest single win

**Cold start:** read these to end-of-file before editing.

- `skills/review/SKILL.md` (330 lines — the file you are refactoring)
- `tests/test_review_contracts.py` (it pins three strings in that file)
- `agents/coder-critic.md` and `agents/strategist-critic.md` (they already read the rubrics you
  are about to delete from SKILL.md — confirm that before deleting)
- `skills/review/templates/code-review-16-categories.md`
- `skills/review/templates/disposition-pool.md` and `agents/editor.md` (these two **contradict**
  each other on the 0-FATAL case; you must decide which is right)

**Baseline:** 18,058 chars. **Target: ≤ 11,000 chars.**

**What moves and why.** Every block below is either (a) a rubric the *critic agent* already reads
for itself, so loading it into the orchestrator's context is pure waste, or (b) a duplicate that
has drifted from its template.

| Block (current lines) | Disposition |
|---|---|
| `#### Full 12-Category Code Review Checklist` (164–175) | **Delete the count and the table.** The template and `agents/coder-critic.md` both say **16**. Replace with one line naming `.claude/skills/review/templates/code-review-16-categories.md` and stating that categories 1–3 run only in-pipeline or via `--methods`. |
| `#### Severity Calibration Examples` (176–202) | **Move** to `skills/review/config/scoring-rubrics.md` (coder-critic section) if not already there; delete from SKILL.md. `coder-critic` reads that file. |
| `#### 4-Phase Econometrics Review Protocol` (207–236) | **Move** to a new `skills/review/templates/causal-audit-4-phases.md`; name it in the `--methods` step. `strategist-critic` is the only consumer. |
| `#### Overall Assessment Scale` (237–247) | **Move** into the same new file. Keep in SKILL.md only the sentence "The label is reported beside the score, not instead of it" and the `scoring-rubrics.md` pointer. |
| `## Bundled Resources` (289–318) | **Delete the whole section.** Each file gets named in the step that reads it, or in the agent that reads it. |
| `## Principles` (319–330) | **Delete.** Every line is either a restatement of the routing table above it or belongs in `rules/agents.md`. |
| `templates/disposition-pool.md` | **Currently unbound and contradicts `agents/editor.md`** on the 0-FATAL case (Minor vs Major-with-4+-ADDRESSABLE). Read both, decide, make them agree, then name the file in the `--peer` Phase 1 step where the editor picks dispositions. |
| `templates/referee-report-template.md` | **Currently unbound** and drifted from both referee agents. Either name it in `--peer` Phase 2 or delete it and let the agents own their format. Read all three before choosing. |

**Must survive verbatim** (pinned by `tests/test_review_contracts.py`): the
`## Verifier Pass/Fail Definition` heading, `.claude/agents/verifier.md` inside it, and
`git status --porcelain`. Every `record-score` command line in every mode also survives.

**Files:**
- Modify: `skills/review/SKILL.md`
- Create: `skills/review/templates/causal-audit-4-phases.md`
- Modify: `skills/review/config/scoring-rubrics.md`
- Modify or delete: `skills/review/templates/disposition-pool.md`,
  `skills/review/templates/referee-report-template.md`
- Create: `tests/test_skill_contracts.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b refactor/review-skill
```

- [ ] **Step 2: Write the step-binding test with a shrinking allowlist**

This is the test that makes "progressive disclosure" mean something mechanical. It asserts that
every bundled file is named **inside a step or mode section** of its SKILL.md, or inside an agent
file — not merely catalogued in a resources table at the bottom. `KNOWN_UNBOUND` is a ratchet:
each later task deletes its own entries, and nothing may ever be added.

Create `tests/test_skill_contracts.py`:

```python
"""Progressive-disclosure and size contracts for skills/.

A bundled file must be named in the step that reads it, or in the agent that reads it. A
`## Bundled Resources` table at the end of a SKILL.md does not count: it tells the model what
exists, never when to read it, so the model either reads nothing (the file rots into an orphan
that contradicts its inline summary) or reads everything defensively. Both were found across
this tree on 2026-09-15.

KNOWN_UNBOUND is a ratchet. Entries come out as each skill is refactored. Nothing goes in.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Sections that CATALOGUE files rather than USE them. Stripped before the search, so a file
# named only here still counts as unbound.
CATALOGUE = re.compile(r"^## (Bundled [Rr]esources|Resources|Principles|Rules)\b.*?(?=^## |\Z)",
                       re.M | re.S)

KNOWN_UNBOUND = {
    # Task 4 — strategize
    # Task 5 — write
    # Task 6 — discover
    "skills/discover/references/pdf-processing.md",
    "skills/discover/templates/data-assessment.md",
    "skills/discover/templates/lit-review-entry.md",
    "skills/discover/templates/research-ideas.md",
    "skills/discover/templates/research-spec.md",
    # Task 7 — checkpoint
    "skills/checkpoint/templates/memory-entry-types.md",
    "skills/checkpoint/templates/research-journal-entry.md",
    "skills/checkpoint/templates/session-report-entry.md",
    # Not in this plan's scope — pipeline, revise, submit
    "skills/pipeline/references/setup.md",
    "skills/pipeline/references/talk.md",
    "skills/revise/templates/diplomatic-disagreement.md",
    "skills/revise/templates/response-tracker.md",
    "skills/submit/templates/audit-10-checks.md",
}

# Level-2 budget in characters of SKILL.md body (frontmatter excluded). Ratchet downward only.
BUDGET = {
    "review": 11000,
    "strategize": 8000,
    "write": 7500,
    "discover": 6000,
    "checkpoint": 5500,
}


def agent_text():
    return "\n".join(p.read_text() for p in (ROOT / "agents").glob("*.md"))


def body_of(skill_md):
    return re.sub(r"^---\n.*?\n---\n", "", skill_md.read_text(), count=1, flags=re.S)


class TestStepBinding(unittest.TestCase):
    def test_every_bundled_file_is_bound_to_a_step_or_an_agent(self):
        agents = agent_text()
        unbound = []
        for skill_dir in sorted((ROOT / "skills").iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            steps = CATALOGUE.sub("", skill_md.read_text())
            for f in sorted(skill_dir.rglob("*.md")):
                if f.name == "SKILL.md":
                    continue
                rel = f.relative_to(ROOT).as_posix()
                named = rel in steps or f.name in steps or rel in agents or f.name in agents
                if not named and rel not in KNOWN_UNBOUND:
                    unbound.append(rel)
        self.assertEqual([], unbound,
                         "bundled files named in no step and no agent (bind them, or delete them)")

    def test_the_allowlist_has_no_stale_entries(self):
        """An entry that is now bound must come out, or the ratchet stops ratcheting."""
        agents = agent_text()
        stale = []
        for rel in sorted(KNOWN_UNBOUND):
            f = ROOT / rel
            if not f.exists():
                stale.append(f"{rel} (file is gone)")
                continue
            skill_md = ROOT / "skills" / rel.split("/")[1] / "SKILL.md"
            steps = CATALOGUE.sub("", skill_md.read_text())
            if rel in steps or f.name in steps or rel in agents or f.name in agents:
                stale.append(f"{rel} (now bound)")
        self.assertEqual([], stale, "remove these from KNOWN_UNBOUND")


class TestLevelTwoBudget(unittest.TestCase):
    def test_refactored_skills_stay_under_budget(self):
        over = []
        for name, cap in sorted(BUDGET.items()):
            n = len(body_of(ROOT / "skills" / name / "SKILL.md"))
            if n > cap:
                over.append(f"{name}: {n} chars > {cap}")
        self.assertEqual([], over, "SKILL.md bodies load in full on every invocation")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and watch exactly two things fail**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_skill_contracts.py -q
```

Expected failures:
- `test_every_bundled_file_is_bound_to_a_step_or_an_agent` naming
  `skills/review/templates/disposition-pool.md` and
  `skills/review/templates/referee-report-template.md` (review's two unbound files — deliberately
  absent from `KNOWN_UNBOUND`, because this task binds them).
- `test_refactored_skills_stay_under_budget` naming `review: 18058 chars > 11000` and
  `strategize: 15966 chars > 8000`.

`strategize` being over budget is expected and stays red until Task 4. To keep this task's
verification unambiguous, run the budget test filtered:

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -c "
import sys; sys.path.insert(0,'tests')
from test_skill_contracts import ROOT, body_of
n = len(body_of(ROOT/'skills'/'review'/'SKILL.md')); print(f'review body: {n} chars (target 11000)')"
```

- [ ] **Step 4: Resolve the two contradictions before deleting anything**

Read `skills/review/templates/disposition-pool.md` and `agents/editor.md` in full. They disagree
on what 0 FATAL concerns means: one says Minor Revisions, the other says Major Revisions when
there are 4+ ADDRESSABLE. Decide which is right, edit the loser, and note the decision in the
commit message. Do the same for `templates/referee-report-template.md` against
`agents/domain-referee.md` and `agents/methods-referee.md`.

If a template turns out to add nothing the agent does not already own, delete it — a deleted file
is the cheapest possible progressive disclosure. `scripts/check_paths.py` will catch any
reference left dangling.

- [ ] **Step 5: Create `skills/review/templates/causal-audit-4-phases.md`**

Move the current lines 207–247 of `skills/review/SKILL.md` — `#### 4-Phase Econometrics Review
Protocol` and `#### Overall Assessment Scale` — into this new file verbatim, under a `# Causal
Audit — 4-Phase Protocol` heading. Add one line at the top: `Read by strategist-critic for
`/review --methods` and for the comprehensive review's causal-design audit.`

- [ ] **Step 6: Cut `skills/review/SKILL.md` per the disposition table above**

Work top to bottom. After each block, re-run the size command from Step 3 so you can see the
number fall. The `### Causal Audit (--methods)` section becomes:

```markdown
### Causal Audit (`--methods`)

Dispatch **strategist-critic** standalone for a full 4-phase causal inference review, per
`.claude/skills/review/templates/causal-audit-4-phases.md`.

The assessment label (SOUND / MINOR ISSUES / MAJOR ISSUES / CRITICAL ERRORS) is reported beside
the score, not instead of it. The score is 100 minus the fixed per-severity deductions in
`.claude/skills/review/config/scoring-rubrics.md` (Strategist-Critic).

Save report to `quality_reports/reviews/strategist-critic_<date>.md`
```

And `#### Full 12-Category Code Review Checklist` becomes:

```markdown
#### Code review checklist

The 16 categories are `.claude/skills/review/templates/code-review-16-categories.md`, which
coder-critic reads for itself. Categories 1–3 (strategic alignment) run only within the pipeline
or via `--methods`; standalone runs cover code quality only.
```

- [ ] **Step 7: Delete `## Bundled Resources` and `## Principles`**

Before deleting the resources table, confirm each file it lists is named either in a mode section
of SKILL.md or in an agent file — the Step 3 test is what tells you. `gotchas.md`,
`manuscript-review-8-categories.md`, `theory-review-4-phases.md`, `talk-review-6-categories.md`,
`data-review-6-categories.md` and `claim-evidence-table.md` are already named in agent files and
need no SKILL.md binding.

- [ ] **Step 8: Verify the pinned strings survived**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_review_contracts.py -q
```

Expected: all pass. If `test_the_review_skill_defers_to_the_agent_rather_than_restating` fails,
you moved something into the Verifier section that must not be there.

- [ ] **Step 9: Confirm every `record-score` call site survived**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git diff main -- skills/review/SKILL.md | grep '^-' | grep -c 'record-score'
```

Expected: `0`. If it is not 0, you deleted a scoring call site — restore it (Global constraint 3).

- [ ] **Step 10: Full verification**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q; ./scripts/check_fork.sh
```

Expected: everything passes except `test_refactored_skills_stay_under_budget`, which still names
`strategize` only. `check_fork` must be `✓ PASS`.

- [ ] **Step 11: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/review tests/test_skill_contracts.py && git commit -m "$(cat <<'EOF'
refactor(review): bind templates to steps, drop rubrics the critics already read

SKILL.md carried the 4-phase econometrics protocol, the severity calibration table and a
"12-category" code checklist — rubrics strategist-critic and coder-critic read for
themselves, loaded into the orchestrator's context where nothing consumes them. The
checklist had also drifted: the template and the agent both say 16.

Adds tests/test_skill_contracts.py: every bundled file must be named in the step that reads
it or in the agent that reads it, and SKILL.md bodies carry a character budget. Both are
ratchets with an allowlist that only shrinks.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff refactor/review-skill -m "Merge refactor/review-skill"
```

- [ ] **Step 12: Update the Progress Log with the new review body size, and stop**

**STOP. Clear the context window.**

---

## Task 4: `strategize`

**Cold start:** read these to end-of-file before editing.

- `skills/strategize/SKILL.md` (300 lines)
- `skills/strategize/templates/pre-strategy-report.md`
- `skills/strategize/references/pap-interview-flow.md`
- `skills/strategize/templates/pap-templates/osf.md` (specifically §6, the observational
  adaptation)
- `tests/test_skill_contracts.py` — the ratchet you are about to satisfy
- This plan's **Open decisions** table — if D1 is answered, implement it here

**Baseline:** 15,966 chars. **Target: ≤ 8,000 chars.**

| Block (current lines) | Disposition |
|---|---|
| `## Pre-Strategy Report` (28–72) | **Delete the pasted form.** `templates/pre-strategy-report.md` already holds it. Replace with one line in Step 1 naming that file. |
| `#### Interactive PAP Interview` (85–97) | **Delete.** `references/pap-interview-flow.md` holds the flow. Name it in the interview step. |
| `#### PAP Sections` (98–112) | **Delete.** Repeats the `pap-templates/*` files. |
| `#### Platform-Specific PAP Templates` (113–134) | **Replace with a one-line rule:** the PAP step reads only the chosen platform's template — `.claude/skills/strategize/templates/pap-templates/{aea-rct,egap,osf}.md`. Do not list their contents. |
| `#### Observational Study PAP Adaptation` (135–145) | **Delete.** Repeats `pap-templates/osf.md` §6. Confirm by reading that section before deleting. |
| `## Bundled Resources` (249–288) | **Delete the whole section** (4 sub-tables). |
| `## Principles` (289–300) | **Delete.** |
| Design checklists | **Add a binding in Step 3:** pass only the chosen design's checklist — `.claude/skills/strategize/templates/design-checklists/<design>.md`. Today no step picks one, so the strategist has no instruction to read one rather than all seven. |
| Iterate rule | **Unify.** Strategy mode says "CRITICAL"; PAP mode says "<80". Make both `<80`, matching `record-score` and the registry gate. |

**Do not touch:** the `record-score` command lines, the mandatory strategist-critic dispatch in
PAP mode (R-103 made it mandatory on purpose), or the Pre-Theory Report structure.

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b refactor/strategize-skill
```

- [ ] **Step 2: Confirm the current red**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_skill_contracts.py -q
```

Expected: `test_refactored_skills_stay_under_budget` fails naming `strategize: 15966 chars > 8000`.

- [ ] **Step 3: Read each template before deleting the block that duplicates it**

For each of the four "Delete — repeats X" rows, open X and confirm it genuinely carries the
content. If the SKILL.md copy has something the template lacks, move that something into the
template first. A deletion that loses content is the failure mode this step exists to prevent.

- [ ] **Step 4: Make the cuts, top to bottom**

After each block, check the size:

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -c "
import re; b=re.sub(r'^---\n.*?\n---\n','',open('skills/strategize/SKILL.md').read(),count=1,flags=re.S)
print(f'strategize body: {len(b)} chars (target 8000)')"
```

- [ ] **Step 5: Add the design-checklist binding**

In the `### /strategize [question]` mode, Step 3 (dispatch), add:

```markdown
Pass the strategist **only the chosen design's** checklist —
`.claude/skills/strategize/templates/design-checklists/<design>.md`, one of `did`,
`event-study`, `iv`, `rdd`, `structural`, `descriptive`. Naming all seven is what makes an
agent read all seven.
```

- [ ] **Step 6: Unify the iterate rule**

Find both iterate rules (strategy mode and PAP mode). Make both read: below 80 → creator revises
→ critic re-scores; `pipeline.py state strike strategist` per failing round; strike three →
escalate to the registry's escalation target with a specific question.

- [ ] **Step 7: Implement decision D1 if it is answered**

Check the **Open decisions** table. If D1 is unanswered, leave the PAP `record-score` line exactly
as it is and say so in the commit message. If the answer was **(a)**, add the one-sentence note.
If **(b)**, change the PAP recording line to
`... state record-score strategy <score> --critic strategist-critic --deductions <total> --scope section:pre-analysis-plan --report ...` and add a line explaining that only a `section:`-prefixed
scope avoids overwriting the component.

- [ ] **Step 8: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git diff main -- skills/strategize/SKILL.md | grep '^-' | grep -c 'record-score'
```

Expected: `0` if D1 is unanswered or (a). If (b), expect `1` and confirm the replacement line is
present in the `+` side.

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q; ./scripts/check_fork.sh
```

Expected: all tests pass (the budget test is now fully green for review and strategize),
`✓ check_fork: PASS`.

- [ ] **Step 9: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/strategize && git commit -m "$(cat <<'EOF'
refactor(strategize): point at the templates instead of pasting them

The Pre-Strategy Report, the PAP interview, the PAP section list and the observational
adaptation were all inline copies of files that already ship. Step 3 now passes the
strategist only the chosen design's checklist; naming all seven is what made an agent read
all seven. Iterate rule unified on <80 in both modes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff refactor/strategize-skill -m "Merge refactor/strategize-skill"
```

- [ ] **Step 10: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 5: `write`

**Cold start:** read these to end-of-file before editing.

- `skills/write/SKILL.md` (179 lines)
- `skills/write/templates/section-templates.md`
- `skills/write/templates/cleanup-patterns.md`
- `skills/write/templates/style-extraction-protocol.md`
- `agents/writer.md` and `agents/writer-critic.md`
- The **R-101, R-103** section of `docs/decisions/2026-09-08_pipeline-repair-rulings.md` — it
  explains why `/write humanize` records with `--scope section:` and why that prefix is
  load-bearing

**Baseline:** 11,290 chars. **Target: ≤ 7,500 chars.**

| Block (current lines) | Disposition |
|---|---|
| `## Section Standards` (134–148) | **Delete.** Repeats `templates/section-templates.md`. Read that file first to confirm. |
| Paper-type list inside `#### 2. Paper Type Detection` | **Reduce to the detection rule plus a pointer.** The type definitions belong in the template. |
| `## Bundled Resources (Level 3)` (157–173) | **Delete.** |
| `## Principles` (174–179) | **Delete.** |
| Pointer at line ~136 | **Fix.** It names `writer.md` as holding the section templates; they are in `templates/section-templates.md`. Verify by reading both, then correct. |
| Style-guide workflow | **Move** the procedure to `templates/style-extraction-protocol.md` (which already holds most of it) and leave the mode section as dispatch + the protocol path. Check the protocol's self-citation step, which the skill currently omits. |
| `templates/cleanup-patterns.md` | **Bind it.** The description promises a cleanup pass but no drafting step reads this file. Add a **Step 4b (cleanup)** between the writer dispatch and the writer-critic dispatch that names it. |

**Do not touch:** the `record-score ... --scope section:<name>` line in the humanize mode. R-101
established that only a `section:`-prefixed scope avoids overwriting the `manuscript` component,
and a proofread covering four of eight categories must never be recorded as a full review.

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b refactor/write-skill
```

- [ ] **Step 2: Add `write` to the budget and watch it fail**

In `tests/test_skill_contracts.py`, `BUDGET` already contains `"write": 7500`. Confirm the red:

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_skill_contracts.py -q
```

Expected: `test_refactored_skills_stay_under_budget` fails naming `write: 11290 chars > 7500`.

- [ ] **Step 3: Read before deleting**

Open `templates/section-templates.md` and confirm it carries the Section Standards content.
Open `agents/writer.md` and confirm it does **not** — that is the pointer bug you are fixing.

- [ ] **Step 4: Make the cuts and add Step 4b**

The new cleanup step:

```markdown
#### 4b. Cleanup pass

After the writer returns and before dispatching writer-critic, apply
`.claude/skills/write/templates/cleanup-patterns.md` to the drafted section. This is the pass
the skill's description promises; without it the description is a claim no step delivers.
```

- [ ] **Step 5: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git diff main -- skills/write/SKILL.md | grep '^-' | grep -cE 'record-score|scope section:'
```

Expected: `0`.

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q; ./scripts/check_fork.sh
```

Expected: all pass, `✓ check_fork: PASS`.

- [ ] **Step 6: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/write && git commit -m "$(cat <<'EOF'
refactor(write): bind the cleanup pass, drop the duplicated section standards

Section Standards duplicated templates/section-templates.md, and the pointer to them named
agents/writer.md, which does not hold them. cleanup-patterns.md was promised by the skill
description and read by no step; it is now Step 4b.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff refactor/write-skill -m "Merge refactor/write-skill"
```

- [ ] **Step 7: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 6: `discover`

**Cold start:** read these to end-of-file before editing.

- `skills/discover/SKILL.md` (170 lines)
- `skills/discover/templates/interview-flow.md`
- `skills/discover/templates/research-spec.md`
- `skills/discover/templates/data-assessment.md`
- `skills/discover/templates/research-ideas.md`
- `skills/discover/references/pdf-processing.md`
- `skills/discover/templates/lit-review-entry.md`
- `agents/explorer.md` and `agents/explorer-critic.md`
- `rules/literature-search-order.md`

**Baseline:** 9,733 chars. **Target: ≤ 6,000 chars.** Five unbound files to resolve — the most of
any skill.

| Block | Disposition |
|---|---|
| Inline interview categories in `### /discover interview` | **Delete.** They disagree with `templates/interview-flow.md`. Read the template, keep whichever content is right, bind the template in the interview step. |
| The pasted 8-section research spec (lines 47–55) | **Delete.** It is a duplicate of `templates/research-spec.md`. The spec step writes *with* that template. |
| Grades A–D vs A–F | **Reconcile.** SKILL.md says A–D, `templates/data-assessment.md` says A–F. Pick one — the explorer-critic's 6 categories are the tie-breaker — and make both agree. |
| `### /discover lit` history note (69–86) | **Reduce to one line:** superseded by `/lit-position`. |
| Literature principles inside the `lit` section | **Delete.** Stale; `rules/literature-search-order.md` is authoritative. Name that rule in the data step, where the local-first order actually applies. |
| `## Bundled Resources` (146–159) | **Delete.** |
| `## Principles` (160–170) | **Delete.** |
| `templates/data-assessment.md` | **Bind** in the data step. |
| `templates/research-ideas.md` | **Bind** in the ideate step. |
| `templates/research-spec.md` | **Bind** in the interview/spec step. |
| `references/pdf-processing.md` | **Decide:** bind it to whichever step processes PDFs, or delete it. It is a leftover from the retired `lit` mode. |
| `templates/lit-review-entry.md` | **Delete** — the `lit` mode it belonged to is superseded by `/lit-position`. Confirm `/lit-position` does not reference it before deleting. |
| `WebSearch`, `WebFetch` in `allowed-tools` | **Remove** if no step uses them after the cuts. Unused pre-approvals widen the skill's permissions for nothing. |

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b refactor/discover-skill
```

- [ ] **Step 2: Confirm the red, then shrink the allowlist**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_skill_contracts.py -q
```

Expected: `test_refactored_skills_stay_under_budget` fails on `discover: 9733 > 6000`. The five
discover entries in `KNOWN_UNBOUND` are still allowlisted, so the binding test passes.

**Remove all five `skills/discover/...` lines from `KNOWN_UNBOUND` now, before editing the
skill.** Re-run: the binding test should now fail naming those five. That is your red.

- [ ] **Step 3: Read every template before cutting the block that duplicates it**

Three of these disagree with SKILL.md (interview categories, spec sections, grade scale). For
each, decide which copy is correct and fix the survivor. Do not assume the template is right.

- [ ] **Step 4: Make the cuts and add the bindings**

Each of `research-spec.md`, `data-assessment.md`, `research-ideas.md` and `interview-flow.md`
must be named in the step that uses it. For `pdf-processing.md` and `lit-review-entry.md`, either
bind or delete — if you delete, `scripts/check_paths.py` catches any dangling reference.

- [ ] **Step 5: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git diff main -- skills/discover/SKILL.md | grep '^-' | grep -c 'record-score'
```

Expected: `0`.

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q; ./scripts/check_fork.sh
```

Expected: all pass — including `test_the_allowlist_has_no_stale_entries`, which now proves the
five discover files are genuinely bound. `✓ check_fork: PASS`.

- [ ] **Step 6: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/discover tests/test_skill_contracts.py && git commit -m "$(cat <<'EOF'
refactor(discover): bind five orphaned templates, delete the copies that disagreed with them

The interview categories, the 8-section spec and the grade scale each existed twice and
disagreed (A-D in the skill, A-F in the template). The templates are now read at the step
that uses them and the inline copies are gone. The retired lit mode's leftovers resolved.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff refactor/discover-skill -m "Merge refactor/discover-skill"
```

- [ ] **Step 7: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 7: `checkpoint`

**Cold start:** read these to end-of-file before editing.

- `skills/checkpoint/SKILL.md` (245 lines)
- `rules/logging.md` — it is the canonical home of the entry formats
- `rules/session-handoff.md` — the staleness sweep and the handoff dry-run
- `rules/ai-disclosure.md` (the `ai_use_log.md` confirmation, around line 116)
- `skills/checkpoint/templates/session-report-entry.md`,
  `research-journal-entry.md`, `memory-entry-types.md`
- The user's global `~/.claude/CLAUDE.md` **Checkpoint behavior** section — `/checkpoint` is
  always `--auto`; it must never stop to ask "look right?"
- This repo's `CLAUDE.md` **Checkpoint / session-report location** — `SESSION_REPORT.md` lives at
  `docs/SESSION_REPORT.md` here, not the repo root

**Baseline:** 8,526 chars. **Target: ≤ 5,500 chars.**

| Block (current lines) | Disposition |
|---|---|
| The `4b` SESSION_REPORT entry format (113–138) | **Delete the pasted format.** `rules/logging.md` is the canonical copy; `templates/session-report-entry.md` is the bundled one. Name the template at step 4b. |
| The `4c` research-journal entry format (139–151) | **Delete the pasted format.** Bind `templates/research-journal-entry.md` at 4c. |
| The `4a` "Qualifies for memory" lists (95–112) | **Reduce to a pointer.** Bind `templates/memory-entry-types.md` at 4a; keep only the sentence that memory is for future conversations. |
| `## Obsidian Config Setup (on demand)` (205–218) | **Move** to `skills/checkpoint/references/obsidian-setup.md` and name it in the `--setup-obsidian` flag row. It runs on explicit opt-in only, so it has no business loading every checkpoint. |
| `## Bundled Resources` (219–229) | **Delete.** |
| `## Precedence` (243–245) | **Delete.** It names `~/.claude/skills/checkpoint`, which does not exist. Verify with `ls ~/.claude/skills/ \| grep checkpoint` before deleting. |
| `## Rules` (230–242) | **Keep, but trim** to the lines that change behaviour: never invent progress, don't duplicate, state file is local-only. Drop the restatements. |

**Three things the rules require that the skill currently drops — add them:**

- [ ] The `Plan staleness sweep:` report line required by `rules/session-handoff.md`. Step 1
  already gathers the state for it; Step 5 never reports it.
- [ ] The handoff reference dry-run from `rules/session-handoff.md` §2.
- [ ] The `ai_use_log.md` confirmation required by `rules/ai-disclosure.md`.

**Do not add** a blocking prompt anywhere. The user's global rule forces `--auto` semantics: this
skill gathers, writes, and reports. Everything new here is a **report line**, not a question.

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b refactor/checkpoint-skill
```

- [ ] **Step 2: Confirm the red, then shrink the allowlist**

Remove the three `skills/checkpoint/...` lines from `KNOWN_UNBOUND` in
`tests/test_skill_contracts.py`, then:

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_skill_contracts.py -q
```

Expected: binding test fails on the three checkpoint templates; budget test fails on
`checkpoint: 8526 > 5500`.

- [ ] **Step 3: Verify the stale Precedence claim before deleting it**

```bash
ls ~/.claude/skills/ | grep -c checkpoint
```

Expected: `0`. If it is not 0, the section is not stale — leave it and note that in the commit.

- [ ] **Step 4: Make the cuts, move the Obsidian setup, add the three missing report lines**

The Step 5 confirmation block gains three lines:

```
- Plan staleness sweep: [none | fixed: <plan> | flagged: <plan>]
- Handoff reference dry-run: [clean | N unresolved]
- ai_use_log.md: [N entries | absent — no agent work this session]
```

- [ ] **Step 5: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q; ./scripts/check_fork.sh
```

Expected: all pass, `✓ check_fork: PASS`.

- [ ] **Step 6: Smoke-test the skill against this repo**

Run `/checkpoint --dry-run` in this repo. Confirm the output names `docs/SESSION_REPORT.md` (not
the repo root), includes the three new report lines, and asks no questions.

- [ ] **Step 7: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/checkpoint tests/test_skill_contracts.py && git commit -m "$(cat <<'EOF'
refactor(checkpoint): bind the three entry templates, restore three dropped report lines

The SESSION_REPORT, research-journal and memory formats were pasted inline while their
templates went unread. The Obsidian setup walkthrough loaded on every checkpoint despite
running only on explicit opt-in. Adds the plan staleness sweep, the handoff dry-run and the
ai_use_log confirmation that rules/session-handoff.md and rules/ai-disclosure.md require —
as report lines, not prompts, per the user's forced --auto.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff refactor/checkpoint-skill -m "Merge refactor/checkpoint-skill"
```

- [ ] **Step 8: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 8: Improvement loop, re-link, and close out

**Cold start:** read these to end-of-file before editing.

- `rules/meta-governance.md`
- `skills/checkpoint/SKILL.md` (as refactored in Task 7)
- `skills/promote/SKILL.md`
- `hooks/context-monitor.py` — the `/tools learn` nudge near the end
- `skills/tools/SKILL.md` — the `learn` subcommand
- This plan's **Progress Log** and **Open decisions**

**The design.** The audit's P6 proposes a `rules/skill-improvement.md` plus one closing step in
all 18 SKILL.md files. **Do not build that** — 18 new instruction blocks read on every invocation
is the exact tax this plan exists to remove, and `rules/meta-governance.md` already defines a
better loop: `/pipeline` surfaces Suggested Learnings from recurring strikes, escalations and
first-pass ≥ 90; promotion requires a pattern validated across 3+ projects; `/promote` is the only
landing mechanism; the user approves every one.

The real gap is narrow: `/checkpoint` Step 1 already scans the conversation for "decisions,
corrections, or learnings", and Step 4a already saves user corrections as `feedback`-type
memory — but that terminates in auto-memory and never reaches `/promote`. Close it there. One
edit, one skill, no per-skill instruction tax, and the 3+ projects bar stays intact because a
correction lands as a project-level note first and is promoted only when it recurs.

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b feat/checkpoint-improvement-candidates
```

- [ ] **Step 2: Add the candidate line to `/checkpoint` Step 5**

In `skills/checkpoint/SKILL.md`, extend the Step 5 confirmation block:

```
- Pipeline improvement candidates: [none | N — <skill>: <one-line correction>]
```

And add to Step 4a, after the memory write:

```markdown
**If a saved `feedback` memory is a correction to a pipeline skill, agent or rule** (as opposed
to a project-specific preference), name it in the Step 5 report as an improvement candidate with
the file it would touch. Do not edit the shared tree and do not prompt — `.claude/rules/
meta-governance.md` requires a pattern validated across 3+ projects and `/promote` is the only
landing mechanism. The report line is what carries it forward.
```

- [ ] **Step 3: Repoint the `/tools learn` stub**

In `skills/tools/SKILL.md`, replace the one-sentence `learn` stub with a pointer to
`.claude/rules/meta-governance.md` and `/promote`. Delete the "auto-memory handles corrections
automatically" claim — silent self-modification is exactly what meta-governance forbids.

Check `hooks/context-monitor.py`'s nudge text still names a real subcommand after this change
(`scripts/check_refs.py`'s `skill-refs` criterion will catch it if not).

- [ ] **Step 4: Re-link the projects**

Membership under `skills/` changed in Tasks 3, 6 and 7 (files created and deleted). Edits
propagate through the symlinks on save; **membership does not.**

```bash
cd /Users/andrew.mueller/Academic/research-claude && ./apply.sh --link && ./scripts/check_install.sh --all; echo "exit=$?"
```

Expected: `exit=0`. If a project reports a missing or dangling link, that is a file you deleted
in Task 3/6/7 that something still references — fix the reference, do not restore the file
blindly.

- [ ] **Step 5: Measure the result**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 - <<'PY'
import re, glob
PIPE = ["pipeline", "lit-position", "discover", "strategize", "analyze", "write", "review", "submit"]
tot = pipe = 0
for f in sorted(glob.glob('skills/*/SKILL.md')):
    name = f.split('/')[1]
    body = re.sub(r'^---\n.*?\n---\n', '', open(f).read(), count=1, flags=re.S)
    tot += len(body)
    if name in PIPE:
        pipe += len(body)
    print(f"{name:18} {len(body):7} chars  ~{len(body)//4:5} tok")
print(f"\n{'ALL 18':18} {tot:7} chars  ~{tot//4:5} tok   (baseline 121,621 / ~30,399)")
print(f"{'PIPELINE RUN':18} {pipe:7} chars  ~{pipe//4:5} tok   (baseline  73,176 / ~18,294)")
PY
```

- [ ] **Step 6: Ratchet the budgets down to what you actually achieved**

In `tests/test_skill_contracts.py`, lower each `BUDGET` entry to the measured size rounded up to
the next 500 chars. This locks the gain in — the next person to paste a table into one of these
files gets a red test instead of a silent regression.

- [ ] **Step 7: Full verification**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && ./scripts/check_install.sh --all; echo "exit=$?"
```

Expected: all green, `exit=0`.

- [ ] **Step 8: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/checkpoint skills/tools tests/test_skill_contracts.py && git commit -m "$(cat <<'EOF'
feat(checkpoint): surface pipeline-skill corrections as promotion candidates

/checkpoint already scans the transcript for corrections and saves them as feedback memory;
that terminated in auto-memory and never reached /promote. It now names them as improvement
candidates in the report, leaving rules/meta-governance.md's 3+ project bar and /promote's
monopoly on landing intact. /tools learn repointed at the same rule.

Chosen over the audit's P6 (a closing improvement step in all 18 skills), which would add an
instruction block to every invocation — the cost this refactor exists to remove.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff feat/checkpoint-improvement-candidates -m "Merge feat/checkpoint-improvement-candidates"
```

- [ ] **Step 9: Write the close-out**

Append a dated entry to `docs/SESSION_REPORT.md` recording: the before/after numbers from Step 5,
the D1 decision and what was done about it, which audit items were deliberately not implemented
(P2, P4, P6-as-specified, P7) and why, and what remains open from the audit — §4's Med/Low
defects in `review`, `revise`, `tools`, `ztp-setup`, `ztp-data-tag`, `lit-position`, `pipeline`,
`promote` and `state/`, plus the P5 subagent routing and the P7 eval suite.

Then repoint this repo's `CLAUDE.md` **Start here** section at that entry if this work supersedes
`docs/2026-09-10_final-cleanup-handoff.md` as the current state of play.

- [ ] **Step 10: Mark the plan complete in the Progress Log**

**Done.**

---

## What this plan deliberately leaves open

Recorded so the next audit does not re-raise them as new findings:

- **§4 Med/Low defects** in `review` (`--theory` has no mode section; `--variance` undocumented),
  `revise` (missing `Bash` in `allowed-tools`, never calls `post writer`, REWRITE class exists
  only in the skill), `tools` (`render` hardcodes a filename; `validate-bib`, `journal`, `context`
  have no steps), `ztp-data-tag` (tagged-but-unnoted items), `lit-position` (local-first order
  cited but not enforced), `pipeline` (possible double-strike — **unverified**, confirm before
  fixing), `promote`, and `state/`.
- **P5 subagent routing** — `ztp-data-tag`'s per-paper MCP loop, `lit-position`'s search,
  `checkpoint`'s Obsidian calls and `submit target`'s 547-line reference read all run in the main
  context. Real context wins, but each needs its own agent definition and testing.
- **`allowed-tools` accuracy** — `revise`, `strategize`, `discover` and `lit-position` run
  `pipeline.py` without pre-approved `Bash`; no ZotPilot-using skill pre-approves
  `mcp__zotpilot__*`. Per the docs this costs permission prompts, not failures.
- **P7 functionality evals** — needs a mock ZotPilot MCP server or a fixture Zotero/ChromaDB.
  Audit §6 has a proposed test input and assertion set for all 25 skills. Run them one at a time:
  two parallel adoptions once exhausted a 5-hour usage window in about 15 minutes.
- **Vendored trees** (`zotpilot-skills/`, `ai-audit/`) are never edited in place. `ztp-tutor`
  (431 lines) and `humanize` (205) are the two worst P1 offenders in the whole tree; both need an
  upstream PR to `EconGeo/ZotPilot` and `EconGeo/ai-audit` respectively, then a re-sync.
