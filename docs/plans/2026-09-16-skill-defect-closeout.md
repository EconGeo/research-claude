> **STALLED 2026-09-16, AUDITED 2026-09-23 — read before resuming.**
> `tested:` nothing ran past Task 0: zero commits between `3ad638e` and 2026-09-23, every
> promised test file absent, eight of nine baselined skills byte-identical. 0 of 7 defect tasks.
> The status table is accurate — this is unstarted work, correctly recorded as unstarted.
>
> **Resumable at Task 1**, but apply the §6.4 amendments first. One is blocking: every task's
> verification block chains `python3 scripts/check_paths.py` with **no `--root`**, which exits on
> an argparse usage error and kills the `&&` chain before `run_fixture.sh`, `check_refs` and
> `check_install --all` ever run.
>
> Sequencing and full context: `docs/2026-09-23_pipeline-closeout-handoff.md`.
> Audit: `docs/audits/2026-09-23_closeout-delivery-audit.md`.

# Skill Defect Close-Out (Phase 2) — Implementation Plan

**Goal:** Close the Medium- and Low-severity defects that
`docs/audits/2026-09-15_skill-best-practices-audit.md` §4 recorded and the token-optimization
plan deliberately left open — without changing any pipeline behaviour that a ruling declares
deliberate.

**Predecessor:** `docs/plans/2026-09-16-skill-token-optimization.md` (Tasks 0–8, all done,
closed out in `66ca1cb`). That plan's **Global constraints** and the budget/step-binding
ratchets it installed in `tests/test_skill_contracts.py` are inherited here in full. This is the
follow-on it named under *"What this plan deliberately leaves open"*, restricted to the §4
Med/Low cluster. The other three clusters it names — **P5 subagent routing**, the **vendored P1
offenders** (`ztp-tutor`, `humanize`), and the **P7 eval suite** — are *not* in this plan.

**Source audit:** `docs/audits/2026-09-15_skill-best-practices-audit.md` §4. The correction block
at the top of that file is binding: the ztp version-skew findings are **withdrawn** and must not
be acted on, and neither must the ZotPilot MCP server's own "skills or configuration paths are
outdated" notice.

**Every §4 row in scope was re-verified by reading the files in full on 2026-09-16, before this
plan was written.** Each task states what was read and what it established. Where the audit said
"Auditor" (reported but not re-checked), this plan says **verified** or **unverified** explicitly.
Two rows in §4 are already closed and are listed under *Already done* below — do not re-open them.

---

## Global constraints

Every task inherits these. Re-read this section at the start of every task.

1. **Edits under `skills/`, `agents/`, `rules/` and `hooks/` are live in every linked paper the
   moment you save.** Branch before the first edit of every task. Never work on `main`.
2. **`./scripts/check_fork.sh` must exit 0** before any commit that touches the shipped tree.
3. **Never remove a `record-score` or `pipeline.py log` call site** (R-104–R-107, R-113). This
   plan *adds* one (`/review --theory`) and *moves* strike ownership; it removes neither.
4. **Never replace a numeric critic gate with a user choice** (R-42, R-44, R-132).
5. **Every mode must still reach its own critic dispatch** (R-101).
6. **Three things that look like gaps are deliberate — do not "fix" them** (R-106):
   `/review --replicate` records no score; `/talk` scores are advisory (`component: none,
   quality_weight: 0`); and `/strategize pap` records with `--scope section:pre-analysis-plan`,
   so `pipeline.py next` reporting `strategy` unscored for a PAP-only project is expected
   (D1, 2026-09-16 — see `skills/strategize/gotchas.md`).
7. **Three strings are pinned by `tests/test_review_contracts.py`** and must survive in
   `skills/review/SKILL.md`: the `## Verifier Pass/Fail Definition` heading, the literal
   `.claude/agents/verifier.md` inside that section, and the literal `git status --porcelain`
   anywhere in the file. That section must **not** contain `prose_number_check`,
   `references.bib`, `quarto render`, or `absolute paths`. Task 1 edits this file — run that
   test specifically, not just the suite.
8. **`tests/test_skill_contracts.py` carries two ratchets installed by the predecessor plan.**
   `BUDGET` caps the SKILL.md body of `review` (11,000), `strategize` (8,000), `write` (7,500),
   `discover` (6,000) and `checkpoint` (5,500) — **ratchet downward only**, and `review` has
   only **122 chars of headroom** today (10,878). `KNOWN_UNBOUND` lists five bundled files not
   yet bound to a step; **entries come out, nothing goes in.** Tasks 2 and 4 remove three of
   them. Any new reference file this plan creates must be named inside the step that uses it.
9. **`scripts/check_paths.py` resolves every `.claude/`-prefixed pipeline path in the shipped
   tree.** Write cross-references as `.claude/<dir>/<file>`, never bare — a bare path fails the
   gate. This caught three writers in the predecessor plan.
10. **Nothing project-specific may ship.** No journal name, dataset name or project noun in
    `agents/`, `skills/`, `rules/`, `hooks/`, `templates/`.
11. **Read before asserting.** Before deleting a block as "a duplicate of file X", read file X to
    end-of-file. Before calling a defect confirmed, read the file the audit cites, in full.

### Already done — do not re-open

- **§4 `checkpoint`** (plan staleness sweep, handoff reference dry-run, `ai_use_log.md`
  confirmation) — added as report lines in the predecessor's Task 7 (`52a3267`).
- **§4 `tools` / `learn`** — `/tools learn` was repointed at `.claude/rules/meta-governance.md`
  in the predecessor's Task 8 (`35f82d5`). Its other four subcommands are still in scope (Task 4).
- **§4 `ztp-setup` / PyPI** — fixed upstream in the fork (`b13bf83`/`f34da2a`, vendored at
  `f92e5b0`). The `~/.config/zotpilot/config.json` secrets half is vendored and stays upstream;
  the `new-project-ztp` half is in scope (Task 0 lands the edit already in the working tree).

---

## How to execute this plan across cleared contexts

Each task is one session. At the end of every task you commit, merge, update the Progress Log,
and **clear the context window**. The next session starts cold and reads only what its task's
**Cold start** block names.

**Every session begins with exactly this:**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short && git branch --show-current
```

Then read, in order:
1. This plan's **Global constraints** (above).
2. This plan's **Progress Log** (below) — the authoritative record of what is actually done.
3. The **Cold start** block of the task you are picking up.

Do not read the other tasks. They are self-contained on purpose.

**Every session ends with:** verification green → commit → merge → update the Progress Log →
report what changed → stop.

---

## Progress Log

The executor appends one row per completed task. The checkboxes inside a task are working
notes; this table is the handoff.

| Task | Status | Branch | Merged | Notes |
|---|---|---|---|---|
| 0 — Land the pending `new-project-ztp` edit; baseline | done | `fix/new-project-ztp-registration` | yes (`b0a95af`) | The draft that had sat uncommitted (and live in all six papers) asserted two mechanisms. **Both were checked against the installed build, not the vendored text.** `zotpilot status` reports `Client integration — Registered: claude-code, opencode`, so the client-level half is right; and `Secrets file: ~/.secrets.env` with `Write ops ready: yes`, while `~/.config/zotpilot/config.json` holds only non-secret settings plus `zotero_user_id` — so the secrets half is right too, and **the vendored `ztp-setup` step 5 ("API keys are stored in `~/.config/zotpilot/config.json`") is stale, as is the audit's "still open" finding on it.** Two draft claims were wrong and were dropped before landing: a `claude mcp add --scope user` invocation (`zotpilot setup` does the registration itself — vendored step 7) and a reference to Codex, which is not a detected client. Suite **159 passed, 3 subtests**; `check_fork` PASS. Baseline: review 10,878 / revise 4,109 / tools 4,347 (note, 2026-09-24: grown to 7,321 chars since, for reasons unrelated to this plan — this session's connectivity-check work touches `check_refs.py`/`check_fork.sh`, not `skills/tools/SKILL.md`; Task 7's re-baseline step should not read this drift as a regression from this plan's own work) / promote 3,176 / lit-position 6,093 / ztp-data-tag 9,173 / pipeline 4,183 / write 7,482 / new-project-ztp 3,966; all 18 = 98,894. |
| 1 — `review`: `--theory`, `--variance`, `--peer` score, `--stress` | not started | | | |
| 2 — `revise`: `allowed-tools`, `post writer`, REWRITE, the letter | not started | | | |
| 3 — `pipeline`: single owner for `state strike` | not started | | | |
| 4 — `tools`: `render`, `lint`, and the three stepless subcommands | not started | | | |
| 5 — ZotPilot side: `ztp-data-tag` atomicity, `lit-position` local-first | not started | | | |
| 6 — Low sweep: `promote`, `state/`, `new-project-ztp`, `/write humanize` | not started | | | |
| 7 — Close out | not started | | | |

**Open decisions** (record the answer here when the user gives it):

| # | Decision | Raised by | Answer |
|---|---|---|---|
| D2 | `/write humanize` rewrites in place; `/humanize` is detect-only **by design** and cites a cross-vendor finding that auto-rewriting degrades prose. Two near-identically named skills do opposite things. (a) Rename the mode to `/write cleanup` and have it name `/humanize` as the detect-only audit — touches `skills/write/SKILL.md`, any `pipeline/references/*.md` that names the mode, and `tests/`; (b) keep both names and state the distinction in both files, with `/write humanize` documented as "apply the 24 cleanup patterns to prose you drafted", not "de-AI a finished paper". **Recommend (a)** — the collision is the defect; a note does not remove it. | Task 6 | |
| D3 | `/review --peer` records `referees` (weight **25**) with `--critic editor`, but `agents/editor.md`'s `editorial_decision.md` format has **no overall score field** — only per-referee scores and a verdict — and `skills/review/config/scoring-rubrics.md` has **no Editor section at all**. (a) Add an Editor rubric and an explicit overall-score line to the decision format, sourced from the two referee scores and the verdict tier; (b) map the verdict tier to a fixed score (Accept 95 / Minor 85 / Major 70 / Reject 40); (c) leave `referees` unscored. **Recommend (a)** — (b) hides judgment behind a lookup table and (c) strands 25 weight points that R-104–R-107 were written to reconnect. | Task 1 | |

---

## Task 0: Land the pending `new-project-ztp` edit, and baseline

**Cold start:** read `skills/new-project-ztp/SKILL.md` to end-of-file and `git diff` it. Read
`README.md` Step 7 and Step 8 (the ZotPilot install and index sections).

**Why this is first.** The working tree has carried `M skills/new-project-ztp/SKILL.md` since
before the predecessor plan started. It is **live in all six linked papers** and committed
nowhere. It is also a real fix to half of §4's `ztp-setup` row: it replaces the false claim that
`/ztp-setup` registers the MCP server in a project `.mcp.json` with client-level registration,
and points API keys at `~/.secrets.env` instead of `config.json`. Land it before anything else
so no later task's diff is contaminated by it.

- [ ] **Step 1: Branch and read the diff**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/new-project-ztp-registration && git diff skills/new-project-ztp/SKILL.md
```

- [ ] **Step 2: Verify the claim the edit makes, do not assume it**

The edit asserts `/ztp-setup` registers at client scope and writes no project `.mcp.json`. Check
it against the vendored skill:

```bash
cd /Users/andrew.mueller/Academic/research-claude && cat zotpilot-skills/ztp-setup/SKILL.md
```

If the vendored skill contradicts the edit, the edit is wrong and the vendored skill wins — it
is the thing that actually runs. Report and stop rather than shipping a confident falsehood.

- [ ] **Step 3: Gate and commit**

```bash
cd /Users/andrew.mueller/Academic/research-claude && ./scripts/check_fork.sh && python3 -m pytest tests/ -q; echo "exit=$?"
```

Expected: `✓ check_fork: PASS` and **159 passed**. Then:

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/new-project-ztp/SKILL.md && git commit -m "$(cat <<'EOF'
fix(new-project-ztp): ZotPilot registers at client scope, not in a project .mcp.json

Step 2 promised micromamba + fork + a project `.mcp.json`. /ztp-setup registers at client
level once per machine, so the project file it described was never written and the closing
note told users to add a global entry that already existed. Keys point at ~/.secrets.env,
per the global single-source-of-truth rule, not config.json.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/new-project-ztp-registration -m "Merge fix/new-project-ztp-registration"
```

- [ ] **Step 4: Record the baseline**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 - <<'PY'
import re, glob
for f in sorted(glob.glob('skills/*/SKILL.md')):
    body = re.sub(r'^---\n.*?\n---\n', '', open(f).read(), count=1, flags=re.S)
    print(f"{f.split('/')[1]:18} {len(body):7} chars")
PY
```

Paste the rows for `review`, `revise`, `tools`, `promote`, `lit-position`, `ztp-data-tag`,
`pipeline`, `write` and `new-project-ztp` into the Progress Log. Task 7 re-runs this.

- [ ] **Step 5: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 1: `review` — `--theory`, `--variance`, the `--peer` score, and `--stress`

**Cold start:** read these to end-of-file before editing anything.

- `skills/review/SKILL.md`
- `agents/editor.md` (all 369 lines — the variance and stress modes are near the end)
- `skills/pipeline/references/adopt.md` and `skills/pipeline/references/theory.md`
- `skills/review/config/scoring-rubrics.md`
- `skills/review/templates/theory-review-4-phases.md`
- `skills/review/gotchas.md`
- `tests/test_review_contracts.py` and `tests/test_skill_contracts.py`

**What is wrong** (each verified by reading the files above in full, 2026-09-16):

1. **`--theory` has a routing line and no mode section.** `skills/review/SKILL.md` lists
   `--theory [target] → Proof audit (theorist-critic standalone, 4-phase review)` under
   *Explicit flags*, but `## Mode Details` has sections for Comprehensive, `--peer`, `--r2`,
   `--stress`, `--code`, `--methods`, `--proofread` and `--replicate` — and **none for
   `--theory`**. There is no dispatch, no report path, and no `record-score`.
   `skills/pipeline/references/adopt.md` routes the `theory` component's critic-only adoption to
   `/review --theory` and says it records `theory`. `rules/registry.yaml:29-32` gives `theory`
   weight **20**, `scored_by: theorist-critic`, `conditional: true`. The creator route
   (`/strategize theory`) records it; the critic-only route cannot.
2. **`--variance` is undocumented in the skill that is supposed to enforce it.**
   `agents/editor.md:117-137` defines `--variance N` (N ∈ {3,4,5}): draw N dispositions **with
   replacement**, a SKEPTIC stratification override, an N-row selection table, and a Phase 3
   replacement that writes `decision_distribution.md` + `editor_synthesis.md` **instead of**
   `editorial_decision.md` (`agents/editor.md:212-214`). Line 124 says *"The `/review --peer`
   skill enforces this — if you receive a Phase 1b call with both flags set, halt and report the
   conflict"*, referring to the rule that `--variance` cannot combine with `--stress`, `--r2` or
   `--r3`. `skills/review/SKILL.md` never mentions `--variance` — not in `argument-hint`, not in
   routing, not in any mode section. The enforcement the agent delegates does not exist.
3. **`--stress` points at a file its own mode never writes.** The skill says `--stress` is the
   "Same three-phase flow as `--peer`", and `--peer`'s Phase 3 carries
   `record-score referees <score> --critic editor --report …/editorial_decision.md`.
   `agents/editor.md` Stress mode says: *"No editorial decision letter — output is a concern-list
   gauntlet."* The skill's own `## Scoring` table already says Stress Test is **Advisory,
   Reported, non-blocking**. So a `--stress` run either records a score from a file that was
   never written, or silently does not record — and nothing says which is correct.
4. **The `referees` score has no source.** See **D3** above: `agents/editor.md`'s
   `editorial_decision.md` format has a per-referee score line (`Referee A …: score X/100`) and
   a verdict, but **no overall score field**, and `skills/review/config/scoring-rubrics.md` has
   sections for Writer-, Coder-, Strategist-, Theorist-, Storyteller-, Explorer- and Lit-Critic
   and **none for the editor**. `referees` is weight 25.
5. **The `## Scoring` table omits two modes** that record: Theory (after fix 1) and Replication
   (recorded by the verifier inside Comprehensive).

**The budget problem, and how to pay for it.** `skills/review/SKILL.md`'s body is **10,878
chars against a cap of 11,000** (`tests/test_skill_contracts.py`, `BUDGET`). Fixes 1, 2 and 5
add text. Pay for them first:

- Move the `**Save each report the moment its critic returns**…` paragraph (**335 chars**) and
  the `**Check the tree around the verifier.**…` paragraph (**467 chars**) out of the
  Comprehensive Review section into `skills/review/gotchas.md`, and **bind `gotchas.md` at the
  Comprehensive step** with one line naming it. Both are incident lessons, not steps — exactly
  the content class the predecessor plan moved. **Keep the literal `git status --porcelain` in
  SKILL.md** (constraint 7 pins it): leave the imperative sentence *"Record `git status
  --porcelain` before dispatching the verifier and again when it returns; the rest of this
  incident is in `gotchas.md`."* in place and move only the rationale.
- That frees ~800 chars; with the existing 122 you have ~920 to spend.
- **If the correct text genuinely does not fit in 11,000**, raise `BUDGET["review"]` to 11,500
  and write a comment in the test saying which correctness fix bought the increase. Do not
  compress a dispatch instruction to hit a number — the cap exists to stop prose creeping back,
  not to block a missing mode section. Say in the Progress Log which route you took.

**Files:**
- Modify: `skills/review/SKILL.md`, `skills/review/gotchas.md`
- Modify: `agents/editor.md` and `skills/review/config/scoring-rubrics.md` (**only** under D3(a))
- Create: `skills/review/templates/variance-mode.md`
- Modify: `tests/test_skill_contracts.py` (only if the cap moves)
- Create: `tests/test_review_modes.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/review-modes
```

- [ ] **Step 2: Put D3 to the user before writing anything**

Show the three options from the **Open decisions** table verbatim, with the evidence: the
`editorial_decision.md` format block from `agents/editor.md`, the rubric file's section list,
and `rules/registry.yaml`'s `referees: weight: 25, scored_by: editor`. Wait for the answer and
record it in the Open decisions table. Everything else in this task proceeds regardless.

- [ ] **Step 3: Write the failing test**

Create `tests/test_review_modes.py`:

```python
"""Every flag /review advertises must have a mode section that dispatches and records.

A routing line with no mode section is worse than an undocumented flag: it tells the model
the mode exists, and the model then invents the dispatch. `--theory` was advertised in the
flag list and in pipeline/references/adopt.md as the critic-only route for a weight-20
component, and no section in the skill dispatched anything.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "review" / "SKILL.md").read_text()
EDITOR = (ROOT / "agents" / "editor.md").read_text()


class TestAdvertisedFlagsHaveModes(unittest.TestCase):
    def test_theory_has_a_mode_section(self):
        self.assertRegex(SKILL, r"(?m)^### .*`--theory`")

    def test_theory_dispatches_its_critic_and_records_the_component(self):
        """adopt.md routes the `theory` component here; registry weight is 20."""
        i = SKILL.index("`--theory`", SKILL.index("## Mode Details"))
        section = SKILL[i:SKILL.index("\n### ", i + 1)] if "\n### " in SKILL[i:] else SKILL[i:]
        self.assertIn("theorist-critic", section)
        self.assertIn("record-score theory", section)
        self.assertIn(".claude/skills/review/templates/theory-review-4-phases.md", section)

    def test_variance_is_documented_where_the_editor_says_it_is_enforced(self):
        """editor.md:124 delegates the flag-conflict halt to this skill."""
        self.assertIn("--variance", EDITOR)
        self.assertIn("--variance", SKILL)
        self.assertIn("--variance", re.search(r"argument-hint:.*", SKILL).group(0))

    def test_variance_conflict_rule_is_stated_in_the_skill(self):
        for other in ("--stress", "--r2"):
            self.assertIn(other, SKILL)
        self.assertRegex(SKILL, r"--variance[^\n]*cannot[^\n]*--stress|--stress[^\n]*--variance")

    def test_stress_does_not_record_a_score(self):
        """editor.md stress mode writes no editorial_decision.md to record from."""
        i = SKILL.index("`--stress`", SKILL.index("## Mode Details"))
        section = SKILL[i:SKILL.index("\n### ", i + 1)] if "\n### " in SKILL[i:] else SKILL[i:]
        self.assertNotIn("record-score referees", section)
        self.assertIn("records no score", section)

    def test_scoring_table_lists_every_recording_mode(self):
        table = SKILL[SKILL.index("## Scoring"):]
        for mode in ("Theory", "Replication"):
            self.assertIn(mode, table)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_review_modes.py -q
```

Expected: **6 failures**. If any passes already, read the file again before proceeding — a
premise of this task is wrong and the rest of it may be too.

- [ ] **Step 5: Free the budget**

Move the two incident paragraphs to `skills/review/gotchas.md` (append, keeping its bullet
style), leave the `git status --porcelain` imperative in SKILL.md, and add one line to the
Comprehensive step naming `gotchas.md`. Then:

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -c "
import re,pathlib
b=re.sub(r'^---\n.*?\n---\n','',pathlib.Path('skills/review/SKILL.md').read_text(),count=1,flags=re.S)
print(len(b),'chars — cap 11000')"
```

- [ ] **Step 6: Add the `--theory` mode section**

Place it between `### Causal Audit (--methods)` and `### Manuscript Polish (--proofread)`, so
the two standalone-critic audits sit together. It must:

- dispatch **theorist-critic** standalone against
  `.claude/skills/review/templates/theory-review-4-phases.md`;
- save to `quality_reports/reviews/theorist-critic_<date>.md`;
- record `python3 .claude/scripts/pipeline.py state record-score theory <score> --critic
  theorist-critic --deductions <total> --report quality_reports/reviews/theorist-critic_<date>.md`;
- say that the score is **conditional** — it counts only when a `# Theory` heading exists in the
  manuscript (`rules/registry.yaml`, `conditional: true`), and that the creator route is
  `/strategize theory`, this being the critic-only route `adopt.md` uses;
- name `.claude/skills/review/config/scoring-rubrics.md` (Theorist-Critic) for the deductions.

Keep it to the size of the `--methods` section. The four phases belong to the template, which
theorist-critic reads for itself — do not paste them.

- [ ] **Step 7: Add `--variance`, with the detail in a bound reference**

In `skills/review/SKILL.md`:
- add `--variance N` to `argument-hint`;
- add one routing line under *Explicit flags*;
- add a short `#### Variance Mode (--variance N)` subsection inside Full Peer Review that (a)
  **enforces the conflict rule** — `--variance` cannot combine with `--stress`, `--r2` or `--r3`;
  on both flags, halt and report, which is what `agents/editor.md:124` delegates here — (b)
  dispatches N referees writing `referee_1.md` … `referee_N.md` rather than the domain/methods
  pair, and (c) names `.claude/skills/review/templates/variance-mode.md` for the rest.

Create `skills/review/templates/variance-mode.md` holding the reporting detail: the two output
files (`decision_distribution.md`, `editor_synthesis.md`) **replacing** `editorial_decision.md`,
the stratification-override footnote, and the fact that **no `referees` score is recorded in
variance mode** — a distribution is not a point estimate, and collapsing it defeats the mode's
purpose (`agents/editor.md:212-214`, read in full). Do not restate the sampling procedure; the
editor owns it.

**The file must be named inside the step that uses it** — `KNOWN_UNBOUND` takes no new entries
(constraint 8).

- [ ] **Step 8: Fix `--stress`**

State in the `--stress` section that it **records no score** and produces no
`editorial_decision.md` — the output is the concern-list gauntlet — and that this is the same
deliberate class as `/review --replicate` (R-106). Make sure no `record-score referees` line is
reachable from the `--stress` path: the "same three-phase flow as `--peer`" wording must
explicitly except Phase 3's recording.

- [ ] **Step 9: Fix the `## Scoring` table and apply D3**

Add Theory (Yes, 80 commit — conditional) and Replication (Yes — 0/100 from the verifier) rows,
and change Stress Test's Gate cell to say it records nothing. Then apply the user's D3 answer.
Under **(a)**: add an `## Editor (Peer Review Synthesis)` section to
`skills/review/config/scoring-rubrics.md` and an explicit overall-score line to
`editorial_decision.md`'s format in `agents/editor.md`, so the number `record-score referees`
writes has a defined source. Under **(b)** or **(c)**, follow the user's wording and say in the
Progress Log what changed.

- [ ] **Step 10: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_review_modes.py tests/test_review_contracts.py tests/test_skill_contracts.py -q && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

Expected: all green. `test_review_contracts.py` must be **9/9** — the three pinned strings.
Then confirm you deleted no recording site:

```bash
cd /Users/andrew.mueller/Academic/research-claude && git diff main -- skills/ agents/ | grep -c "^-.*record-score"
```

Expected: **0**.

- [ ] **Step 11: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/review agents/editor.md tests/ && git commit -m "$(cat <<'EOF'
fix(review): give --theory a mode section, document --variance, stop --stress recording

--theory was advertised in the flag list and named by pipeline/references/adopt.md as the
critic-only route for a weight-20 component, with no mode section to dispatch anything.
--variance is fully specified in agents/editor.md, which delegates its flag-conflict halt to
"the /review --peer skill" — a skill that never mentioned the flag. --stress reused --peer's
Phase 3, which records from an editorial_decision.md that stress mode does not write.

Paid for in budget by moving two incident paragraphs to gotchas.md, bound at the
comprehensive step. The pinned verifier strings are untouched.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/review-modes -m "Merge fix/review-modes"
```

- [ ] **Step 12: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 2: `revise` — `allowed-tools`, `post writer`, the REWRITE class, and the letter

**Cold start:** read these to end-of-file before editing anything.

- `skills/revise/SKILL.md`
- `rules/revision.md`
- `skills/revise/templates/response-letter.qmd`
- `skills/revise/templates/response-tracker.md`
- `skills/revise/templates/diplomatic-disagreement.md`
- `skills/revise/gotchas.md`
- `rules/registry.yaml` (the `agents:` block — for `post writer`'s predicates)
- `tests/test_skill_contracts.py` (`KNOWN_UNBOUND`)

**What is wrong** (each verified by reading the files above in full, 2026-09-16):

1. **No `Bash` in `allowed-tools`.** The frontmatter is
   `allowed-tools: Read,Grep,Glob,Write,Edit,Agent`, and Step 5 runs
   `python3 .claude/scripts/pipeline.py state record-score …` twice. Per the Claude Code docs
   this costs permission prompts, not failures — but a skill that prompts mid-dispatch is a
   skill people learn to run with the gate off.
2. **`post writer` is never called.** `rules/revision.md`'s R&R flow is explicit:
   `Revised paper → writer-critic → pipeline.py post writer`. `skills/revise/SKILL.md` Step 5
   dispatches writer → writer-critic and records the score, then Step 6 goes straight to the
   letter. Nothing runs `post`. This is the one gate that catches a critic that never ran, a
   render that failed, or a failing prose-number check before the response letter is written.
3. **The REWRITE class exists only in the skill.** `skills/revise/SKILL.md` Step 3 routes five
   classes: NEW ANALYSIS, CLARIFICATION, **REWRITE**, DISAGREE, MINOR. `rules/revision.md`'s
   classification table has NEW ANALYSIS, CLARIFICATION, DISAGREE, MINOR and FATAL — no REWRITE.
   The rule also says *"Each pairing above is declared in `.claude/rules/registry.yaml`; this
   column names who to dispatch, not a second source of truth."* Decide which is right by
   reading both plus the registry, and make one of them the only copy. **Likely resolution:**
   REWRITE and CLARIFICATION route identically (Writer → writer-critic) and differ only in
   scope, so REWRITE is a useful distinction the rule lacks — add it to the rule rather than
   deleting it from the skill. Confirm before acting; do not assume.
4. **The response letter contradicts its own template.** Step 6 says *"Generate the response
   letter (Markdown)"* with *"Page/section references for each change"*, and Step 8 saves
   `quality_reports/referee_response_[journal]_[date].md`. The template is
   `skills/revise/templates/response-letter.qmd` and its usage note says: *"Every response names
   where the change landed: section, table, or figure, by cross-reference (`@sec-results`,
   `@tbl-main`), **never a hardcoded page number**. Page numbers move; anchors do not."*
   The template is right — it is the copy that ships to an editor and the one `quarto render`
   can turn into a PDF. Fix the skill.
5. **Two templates are unbound.** `response-tracker.md` and `diplomatic-disagreement.md` are in
   `KNOWN_UNBOUND`. They are named only in the `## Bundled Resources (Level 3)` catalogue table,
   which `tests/test_skill_contracts.py` strips before searching — by design, because a
   catalogue is not a binding. Bind them at Steps 4 and 7 and delete the catalogue table.

**Files:**
- Modify: `skills/revise/SKILL.md`, `rules/revision.md`
- Modify: `tests/test_skill_contracts.py` (remove two `KNOWN_UNBOUND` entries)
- Create: `tests/test_revise_contracts.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/revise-gate-and-letter
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_revise_contracts.py`:

```python
"""Contracts for /revise.

The response letter goes to a journal editor. The template forbids hardcoded page numbers
because they move between renders; the skill asked for them anyway, and the skill is what
the model reads first.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "revise" / "SKILL.md").read_text()
RULE = (ROOT / "rules" / "revision.md").read_text()
TEMPLATE = (ROOT / "skills" / "revise" / "templates" / "response-letter.qmd").read_text()


class TestRevise(unittest.TestCase):
    def test_bash_is_pre_approved_because_the_skill_runs_pipeline_py(self):
        front = SKILL.split("---")[1]
        self.assertIn("pipeline.py", SKILL)
        self.assertRegex(front, r"allowed-tools:.*\bBash\b")

    def test_post_writer_runs_before_the_response_letter(self):
        """rules/revision.md: Revised paper -> writer-critic -> pipeline.py post writer."""
        self.assertIn("post writer", SKILL)
        self.assertLess(SKILL.index("post writer"), SKILL.index("Response Letter"))

    def test_the_letter_uses_anchors_not_page_numbers(self):
        self.assertIn("never a hardcoded page number", TEMPLATE)
        self.assertNotRegex(SKILL, r"[Pp]age/section references")
        self.assertIn("@sec-", SKILL)

    def test_the_letter_is_a_qmd_matching_its_template(self):
        self.assertIn("response-letter.qmd", SKILL)
        self.assertNotRegex(SKILL, r"referee_response_\[journal\]_\[date\]\.md")

    def test_every_comment_class_in_the_skill_exists_in_the_rule(self):
        classes = set(re.findall(r"\*\*(NEW ANALYSIS|CLARIFICATION|REWRITE|DISAGREE|MINOR|FATAL)\*\*", SKILL))
        missing = sorted(c for c in classes if c not in RULE)
        self.assertEqual([], missing, "a routing class the shared rule does not declare")

    def test_the_two_templates_are_bound_to_steps(self):
        steps = re.sub(r"^## Bundled [Rr]esources.*?(?=^## |\Z)", "", SKILL, flags=re.M | re.S)
        for t in ("response-tracker.md", "diplomatic-disagreement.md"):
            self.assertIn(t, steps)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_revise_contracts.py -q
```

Expected: **6 failures**.

- [ ] **Step 4: Fix the frontmatter and add the gate**

Add `Bash` to `allowed-tools`. In Step 5, after the last critic dispatch and its `record-score`,
add:

```
Then `python3 .claude/scripts/pipeline.py post writer`. FAIL (critic-ran / render /
prose-check) → fix and re-dispatch; do not write the response letter against a manuscript
that has not passed `post`.
```

Do not remove or reorder either existing `record-score` line (constraint 3).

- [ ] **Step 5: Reconcile REWRITE**

Read `rules/revision.md` and `rules/registry.yaml` in full, decide which copy is right, and make
that copy the only one. If REWRITE survives, add it to the rule's classification table and its
flow diagram with the same routing the skill gives it. If it does not, delete it from the skill
and fold its cases into CLARIFICATION. Say in the Progress Log which way it went and why.

- [ ] **Step 6: Fix the letter**

Step 6 and Step 8 must agree with `response-letter.qmd`: the letter is written **from** that
template, is a `.qmd`, saves as `quality_reports/referee_response_[journal]_[date].qmd`, quotes
each referee comment verbatim, and names where each change landed **by cross-reference**
(`@sec-`, `@tbl-`, `@fig-`) — never a page number. Name the template in the step.

- [ ] **Step 7: Bind the other two templates, delete the catalogue**

Name `.claude/skills/revise/templates/response-tracker.md` inside Step 4 and
`.claude/skills/revise/templates/diplomatic-disagreement.md` inside Step 7, delete the
`## Bundled Resources (Level 3)` table, and bind `gotchas.md` at Step 1. Then remove both
entries from `KNOWN_UNBOUND` in `tests/test_skill_contracts.py`.

- [ ] **Step 8: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

- [ ] **Step 9: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/revise rules/revision.md tests/ && git commit -m "$(cat <<'EOF'
fix(revise): run post writer, write the letter the template specifies, pre-approve Bash

rules/revision.md puts `pipeline.py post writer` between the critic and the response letter;
the skill went straight to the letter, so a failed render or a critic that never ran reached
an editor-facing document. Step 6 asked for page references that the .qmd template forbids
because they move. Bash was missing from allowed-tools although Step 5 runs pipeline.py twice.

The response tracker and diplomatic-disagreement templates are now bound to the steps that
use them and leave KNOWN_UNBOUND.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/revise-gate-and-letter -m "Merge fix/revise-gate-and-letter"
```

- [ ] **Step 10: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 3: `pipeline` — one owner for `state strike`

**Cold start:** read these to end-of-file before editing anything.

- `skills/pipeline/SKILL.md`
- every file in `skills/pipeline/references/` (twelve files; read all of them — the task turns
  on which stages delegate to a skill and which do not)
- `scripts/pipeline.py` — the `strike` branch of `cmd state` and `limits` handling
- `rules/agents.md` (the escalation section)
- `rules/registry.yaml` (`limits`, `escalation_target`)
- `tests/test_pipeline.py`

**The audit's claim, and what reading established.** §4 records *"The loop and the stage skills
both appear to `record-score`/`strike`, so one failing round may count two strikes"* and marks
it **unverified**. Reading settles half of it and refines the other half:

- **`record-score` is not double-counted.** Each `skills/pipeline/references/<stage>.md` states
  that the stage skill records the score itself (e.g. `literature.md`: *"`/lit-position` (Step 7
  of its own SKILL.md) dispatches lit-critic itself and records the score itself"*). The
  reference files assign ownership explicitly. No change needed.
- **`strike` has no such convention, and the call sites are inconsistent.** A tree-wide search
  (then confirmed by reading each file) finds `state strike` in exactly these places:
  `skills/pipeline/SKILL.md:51` (the generic `run` loop, `state strike <creator>`),
  `skills/lit-position/SKILL.md:121` (`strike lit-position`),
  `skills/strategize/SKILL.md:45` and `:105` (`strike strategist`),
  `skills/analyze/SKILL.md:38` (`strike coder`),
  `skills/write/SKILL.md:66` and `:111` (`strike writer`).
  `skills/discover`, `skills/review`, `skills/submit` and `skills/talk` have **none**.
- **`strike` is an unconditional increment with no idempotency key.** `scripts/pipeline.py`:
  `n = stt["strikes"].get(cr, 0) + 1` — no round id, no dedupe. Two calls in one round are two
  strikes, and escalation fires at `n >= limits.rounds_per_pair` (3).

So a `/pipeline run` whose literature, strategy, analyze or write stage fails a round
double-counts and escalates after **two** real rounds; and if the driver's generic line were
simply deleted, the data, review, submit and talk stages would **never** strike. Fix both
directions at once — a blanket edit in either direction breaks the other half.

**The rule to install** (mirroring the `record-score` convention that already works): **the
stage skill owns `state strike` for its own creator.** The driver counts rounds and reads the
strike total; it does not add to it.

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/strike-ownership
```

- [ ] **Step 2: Confirm the premise yourself before changing anything**

```bash
cd /Users/andrew.mueller/Academic/research-claude && grep -rn "state strike" skills/ agents/ rules/ scripts/ && grep -n "Delegates to" skills/pipeline/references/*.md
```

Every stage whose reference says **Delegates to: `/<skill>`** must end up with the strike in that
skill. If a stage delegates to no skill (the driver dispatches an agent directly), the strike
stays in the driver for that stage and the plan's rule needs a stated exception — write it down
rather than forcing the rule.

- [ ] **Step 3: Write the failing test**

Create `tests/test_strike_ownership.py`:

```python
"""`state strike` must have exactly one owner per creator.

pipeline.py's strike is an unconditional increment with no round id, so two call sites firing
in one failing round count two strikes and escalate after two real rounds instead of three.
The mirror failure is worse and quieter: a stage whose skill has no strike line at all never
escalates, so a creator can loop indefinitely.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRIVER = (ROOT / "skills" / "pipeline" / "SKILL.md").read_text()
REFS = ROOT / "skills" / "pipeline" / "references"


def delegating_stages():
    """{stage: skill} for every reference file that delegates to a slash command."""
    out = {}
    for f in sorted(REFS.glob("*.md")):
        m = re.search(r"\*\*Delegates to:\*\*\s*`?/([a-z-]+)", f.read_text())
        if m:
            out[f.stem] = m.group(1)
    return out


class TestStrikeOwnership(unittest.TestCase):
    def test_the_driver_does_not_issue_a_generic_strike(self):
        """It cannot know whether the stage skill it just invoked already struck."""
        self.assertNotRegex(DRIVER, r"state strike <creator>")
        self.assertIn("strike", DRIVER)  # it still reports and escalates on the count

    def test_every_delegating_stage_skill_strikes_its_own_creator(self):
        missing = []
        for stage, skill in delegating_stages().items():
            p = ROOT / "skills" / skill / "SKILL.md"
            if not p.exists():
                continue
            if "state strike" not in p.read_text():
                missing.append(f"{stage} -> /{skill}")
        self.assertEqual([], missing, "stage skills that can never escalate")

    def test_the_ownership_rule_is_written_down_where_a_reader_will_meet_it(self):
        self.assertIn("state strike", (ROOT / "rules" / "agents.md").read_text())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_strike_ownership.py -q
```

Expected: at least the first two fail. **If `test_every_delegating_stage_skill_strikes_its_own_creator`
lists a stage whose creator is dispatched by the driver as an Agent rather than by a skill, that
stage is the exception from Step 2** — exclude it in the test with a comment naming why, rather
than adding a strike line to a skill that does not own the creator.

- [ ] **Step 5: Change the driver**

In `skills/pipeline/SKILL.md`'s `run` pseudocode, replace

```
  below 80: creator fixes → critic re-scores; `state strike <creator>`; at 3 → escalate to
            registry's ESCALATION_TARGET with a specific question
```

with wording that (a) says the stage skill records the strike — the driver reads the count from
`state show` and does not add to it — and (b) keeps the escalation behaviour: at
`limits.rounds_per_pair` the driver escalates to the registry's `ESCALATION_TARGET` with the
specific question from that stage's `references/<stage>.md` **Escalation** block. The escalation
half is load-bearing and must not be lost.

- [ ] **Step 6: Add the missing strike lines**

For each delegating stage skill with no `state strike`, add one line in the same shape the four
existing ones use, naming the correct creator from `rules/registry.yaml` (not the skill name —
`strike` takes the creator agent, which is why `lit-position` strikes `lit-position` and
`/write` strikes `writer`). Put it beside that mode's `record-score`, on the `below 80` branch,
with the strike-three escalation question already written in that stage's reference file.

- [ ] **Step 7: Write the rule down once**

Add one short paragraph to `rules/agents.md`'s escalation section: the stage skill owns
`state strike` for its creator; the driver reads the count; `pipeline.py state strike` is an
unconditional increment with no round key, so a second call in the same round is a second strike.

- [ ] **Step 8: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && ./tests/run_fixture.sh; echo "exit=$?"
```

`run_fixture.sh`'s mechanical tier simulates dispatch lines and is the closest thing to an
end-to-end check for the driver — run it, and report what it says even if it is unrelated.

- [ ] **Step 9: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/ rules/agents.md tests/ && git commit -m "$(cat <<'EOF'
fix(pipeline): give state strike a single owner per creator

pipeline.py's strike is an unconditional increment with no round key. The driver's run loop
and four stage skills both issued one, so a failing literature/strategy/analyze/write round
counted two strikes and escalated after two real rounds. The stages with no skill-level
strike line had the opposite failure and could never escalate at all.

The stage skill now owns the strike, mirroring the record-score convention each
references/<stage>.md already states; the driver reads the count and still escalates to the
registry's ESCALATION_TARGET with that stage's question.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/strike-ownership -m "Merge fix/strike-ownership"
```

- [ ] **Step 10: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 4: `tools` — `render`, `lint`, and the three stepless subcommands

**Cold start:** read these to end-of-file before editing anything.

- `skills/tools/SKILL.md`
- `skills/tools/gotchas.md`
- `hooks/lint-scripts.sh`
- `scripts/pipeline.py` — the `manuscript` command and `declared_manuscript()`
- `scripts/qmd_chunks.py` (referenced by the lint step)
- `tests/test_skill_contracts.py` (`KNOWN_UNBOUND`)

**What is wrong** (each verified by reading the files above in full, 2026-09-16):

1. **`render` hardcodes a filename.** It says `quarto render manuscript_<project>.qmd`. Every
   other skill resolves the manuscript with `python3 .claude/scripts/pipeline.py manuscript`,
   which reads the declared name and refuses when it is absent or ambiguous. The hardcoded form
   encodes a naming convention the pipeline deliberately stopped assuming.
2. **The lint default is wrong.** `skills/tools/SKILL.md` says *"**Default:** `/tools lint`
   (lints `scripts/acquire/` and `explorations/`)"*. `hooks/lint-scripts.sh:19` is
   `TARGET="${1:-scripts/acquire}"` — a single default target, `explorations/` not included.
   The script is the thing that runs; the skill is wrong.
3. **`validate-bib`, `journal` and `context` have no steps.** Each is two sentences of
   description with no command, no output path and no pass condition. `learn` was fixed in the
   predecessor plan and is deliberately a pointer to `.claude/rules/meta-governance.md` — leave
   it alone.
4. **`gotchas.md` is loaded "Always" and, per audit §3 P3, contradicts SKILL.md in three
   places.** Read both in full, find the three, and resolve each by moving the surviving gotcha
   into the subcommand it belongs to. Delete the `## Bundled Resources (Level 3)` catalogue.

**Out of scope here:** `/tools commit` has no confirmation gate before commit/PR/merge. That is
audit **P4** (HITL), not §4, and it needs the `--yes` contract the P4 work will define. Leave it,
and say so in the Progress Log so the next audit does not read the omission as an oversight.

**Files:**
- Modify: `skills/tools/SKILL.md`, `skills/tools/gotchas.md`
- Create: `tests/test_tools_contracts.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/tools-subcommands
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_tools_contracts.py`:

```python
"""Contracts for /tools.

A documented default that disagrees with the script is worse than no default: the user reads
`/tools lint` as covering explorations/ and it silently covers scripts/acquire only.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "tools" / "SKILL.md").read_text()
LINT = (ROOT / "hooks" / "lint-scripts.sh").read_text()


class TestTools(unittest.TestCase):
    def test_render_resolves_the_declared_manuscript(self):
        i = SKILL.index("### `/tools render")
        section = SKILL[i:SKILL.index("\n### ", i + 1)]
        self.assertIn("pipeline.py manuscript", section)
        self.assertNotIn("manuscript_<project>.qmd", section)

    def test_the_documented_lint_default_matches_the_script(self):
        default = re.search(r'TARGET="\$\{1:-([^}"]+)\}"', LINT).group(1)
        i = SKILL.index("### `/tools lint")
        section = SKILL[i:SKILL.index("\n### ", i + 1)]
        line = next(l for l in section.splitlines() if "**Default:**" in l)
        self.assertIn(default, line)
        self.assertNotIn("explorations/", line)

    def test_every_subcommand_has_a_command_or_an_explicit_pointer(self):
        """`learn` is deliberately a pointer at meta-governance; the rest need steps."""
        stepless = []
        for name in ("validate-bib", "journal", "context"):
            i = SKILL.index(f"### `/tools {name}")
            j = SKILL.index("\n### ", i + 1) if "\n### " in SKILL[i:] else len(SKILL)
            section = SKILL[i:j]
            if "```" not in section:
                stepless.append(name)
        self.assertEqual([], stepless)

    def test_no_bundled_resources_catalogue(self):
        self.assertNotIn("## Bundled Resources", SKILL)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_tools_contracts.py -q
```

Expected: **4 failures**.

- [ ] **Step 4: Fix `render`**

```bash
MS=$(python3 .claude/scripts/pipeline.py manuscript) && quarto render "$MS"
```

Keep the existing pass condition (exit 0, output newer than source, grep the log for
`ERROR`/`WARNING` and the output for `?@fig-`/`?@tbl-`) and the `prose_number_check.py` note.
Keep the talks form as it is — talks are not the declared manuscript.

- [ ] **Step 5: Fix the lint default**

Change the `**Default:**` line to name `scripts/acquire/` only, and add one line saying how to
lint `explorations/` (`/tools lint explorations/`). Do **not** change `hooks/lint-scripts.sh` to
match the doc — the hook is wired into the harness and a second default target changes what runs
on every invocation. If you think the hook's default is the wrong one, say so in the Progress Log
and leave it.

- [ ] **Step 6: Give the three subcommands steps**

Each gets a command block, an output, and a pass condition:

- **`validate-bib`** — resolve the manuscript with `pipeline.py manuscript`, collect `@key` and
  `[@key]` citations from it and from `talks/*.qmd`, diff against the project `.bib`, report
  missing / unused / duplicate. State the `references.bib` convention and that Zotero is the
  source of truth (`.claude/skills/lit-position/SKILL.md`), so an unused entry is not
  automatically a defect.
- **`journal`** — name the output path (`research_journal.md`), say it is regenerated from the
  state file and the dispatch log rather than written by hand
  (`skills/pipeline/SKILL.md`: *"the research journal is written from it"*), and that it never
  decides where the pipeline starts (`pipeline.py next` does).
- **`context`** — name what it reads and what it reports. `hooks/context-monitor.py` already
  computes this; point at it rather than describing a second method.

If reading shows a subcommand cannot be given a real step without inventing a mechanism, **delete
the subcommand** and its `argument-hint` entry instead of documenting a fiction. Say which you
did, and check `hooks/context-monitor.py`'s nudge text still names a real subcommand afterwards —
`scripts/check_refs.py`'s `skill-refs` criterion will catch it if not.

- [ ] **Step 7: Resolve the gotchas and delete the catalogue**

Find the three contradictions between `gotchas.md` and `SKILL.md`, resolve each in favour of the
copy the evidence supports, move the survivors into their subcommands, and delete the
`## Bundled Resources (Level 3)` table. Name `gotchas.md` at the first subcommand that needs it,
or delete the file if nothing survives.

- [ ] **Step 8: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && python3 scripts/check_refs.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

- [ ] **Step 9: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/tools tests/ && git commit -m "$(cat <<'EOF'
fix(tools): resolve the manuscript, correct the lint default, give three subcommands steps

render hardcoded manuscript_<project>.qmd instead of asking pipeline.py, which is the one
thing that knows the declared name and refuses an ambiguous one. The documented lint default
claimed explorations/ coverage that lint-scripts.sh does not provide. validate-bib, journal
and context were descriptions with no command, no output and no pass condition.

/tools commit's missing confirmation gate is audit P4 and is deliberately not addressed here.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/tools-subcommands -m "Merge fix/tools-subcommands"
```

- [ ] **Step 10: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 5: ZotPilot side — `ztp-data-tag` atomicity and `lit-position` local-first

**Cold start:** read these to end-of-file before editing anything.

- `skills/ztp-data-tag/SKILL.md`
- `skills/lit-position/SKILL.md`
- `rules/literature-search-order.md`
- `zotpilot-skills/ztp-research/SKILL.md` (**read-only — vendored, never edited**)
- `zotpilot-skills/VENDORED.md`
- `agents/lit-critic.md` (its `mcpServers:` line — the precedent that a subagent can hold
  ZotPilot)

**What is wrong** (each verified by reading the files above in full, 2026-09-16):

1. **`ztp-data-tag` can tag an item `data-tagged` with no Data note.** Step 5 writes tags first
   (including the `data-tagged` marker), then calls
   `create_note(idempotent=true, title="Data (auto-extracted)", …)`. The skill's own text says
   `idempotent=true` *"skips creation if the item already has a ZotPilot note"* — **any**
   ZotPilot note, not specifically a Data note. An item that already carries a note from
   `/ztp-tutor` or `/ztp-research` therefore gets the marker tag and no Data note, and Step 2
   skips it forever after ("Drop any item that already carries the `data-tagged` marker tag").
   The failure is silent and permanent.
2. **`lit-position` cites the local-first rule and never performs it.**
   `rules/literature-search-order.md` is unambiguous: *"Before any `WebSearch` / `WebFetch` for
   literature, search the local Zotero index first. Order: ZotPilot `search_topic` →
   `advanced_search` → `search_papers`, then web… Applies to `/lit-position`."*
   `skills/lit-position/SKILL.md` Step 1 quotes the rule, then its numbered procedure goes
   straight to *"Invoke `/ztp-research` for the topic. It handles external search → candidate
   selection → PDF ingest → tagging → indexing."* `zotpilot-skills/ztp-research/SKILL.md`
   Phase 1 step 2 is *"**External search**: `search_academic_databases`"*, and its step 2 note
   says the server annotates `local_duplicate` — that is **de-duplication against the local
   library, not local-first discovery**, and the skill explicitly says *"Do NOT run a separate
   `advanced_search` dedup call"*. No local search happens anywhere in the chain.
   **ztp-research is vendored and must not be edited** (`CLAUDE.md`, `zotpilot-skills/VENDORED.md`).
   The fix belongs in `lit-position`, which is the bridge skill that exists for exactly this.
3. **`lit-position` has no `Bash` in `allowed-tools`** although Step 7 runs
   `pipeline.py log lit-position` and `pipeline.py state record-score`. Same class as the
   `revise` defect in Task 2; fixed here because the file is open. (The broader `allowed-tools`
   sweep — `strategize`, `discover`, and `mcp__zotpilot__*` pre-approval everywhere — stays out
   of scope.)

**Files:**
- Modify: `skills/ztp-data-tag/SKILL.md`, `skills/lit-position/SKILL.md`
- Create: `tests/test_zotpilot_skills.py`
- **Never modify:** anything under `zotpilot-skills/`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/zotpilot-bridge-skills
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_zotpilot_skills.py`:

```python
"""Contracts for the two ZotPilot bridge skills.

The marker tag is the idempotency key for the whole library, so writing it for an item that
got no Data note removes that item from every future run. And a local-first rule that only
appears as a citation is not a rule — ztp-research goes straight to external search, so the
local sweep has to happen in the bridge or nowhere.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAG = (ROOT / "skills" / "ztp-data-tag" / "SKILL.md").read_text()
LIT = (ROOT / "skills" / "lit-position" / "SKILL.md").read_text()
VENDORED = (ROOT / "zotpilot-skills" / "ztp-research" / "SKILL.md").read_text()


class TestDataTagAtomicity(unittest.TestCase):
    def test_the_marker_tag_is_conditional_on_the_data_note(self):
        i = TAG.index("## Step 5")
        j = TAG.index("## Step 6")
        step5 = TAG[i:j]
        self.assertIn("get_notes", step5, "must check for an existing Data note first")
        self.assertRegex(step5, r"data-tagged[^\n]*only|only[^\n]*data-tagged")

    def test_the_skip_case_is_reported_not_silent(self):
        self.assertIn("no Data note", TAG)


class TestLitPositionLocalFirst(unittest.TestCase):
    def test_ztp_research_still_starts_externally(self):
        """If this ever fails, upstream changed and the bridge workaround can be revisited."""
        self.assertIn("**External search**", VENDORED)

    def test_the_bridge_runs_the_local_sweep_before_dispatching(self):
        i = LIT.index("## Step 1")
        j = LIT.index("## Step 2")
        step1 = LIT[i:j]
        for tool in ("search_topic", "advanced_search"):
            self.assertIn(tool, step1)
        self.assertLess(step1.index("search_topic"), step1.index("/ztp-research"))

    def test_bash_is_pre_approved_because_step_7_runs_pipeline_py(self):
        front = LIT.split("---")[1]
        self.assertIn("pipeline.py", LIT)
        self.assertRegex(front, r"allowed-tools:.*\bBash\b")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_zotpilot_skills.py -q
```

Expected: 5 failures, and `test_ztp_research_still_starts_externally` **passing** — it is a
tripwire on the vendored file, not a defect.

- [ ] **Step 4: Make the tag conditional on the note**

Rewrite `ztp-data-tag` Step 5 so the note is written **first** and the marker tag second:

1. `mcp__zotpilot__get_notes(item_key=…)` — does a "Data (auto-extracted)" note already exist?
2. If yes, this item is genuinely done: tag it and move on.
3. If no, call `create_note(idempotent=true, …)`. **If it returns without creating** — the item
   has some other ZotPilot note — do **not** write `data-tagged`. Record the item in the Step 6
   report under "skipped: has a non-Data ZotPilot note", so the user can decide.
4. Write the `dataset:`/`var:` tags and the `data-tagged` marker only for items that now have a
   Data note.

Update the `## Rules` bullet on idempotency and the `## Undo` section to match, and add the
counter to Step 6's summary. Do not weaken the `action="add"` / `allow_new=true` / never-`set`
rules — they are load-bearing and destructive to get wrong.

- [ ] **Step 5: Put the local sweep in `lit-position` Step 1**

Insert it **before** the `/ztp-research` invocation, as its own numbered sub-step, in the rule's
order: `mcp__zotpilot__search_topic` → `mcp__zotpilot__advanced_search` →
`mcp__zotpilot__search_papers`. Its output is the list of what the library already covers; that
list is what gets passed to `/ztp-research` as the gap set, alongside the Step 0 seed's
`## Notes for the Literature Review` gaps. State plainly, in one line, **why the sweep lives
here**: `/ztp-research` is vendored and starts at external search, and its `local_duplicate`
annotation is de-duplication, not local-first discovery. Without that line the next reader
deletes the sweep as redundant.

Add `Bash` to `allowed-tools`.

- [ ] **Step 6: Verify nothing vendored moved**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short zotpilot-skills/ ai-audit/ && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

Expected: **no output** from the first command, everything else green.

- [ ] **Step 7: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/ztp-data-tag skills/lit-position tests/ && git commit -m "$(cat <<'EOF'
fix(zotpilot): never mark an item data-tagged without a Data note; run the local sweep

create_note(idempotent=true) skips any item that already has a ZotPilot note — from
/ztp-tutor or /ztp-research, not just this skill — while the marker tag was written
unconditionally. The item was then skipped by every later run with no Data note and no
report. The note now comes first and the marker follows it.

/lit-position cited rules/literature-search-order.md and then handed straight to
/ztp-research, whose Phase 1 starts at search_academic_databases; its local_duplicate
annotation is de-duplication, not local-first discovery. The sweep lives in the bridge
because the vendored skill is never edited.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/zotpilot-bridge-skills -m "Merge fix/zotpilot-bridge-skills"
```

- [ ] **Step 8: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

> **Amendment, 2026-09-24 (before resuming this task):** D2 is moot. The vendored skill this
> defect names — `ai-audit`'s `/humanize` — was renamed to `/civilize` upstream
> (`docs/plans/2026-09-23_pipeline-repair.md` Phase 2.4, gate met 2026-09-24, commit `c737ac6`).
> There is no longer a second skill named `/humanize` for `/write humanize` to collide with.
> Skip Step 2 ("Put D2 to the user") and Step 8 ("Apply D2") below — do not rename `/write
> humanize`; there is nothing left to disambiguate it from. Re-verify with
> `grep -rn humanize skills/ agents/ ai-audit/ rules/` before skipping: it should show only
> `skills/write/SKILL.md`'s own humanize mode and `ai-audit/VENDORED.md`'s provenance note.

## Task 6: Low sweep — `promote`, `state/`, `new-project-ztp`, `/write humanize`

**Cold start:** read these to end-of-file before editing anything.

- `skills/promote/SKILL.md`
- `rules/shared-pipeline.md`
- `apply.sh` (the flag parsing and `write_lock()`)
- `state/obsidian-config.md.example`
- `scripts/check_refs.py` (`SHIP`, `TEXT_SUFFIX`, `shipped_files`)
- `skills/new-project-ztp/SKILL.md` (as landed in Task 0)
- `skills/write/SKILL.md` (the `humanize` mode section)
- `ai-audit/skills/humanize/SKILL.md` (**read-only — vendored**)
- `skills/write/templates/cleanup-patterns.md` and `agents/humanize-auditor.md`

**What is wrong** (each verified by reading the files above in full, 2026-09-16):

1. **`promote` Step 1's checkout test is always true.** It says *"Confirm it against
   `.claude/pipeline.lock` — if the lock names a commit but `$RC` is on `main`, this project is
   on the shared (`--tip`) checkout."* `apply.sh`'s `write_lock()` always writes `commit=$sha`,
   in **both** modes. The discriminator that actually exists is the last line it writes:
   `# installed via: tip (shared checkout)` or `# installed via: pinned`.
2. **`promote` Step 5 gives a command that fails, and a claim that is too broad.**
   It offers `apply.sh --link`; `apply.sh:93` is
   `[[ -n "$PROJECT_DIR" ]] || { echo "Error: --project-dir is required"; exit 1; }`.
   `rules/shared-pipeline.md` gives the re-link as `./bootstrap-pipeline.sh --tip`, run from the
   project. It also claims *"A promotion that **adds** a file matters beyond the lock: no other
   project has a link to it until each one re-links."* The predecessor plan established
   (verified in `NAR_settlement`, `docs/SESSION_REPORT.md`) that each skill is a **directory**
   symlink, so a file added inside an existing skill propagates immediately; only a **new
   top-level item** (a new skill, agent, rule or hook) needs a re-link. Narrow the claim to that.
3. **`state/obsidian-config.md.example` names a skill that was deleted on 2026-09-09.**
   `/obsidian-digest-sync` appears twice: the header comment and the
   "Knowledge-base folders (used by `/obsidian-digest-sync`)" line. `CLAUDE.md` records the
   skill's removal.
4. **`check_refs.py` cannot catch that, twice over.** `SHIP` (line 16) is
   `["agents", "skills", "rules", "references", "hooks", "templates", "seeds", "scripts"]` —
   no `state`. And `TEXT_SUFFIX` (line 18) has no `.example`, so even adding `state` to `SHIP`
   would skip this file, whose suffix is `.example`. Both are needed.
5. **`new-project-ztp` points at an anchor that ships nowhere.** Step 4 says *"If `## Tools`
   already exists, update in place. If not, append after `## Current Project State`."* A
   tree-wide search finds that string **only on that line**; `templates/` contains
   `handoff.md`, `journal-profile-template.md` and `pipeline-state.json` — there is **no CLAUDE.md
   template at all** — and `apply.sh` never creates or writes a project `CLAUDE.md`. Confirm
   against a real project (`grep -n '^## ' <a linked project>/CLAUDE.md`) before choosing the
   fix: either append at end-of-file, or name a heading that projects actually have.
6. **`new-project-ztp`'s index estimate contradicts the README.** Step 3 offers *"~15–20 min for
   300 papers (Gemini free tier)"*; `README.md:409` says *"200 papers ≈ 10–20 minutes either
   way"*, and the README recommends Ollama over Gemini throughout (`README.md:266`). Quote the
   README's figure and stop naming only the provider the README steers away from.
7. **`/write humanize` and `/humanize` do opposite things under near-identical names.**
   `skills/write/SKILL.md`'s mode is *"Cleanup Pass Only — Strip AI writing patterns from
   existing text"*, **Output: Edited file with AI patterns removed**.
   `ai-audit/skills/humanize/SKILL.md` is *"Read-only audit … **The skill does not rewrite.**"*
   and says under **What this skill is NOT**: *"Not a rewriter. No `--rewrite` mode.
   Auto-rewriting AI tells degrades prose quality (cross-vendor research finding)."*
   This is **D2** — put it to the user (see Open decisions) before touching either file. The
   vendored copy is read-only regardless of the answer.
   **Before presenting D2, read `skills/write/templates/cleanup-patterns.md` and
   `agents/humanize-auditor.md` in full** and say in the question how much the 24 cleanup
   patterns actually overlap the auditor's 10 categories — if they barely overlap, the two modes
   are less redundant than the names suggest, and that changes which option is right.

**Files:**
- Modify: `skills/promote/SKILL.md`, `state/obsidian-config.md.example`,
  `scripts/check_refs.py`, `skills/new-project-ztp/SKILL.md`, `skills/write/SKILL.md` (per D2)
- Possibly modify: `skills/write/SKILL.md`'s `BUDGET` entry — it is at 7,482 of 7,500, so a
  rename that lengthens the mode heading needs the offset found inside that file
- Create: `tests/test_low_severity_contracts.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git checkout -b fix/low-severity-sweep
```

- [ ] **Step 2: Put D2 to the user with the overlap evidence**

Read `cleanup-patterns.md` and `agents/humanize-auditor.md` in full, then present D2 with a
one-line count of how many of the 24 cleanup patterns appear in the auditor's categories. Record
the answer in the Open decisions table. The rest of the task proceeds regardless.

- [ ] **Step 3: Write the failing test**

Create `tests/test_low_severity_contracts.py`:

```python
"""Small contracts for the low-severity defects in audit section 4.

Each of these is a documented instruction that does not work: a command missing a required
flag, a test that is always true, an anchor that exists in no shipped file, a reference to a
deleted skill that the reference checker structurally cannot see.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMOTE = (ROOT / "skills" / "promote" / "SKILL.md").read_text()
APPLY = (ROOT / "apply.sh").read_text()
EXAMPLE = (ROOT / "state" / "obsidian-config.md.example").read_text()
REFS = (ROOT / "scripts" / "check_refs.py").read_text()
NPZ = (ROOT / "skills" / "new-project-ztp" / "SKILL.md").read_text()


class TestPromote(unittest.TestCase):
    def test_relink_command_carries_the_required_flag(self):
        self.assertIn("--project-dir is required", APPLY)
        for m in re.finditer(r"apply\.sh --link[^\n]*", PROMOTE):
            self.assertIn("--project-dir", m.group(0))

    def test_the_checkout_test_uses_the_discriminator_that_exists(self):
        """write_lock() writes commit= in BOTH modes; only the trailing comment differs."""
        self.assertIn("installed via", APPLY)
        self.assertIn("installed via", PROMOTE)


class TestStateDirIsScanned(unittest.TestCase):
    def test_deleted_skill_is_not_referenced(self):
        self.assertNotIn("obsidian-digest-sync", EXAMPLE)

    def test_check_refs_can_see_this_file_at_all(self):
        ship = re.search(r"SHIP = \[([^\]]*)\]", REFS).group(1)
        self.assertIn('"state"', ship)
        suffix = re.search(r"TEXT_SUFFIX = \{([^}]*)\}", REFS).group(1)
        self.assertIn('".example"', suffix)


class TestNewProjectZtp(unittest.TestCase):
    def test_no_anchor_that_ships_nowhere(self):
        self.assertNotIn("## Current Project State", NPZ)

    def test_index_estimate_matches_the_readme(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("200 papers", readme)
        self.assertIn("200 papers", NPZ)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run it and confirm it fails**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/test_low_severity_contracts.py -q
```

Expected: **6 failures**.

- [ ] **Step 5: Fix `promote`**

Step 1: read the lock's `# installed via:` line, not the presence of `commit=`. Step 5: give the
re-link as `./bootstrap-pipeline.sh --tip` from the project (matching `rules/shared-pipeline.md`)
or `apply.sh --project-dir <path> --link` from this checkout — and narrow the "no other project
has a link to it" claim to **new top-level items**, noting that a file added inside an existing
skill directory propagates on save because the link is to the directory.

- [ ] **Step 6: Fix `state/` and let the checker see it**

Remove the three `/obsidian-digest-sync` references from `state/obsidian-config.md.example`. The
knowledge-base folder table exists only for that skill — read the file in full and decide whether
the table has any other consumer before deleting it; if `/checkpoint` reads any of those paths
(`skills/checkpoint/references/obsidian.md`, added in the predecessor's Task 7), keep the table
and repoint it. Then add `"state"` to `SHIP` and `".example"` to `TEXT_SUFFIX` in
`scripts/check_refs.py`, and run the checker — **expect new findings in `state/` and fix them,
rather than reverting the widened scan.**

- [ ] **Step 7: Fix `new-project-ztp`**

Replace the `## Current Project State` anchor per Step 5 of *What is wrong* above, after checking
a real linked project's `CLAUDE.md` headings. Replace the index estimate with the README's
figure, naming both providers as the README does.

- [ ] **Step 8: Apply D2**

Follow the user's answer. Under **(a)**, rename the mode, update every reference to it
(`grep -rn "write humanize" skills/ rules/ agents/ tests/`), keep `write`'s body under its
7,500-char cap, and have the renamed mode name `/humanize` as the detect-only audit to run first.
Under **(b)**, state the distinction in `skills/write/SKILL.md` in one or two lines. Either way,
do not edit `ai-audit/`.

- [ ] **Step 9: Verify**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short zotpilot-skills/ ai-audit/ && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && python3 scripts/check_refs.py --root /Users/andrew.mueller/Academic/research-claude; echo "exit=$?"
```

- [ ] **Step 10: Commit and merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add skills/ state/ scripts/check_refs.py tests/ && git commit -m "$(cat <<'EOF'
fix: close the low-severity audit defects — promote, state/, new-project-ztp

promote's checkout test read `commit=`, which apply.sh writes in both modes, and offered
`apply.sh --link` without the --project-dir that apply.sh requires; its re-link warning is
narrowed to new top-level items, since a file added inside a linked skill directory
propagates on save. state/obsidian-config.md.example still named /obsidian-digest-sync,
deleted 2026-09-09 — check_refs could not see it because SHIP omits state/ and TEXT_SUFFIX
omits .example; both are widened. new-project-ztp pointed at a `## Current Project State`
anchor that ships in no file and quoted an index estimate the README contradicts.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)" && git checkout main && git merge --no-ff fix/low-severity-sweep -m "Merge fix/low-severity-sweep"
```

- [ ] **Step 11: Update the Progress Log and stop**

**STOP. Clear the context window.**

---

## Task 7: Close out

**Cold start:** this plan's **Progress Log** and **Open decisions**;
`docs/SESSION_REPORT.md` (the 2026-09-16 entry); `docs/2026-09-10_final-cleanup-handoff.md`
(its progress log); `CLAUDE.md` (the **Start here** section).

- [ ] **Step 1: Full verification from a clean tree**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --short && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && python3 scripts/check_paths.py --root /Users/andrew.mueller/Academic/research-claude && python3 scripts/check_refs.py --root /Users/andrew.mueller/Academic/research-claude && ./scripts/check_install.sh --all; echo "exit=$?"
```

`check_install --all` is **expected RED** — `clone-links` fails in BRI, NAR_settlement, POGM4,
zoning2026 (deliberate: each needs real copies of the three `references/*` files before a
coauthor clones it) and in ESG (its fix `9349a8e` is on `main` and is not an ancestor of the
checked-out `pipeline-adoption` branch). Confirm the failure set is **exactly** that and no
larger. A new name in that list is this plan's doing.

- [ ] **Step 2: Measure**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 - <<'PY'
import re, glob
PIPE = ["pipeline", "lit-position", "discover", "strategize", "analyze", "write", "review", "submit"]
tot = pipe = 0
for f in sorted(glob.glob('skills/*/SKILL.md')):
    name = f.split('/')[1]
    body = re.sub(r'^---\n.*?\n---\n', '', open(f).read(), count=1, flags=re.S)
    tot += len(body); pipe += len(body) if name in PIPE else 0
    print(f"{name:18} {len(body):7} chars")
print(f"\n{'ALL 18':18} {tot:7}   (after phase 1: 98,672)")
print(f"{'PIPELINE RUN':18} {pipe:7}   (after phase 1: 50,819)")
PY
```

A modest increase is the expected outcome — this plan adds correctness text. Report it plainly
rather than framing it as a regression, and say which budgets moved and why.

- [ ] **Step 3: Write the close-out**

Append a dated entry to `docs/SESSION_REPORT.md` recording, per task: what was verified, what
was fixed, the D2 and D3 answers and what was done about them, every contradiction resolved and
**which copy won and why**, anything found in passing, and what remains open. Carry forward
explicitly:

- **Still open from the audit**, unchanged by this plan: P4 option points (including
  `/tools commit`'s missing confirmation gate), **P5 subagent routing**, the full
  `allowed-tools` sweep (`strategize`, `discover`, and `mcp__zotpilot__*` pre-approval
  everywhere), **P7 evals**, and the **vendored P1 offenders** `ztp-tutor` (431 lines) and
  `humanize` (205), which need upstream PRs to `EconGeo/ZotPilot` and `EconGeo/ai-audit`.
- **Still open from the predecessor's close-out, and from the 2026-09-10 handoff** (whose §2
  status markers were corrected on 2026-09-16 — see its progress log): R-136, the seed/hook
  propagation gap where a new hook in `seeds/settings.json` reaches no existing project; a full
  green `--live` run; `clone-links` failing in BRI, NAR_settlement, POGM4, zoning2026 and
  ESG-on-`pipeline-adoption`; the six `pipeline.lock` files, now 40+ commits behind; POGM4's
  leftover `manuscript_quarto_word.html`. None of it is skill text, which is why this plan does
  not touch it.
- **Found in passing while writing this plan, not fixed:** this repo's own `CLAUDE.md` says
  *"`templates/` holds files `apply.sh` installs directly into a project (e.g.
  `data_manifest.md` → `data/raw/`, `gitignore` → `.gitignore`)"*. Neither file is in
  `templates/` — it holds `handoff.md`, `journal-profile-template.md` and
  `pipeline-state.json`. Verify and correct or delete that sentence.

- [ ] **Step 4: Repoint the pointer, or explain why not**

`CLAUDE.md`'s **Start here** points at `docs/2026-09-10_final-cleanup-handoff.md`. The
predecessor deliberately did **not** repoint it, on the grounds that the handoff's
§2a/§2b/§2c/§4 were still open — **and that was checked and corrected on 2026-09-16 before this
plan began** (`docs/2026-09-10_final-cleanup-handoff.md`, the 2026-09-16 progress-log entry):
§2a is done, §2b is a revisit-when condition, §2c is three recorded decisions, and §4's
submodule half is obsolete. What is genuinely open there is infrastructure, not skill text:
R-136's seed/hook propagation gap, a full green `--live` run, `clone-links` in five repos, the
six stale `pipeline.lock` files, and POGM4's leftover `.html`.

So the question at this step is narrow: **does that remaining list still belong to the handoff?**
If it does, cross-link this plan's close-out from the handoff and leave the pointer alone. If it
has shrunk to nothing, repoint **Start here** and say so. Do not add a second pointer — the
single-pointer rule is the point.

- [ ] **Step 5: Commit**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add docs/ CLAUDE.md && git commit -m "$(cat <<'EOF'
docs: close out the skill defect close-out plan

Per-task record of what was verified, what was fixed, which copy won each contradiction, the
D2/D3 answers, and what the audit still leaves open.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Mark the plan complete in the Progress Log**

**Done.**

---

## What this plan deliberately leaves open

Recorded so the next audit does not re-raise them as new findings:

- **P4 option points** (audit §3 P4), including `/tools commit`'s missing confirmation gate
  before commit/PR/merge. Each new wait must honour `--yes` or `/pipeline` and the live fixture
  tier stall, so they are one coherent piece of work, not a scatter of small fixes.
- **P5 subagent routing** — `ztp-data-tag`'s per-paper MCP loop, `lit-position`'s search (Task 5
  adds a local sweep to the main context, which makes the case for routing *stronger*, not
  weaker), `checkpoint`'s Obsidian calls, and `submit target`'s 547-line reference read.
- **The full `allowed-tools` sweep.** Task 2 and Task 5 add `Bash` to `revise` and
  `lit-position` because those files were open. `strategize` and `discover` still run
  `pipeline.py` without it, and no ZotPilot-using skill pre-approves `mcp__zotpilot__*`.
- **P7 functionality evals** — needs a mock ZotPilot MCP server or a fixture Zotero/ChromaDB.
  Audit §6 has a proposed input and assertion set for all 25 skills. Run them one at a time.
- **`seed-papers` (vendored, audit §4 Low)** — Step 1 reads a "Research Question" field that
  `references/domain-profile.md` does not have, so it always falls through to asking, and its
  dedupe line mixes `doc_id` with `ZOTERO_KEY`. Not verified here; it is vendored, so it goes
  upstream with the other `ztp-*` work.
- **Vendored trees** (`zotpilot-skills/`, `ai-audit/`) are never edited in place. `ztp-tutor`
  (431 lines) and `humanize` (205) are the two worst P1 offenders in the tree; both need an
  upstream PR then a re-sync. `ztp-setup`'s storage of API keys in
  `~/.config/zotpilot/config.json` — against the global `~/.secrets.env` single-source rule —
  is in the same category.
- **`skills/submit/templates/audit-10-checks.md`** stays in `KNOWN_UNBOUND`. Audit §3 P3 says it
  is an orphan drifted from `agents/verifier.md` (check 3, the INV list) and should be deleted
  or reduced to a pointer. That is a P3 refactor of `submit`, which this plan does not open.
