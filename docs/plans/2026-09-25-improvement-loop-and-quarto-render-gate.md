# Improvement Loop (P6) and Quarto Render Gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** not started.

**Goal:** Close the P6 self-improvement residue with two mechanisms — a correction rule that
lands a user-confirmed fix at once, and a cross-project ledger that surfaces the same
correction made twice — then use the ledger's first repeated entry (Quarto silent-failure
corrections, made in two projects) to land the fix those corrections never reached the shared
tree with: a bound authoring reference and an executable post-render check.

**Architecture:** One rule (`rules/meta-governance.md`, amended, not a new file) says what
happens at the moment a user corrects a shared skill, agent or rule: ask once, land on yes via
`/promote`, otherwise record. One script (`scripts/ledger.py`) owns an append-only ledger in
this repo (`docs/improvement-ledger.md`), written by `/checkpoint` for every improvement
candidate and read by `/promote`, which flags any target named by two or more distinct
projects. The 3+ project bar stays, for log-inferred learnings only. The Quarto half moves
the cross-domain authoring reference into `references/` (linked into every project by
`apply.sh`, the global path becomes a symlink so `~/Courses/` keeps reading it), binds it
into the agents that write `.qmd`, and adds `scripts/check_render.py` — a `pdftotext`-based
check of the rendered output — as write-gate item 4, because every Quarto failure this
pipeline keeps making is silent at render time.

**Tech Stack:** Python 3.9 stdlib, `unittest` via `python3 -m pytest tests/ -q`, Bash,
`pdftotext` (poppler, present at `/opt/homebrew/bin/pdftotext`).

**Spec:** the decision recorded in this plan's Rationale section (2026-09-25 session), against
`docs/audits/2026-09-15_skill-best-practices-audit.md` §3 P6 and §7 decision 2, and
`docs/plans/2026-09-24-option-gates-subagent-routing-evals.md` "What this plan deliberately
leaves open". Evidence for the Quarto rows: the NAR project's memory file
`feedback-quarto-authoring.md` (author corrections 2026-09-04 and 2026-09-21) and zoning2026's
`latex_table_compile_bugs.md` (2026-06-08).

## Rationale (the decision this plan implements)

1. **The 3+ bar never applied to user corrections.** `rules/meta-governance.md` (read in
   full) has two parts. "The one rule" asks whether every project would be better off, and the
   user answers it. The "Learning promotion" table, where the 3+ bar lives, has three rows
   (PATTERN, FRICTION, HIGH-PERF), all inferred by `/pipeline` from the dispatch log and state
   file. A user correction is decided evidence, not a statistical pattern. The 09-16 Task 8
   wiring (`skills/checkpoint/SKILL.md` 4a, `/tools learn`) carried the bar onto corrections
   anyway, and nothing counts projects, so a correction becomes a report line in one
   project's SESSION_REPORT and dies there.
2. **Corrections get two paths.** At the moment of correction: ask once, land on yes. Declined
   or unnoticed: a ledger row. `/promote` flags a target named by **2** distinct projects.
   Log-inferred learnings keep 3+ (unchanged, and still unenforced — recorded, not fixed here).
3. **No per-skill closing step.** The 09-16 ruling stands: P6-as-specified is a per-invocation
   tax across 18 SKILL.md files. Follow the option-gates precedent — one rule, pointers from
   the places that already cite it. A contract test guards against the block returning.
4. **`/checkpoint` never prompts.** It appends to the ledger and reports; the user's standing
   `--auto` instruction is untouched.
5. **The Quarto case is the ledger's worked example.** The reference exists
   (`~/.claude/references/quarto-authoring.md`, 400 lines), nothing in the shipped tree names
   it (`grep -rn quarto-authoring agents/ skills/ rules/ hooks/ references/` is empty), and
   the only pointer is a memory file in one project. Source-side structure is already checked
   (`quarto_structure_check.py`, INV-25/INV-13); nothing checks the **rendered page**, which
   is where every entry in the reference's 18-row gotchas ledger shows up. Per
   `hooks/install-check.py`'s own docstring, a rule nothing executes is the artifact class
   that already failed here — so the fix is a script and a gate, plus the binding.

## Global Constraints

1. **Edits under `skills/`, `agents/`, `rules/`, `hooks/`, `references/`, `scripts/` are live
   in every linked paper on save.** Branch before the first edit. Never work on `main`.
2. **`./scripts/check_fork.sh` exits 0 and `python3 -m pytest tests/ -q` passes before every
   commit.** After a task that adds a shipped file (`references/quarto-authoring.md`,
   `scripts/ledger.py`, `scripts/check_render.py`), re-link every project and run
   `./scripts/check_install.sh --all` from `main` after the merge.
3. **Nothing project-specific ships.** Ledger rows live in `docs/`, which `check_fork.sh` does
   not scan, but the `note` text of every row is written generically (no dataset, journal or
   paper nouns) because the repo is public.
4. **Skill body budgets** (`tests/test_skill_contracts.py` `BUDGET`): `checkpoint` is at
   5,496 of 5,500. A raise is allowed only with a dated comment in the test naming the task
   and the measured size, following the A2/A3/A9 precedent. `promote` and `tools` are not
   budgeted.
5. **`/checkpoint` adds no prompt.** Any new behaviour is a command plus a report line.
6. **Numeric critic gates are untouched** (R-42, R-44, R-132). The render check is a write-gate
   item and a `/tools render` step, never a critic score.
7. **Vendored trees (`zotpilot-skills/`, `ai-audit/`) are not edited.** A ledger row whose
   target is under either is reported by `/promote` as "upstream PR", nothing else.
8. Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Decisions taken in this plan (executor proceeds on these unless the user overrides)

- **D1 — Where the Quarto reference lives.** Canonical copy moves to
  `references/quarto-authoring.md` in this repo; `~/.claude/references/quarto-authoring.md`
  becomes a symlink to it. Reason: `apply.sh` already links `references/*.md` into every
  project, the file is generic (the identity and noun scans return nothing on it — verified
  2026-09-25), `~/Courses/` keeps its documented path, and a copy would be the second source
  of truth the NAR memory file warns against. The user's global `CLAUDE.md` carve-out text
  still holds: the path it names still resolves.
- **D2 — Ledger threshold for corrections: 2 distinct projects.** Set by the user
  2026-09-25.
- **D3 — Ledger location: `docs/improvement-ledger.md` in this repo, Markdown table,
  append-only.** `docs/` is not shipped, so no re-link is needed for the ledger itself; only
  `scripts/ledger.py` is shipped (via `scripts/SHIPPED`).

---

## File map

| Path | Change | Responsibility |
|---|---|---|
| `scripts/ledger.py` | create, add to `scripts/SHIPPED` | `add`, `show`, `mark` on the ledger; resolves the ledger through its own real path |
| `docs/improvement-ledger.md` | create | the ledger: header + one table row per candidate |
| `tests/test_ledger.py` | create | ledger CLI behaviour |
| `rules/meta-governance.md` | modify | add "User corrections" section; state both bars |
| `rules/logging.md:71-74` | modify | Learning Loop names both paths |
| `skills/checkpoint/SKILL.md:73-79, 115-124` | modify | 4a appends to ledger; report line carries ids |
| `skills/tools/SKILL.md:182-187` | modify | `learn` names the correction rule and the ledger |
| `skills/promote/SKILL.md` | modify | Step 2b reads the ledger; `mark` on landing |
| `tests/test_improvement_loop.py` | create | rule content, pointers, no closing blocks, threshold |
| `tests/test_skill_contracts.py:72` | modify | checkpoint budget raise with note |
| `references/quarto-authoring.md` | create (moved) | canonical Quarto authoring reference |
| `~/.claude/references/quarto-authoring.md` | becomes symlink | courses keep their path |
| `agents/writer.md:40-52`, `agents/coder.md:64-71`, `skills/write/SKILL.md:135-139`, `skills/talk/SKILL.md` (create mode), `rules/quarto-empirical.md:321-335` | modify | bind the reference |
| `scripts/check_render.py` | create, add to `scripts/SHIPPED` | post-render checks on `pdftotext` output |
| `tests/test_check_render.py` | create | checker behaviour on text fixtures |
| `rules/quarto-empirical.md:199-205` | modify | write gate item 4 |
| `skills/tools/SKILL.md:84-102` | modify | `/tools render` runs the checker |
| `agents/coder.md:70-71` | modify | "Done means" includes the checker |
| `tests/test_quarto_binding.py` | create | every `.qmd`-writing agent/skill names the reference; gate item 4 present |

---

### Task 0: Branch

- [ ] **Step 1: Branch from main**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git status --porcelain && git checkout -b improvement-loop
```

Expected: no porcelain output before the checkout; `Switched to a new branch 'improvement-loop'`.

---

### Task 1: The ledger script

**Files:**
- Create: `scripts/ledger.py`
- Create: `docs/improvement-ledger.md`
- Modify: `scripts/SHIPPED` (append `ledger.py`)
- Test: `tests/test_ledger.py`

**Interfaces:**
- Produces: CLI `ledger.py add --project P --target T --note N [--date D] [--ledger PATH]`
  → prints the new id `L-001`; `ledger.py show [--open] [--ledger PATH]` → grouped report,
  exit 0; `ledger.py mark ID (landed SHA | declined REASON) [--ledger PATH]`. Threshold
  constant `REPEATED_AT = 2`. Row format: `| L-001 | 2026-09-25 | proj | target | note | open |`.
  Later tasks call these exact forms.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger.py
"""Cross-project improvement ledger (P6, plan 2026-09-25).

A correction recorded in one project's SESSION_REPORT dies there. The ledger is the one place
/checkpoint writes candidates to and /promote reads them from; `show` flags a target named by
REPEATED_AT distinct projects.
"""
import pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ledger.py"


def run(*args, ledger):
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--ledger", str(ledger)],
                          capture_output=True, text=True)


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = pathlib.Path(self.tmp.name) / "improvement-ledger.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_creates_the_file_with_header_and_returns_sequential_ids(self):
        r1 = run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "first",
                 "--date", "2026-09-25", ledger=self.ledger)
        r2 = run("add", "--project", "beta", "--target", "rules/x.md", "--note", "second",
                 "--date", "2026-09-26", ledger=self.ledger)
        self.assertEqual(0, r1.returncode, r1.stderr)
        self.assertEqual("L-001", r1.stdout.strip())
        self.assertEqual("L-002", r2.stdout.strip())
        text = self.ledger.read_text()
        self.assertIn("| id | date | project | target | note | status |", text)
        self.assertIn("| L-002 | 2026-09-26 | beta | rules/x.md | second | open |", text)

    def test_add_is_append_only(self):
        run("add", "--project", "a", "--target", "t", "--note", "n", ledger=self.ledger)
        before = self.ledger.read_text()
        run("add", "--project", "b", "--target", "t", "--note", "m", ledger=self.ledger)
        self.assertTrue(self.ledger.read_text().startswith(before))

    def test_pipe_in_note_is_escaped_so_the_table_survives(self):
        run("add", "--project", "a", "--target", "t", "--note", "x | y", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertIn("x \\| y", self.ledger.read_text())
        self.assertIn("t", r.stdout)

    def test_show_groups_by_target_and_flags_two_distinct_projects(self):
        run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "a", ledger=self.ledger)
        run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "b", ledger=self.ledger)
        run("add", "--project", "gamma", "--target", "agents/y.md", "--note", "c", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertNotIn("REPEATED", r.stdout, "same project twice is not repeated")
        run("add", "--project", "beta", "--target", "rules/x.md", "--note", "d", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertRegex(r.stdout, r"rules/x\.md.*projects=2.*REPEATED")
        self.assertRegex(r.stdout, r"agents/y\.md.*projects=1")

    def test_mark_landed_and_declined_change_status_and_open_hides_them(self):
        run("add", "--project", "a", "--target", "t1", "--note", "n", ledger=self.ledger)
        run("add", "--project", "b", "--target", "t2", "--note", "n", ledger=self.ledger)
        r = run("mark", "L-001", "landed", "abc1234", ledger=self.ledger)
        self.assertEqual(0, r.returncode, r.stderr)
        r = run("mark", "L-002", "declined", "project-specific", ledger=self.ledger)
        self.assertEqual(0, r.returncode, r.stderr)
        text = self.ledger.read_text()
        self.assertIn("| landed abc1234 |", text)
        self.assertIn("| declined: project-specific |", text)
        r = run("show", "--open", ledger=self.ledger)
        self.assertNotIn("t1", r.stdout)
        self.assertNotIn("t2", r.stdout)

    def test_mark_unknown_id_exits_2(self):
        run("add", "--project", "a", "--target", "t", "--note", "n", ledger=self.ledger)
        r = run("mark", "L-009", "landed", "abc", ledger=self.ledger)
        self.assertEqual(2, r.returncode)

    def test_show_on_missing_ledger_is_empty_not_an_error(self):
        r = run("show", ledger=self.ledger)
        self.assertEqual(0, r.returncode)
        self.assertIn("no rows", r.stdout)

    def test_ledger_is_shipped(self):
        self.assertIn("ledger.py", (ROOT / "scripts" / "SHIPPED").read_text().split())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_ledger.py -q`
Expected: 8 failures (script missing).

- [ ] **Step 3: Write the script**

```python
#!/usr/bin/env python3
"""ledger.py — the cross-project improvement ledger (rules/meta-governance.md, User corrections).

Why it exists. A correction to a shared skill, agent or rule made in one paper project is
recorded by /checkpoint as one line in that project's SESSION_REPORT.md. Six projects, six
files, nothing reads them together — so the same correction is made again in the next project.
This file is the one place /checkpoint writes such candidates and /promote reads them from.
`show` flags any target named by REPEATED_AT distinct projects.

The ledger lives in the research-claude checkout (docs/improvement-ledger.md), found through
this script's own real path so that `.claude/scripts/ledger.py` in a project resolves to the
shared checkout. Under a pinned install that is a project-local clone; `add` prints the path it
wrote so the caller can see which.

Exit 0 = done. Exit 2 = usage or unknown id.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

REPEATED_AT = 2
HEADER = ("# Improvement ledger\n\n"
          "Append-only. Written by `/checkpoint` (one row per pipeline improvement candidate), "
          "read by `/promote`. A target named by " + str(REPEATED_AT) + " distinct projects is "
          "flagged REPEATED by `scripts/ledger.py show`. Status is `open`, `landed <sha>` or "
          "`declined: <reason>`. Notes are generic — no dataset, journal or paper nouns; this "
          "repo is public.\n\n"
          "| id | date | project | target | note | status |\n"
          "|---|---|---|---|---|---|\n")
ROW = re.compile(r"^\| (L-\d{3,}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ((?:[^|]|\\\|)*) \| ([^|]*) \|\s*$")


def default_ledger() -> Path:
    return Path(__file__).resolve().parent.parent / "docs" / "improvement-ledger.md"


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


def rows(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        m = ROW.match(line)
        if m:
            out.append(dict(id=m[1], date=m[2].strip(), project=m[3].strip(),
                            target=m[4].strip(), note=m[5].strip(), status=m[6].strip()))
    return out


def cmd_add(a) -> int:
    path = a.ledger
    existing = rows(path)
    n = max((int(r["id"][2:]) for r in existing), default=0) + 1
    rid = f"L-{n:03d}"
    date = a.date or dt.date.today().isoformat()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(HEADER)
    with path.open("a") as f:
        f.write(f"| {rid} | {date} | {esc(a.project)} | {esc(a.target)} | {esc(a.note)} | open |\n")
    print(rid)
    print(f"ledger: {path}", file=sys.stderr)
    return 0


def cmd_show(a) -> int:
    rs = rows(a.ledger)
    if a.open:
        rs = [r for r in rs if r["status"] == "open"]
    if not rs:
        print("ledger: no rows")
        return 0
    by_target: dict[str, list] = {}
    for r in rs:
        by_target.setdefault(r["target"], []).append(r)
    for target, group in sorted(by_target.items(), key=lambda kv: (-len({r["project"] for r in kv[1]}), kv[0])):
        projects = {r["project"] for r in group}
        flag = "  REPEATED" if len(projects) >= REPEATED_AT else ""
        print(f"{target}  projects={len(projects)}  rows={len(group)}{flag}")
        for r in group:
            print(f"  {r['id']}  {r['date']}  {r['project']}  {r['status']}  — {r['note']}")
    return 0


def cmd_mark(a) -> int:
    path = a.ledger
    lines = path.read_text().splitlines(keepends=True) if path.exists() else []
    status = f"landed {a.value}" if a.what == "landed" else f"declined: {a.value}"
    hit = False
    for i, line in enumerate(lines):
        m = ROW.match(line)
        if m and m[1] == a.id:
            lines[i] = line[: m.start(6)] + f" {esc(status)} |\n"
            hit = True
    if not hit:
        print(f"ledger: no row {a.id}", file=sys.stderr)
        return 2
    path.write_text("".join(lines))
    print(f"{a.id}: {status}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", type=Path, default=default_ledger())
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); p.add_argument("--project", required=True); p.add_argument("--target", required=True)
    p.add_argument("--note", required=True); p.add_argument("--date"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("show"); p.add_argument("--open", action="store_true"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("mark"); p.add_argument("id"); p.add_argument("what", choices=["landed", "declined"])
    p.add_argument("value"); p.set_defaults(fn=cmd_mark)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
```

Note on `cmd_mark`: `m.start(6)` is the offset of the status group; the slice keeps `| id | … | note ` and the leading `|` before status. Verify with the test; if the regex group boundary leaves a double space, adjust the slice to `line[: m.start(6) - 1] + f" {esc(status)} |\n"` — the test's exact-string assertions decide.

- [ ] **Step 4: Ship it and create the ledger header**

```bash
cd /Users/andrew.mueller/Academic/research-claude && echo ledger.py >> scripts/SHIPPED && chmod +x scripts/ledger.py && python3 - <<'EOF'
import sys; sys.path.insert(0, "scripts"); import ledger, pathlib
p = pathlib.Path("docs/improvement-ledger.md"); p.write_text(ledger.HEADER); print(p.read_text())
EOF
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_ledger.py -q`
Expected: 8 passed.

- [ ] **Step 6: Check `tests/test_apply_lock.py` / `test_check_install.py` still pass with the new SHIPPED line**

Run: `python3 -m pytest tests/ -q`
Expected: all pass. If a test pins the SHIPPED count or list, update it and say so in the commit.

- [ ] **Step 7: Commit**

```bash
git add scripts/ledger.py scripts/SHIPPED docs/improvement-ledger.md tests/test_ledger.py && git commit -q -m "feat(ledger): cross-project improvement ledger — add/show/mark, REPEATED at 2 projects

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && git log --oneline -1
```

---

### Task 2: Seed the ledger with the Quarto corrections

**Files:**
- Modify: `docs/improvement-ledger.md` (three rows, via the script only)

**Interfaces:**
- Consumes: `ledger.py add` from Task 1.
- Produces: rows L-001…L-003; `show` prints `rules/quarto-empirical.md  projects=2 … REPEATED`. Task 7 marks them landed.

- [ ] **Step 1: Add the three rows**

Dates and projects are from the memory files named in the Spec; notes are generic.

```bash
cd /Users/andrew.mueller/Academic/research-claude && \
python3 scripts/ledger.py add --project NAR_settlement --date 2026-09-04 --target rules/quarto-empirical.md --note "Author correction: .qmd written without reading the Quarto authoring reference; silent render failures (dropped YAML field, doubled exhibit numbers, plain-text section refs). Nothing in the shipped tree names the reference." && \
python3 scripts/ledger.py add --project NAR_settlement --date 2026-09-21 --target rules/quarto-empirical.md --note "Same class twice in one session: kableExtra footnote boxed to table width clipped a column, then clipped words from a note; render exit 0. Only a check of the rendered page catches it." && \
python3 scripts/ledger.py add --project zoning2026 --date 2026-06-08 --target rules/quarto-empirical.md --note "R-generated .tex tables: unescaped % and Unicode outside math mode; fixed per file, never as a pre-render check." && \
python3 scripts/ledger.py show
```

Expected: last command prints `rules/quarto-empirical.md  projects=2  rows=3  REPEATED` and three indented rows.

- [ ] **Step 2: Commit**

```bash
git add docs/improvement-ledger.md && git commit -q -m "docs(ledger): seed with the three Quarto corrections (two projects) — first REPEATED target

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: The correction rule and its pointers

**Files:**
- Modify: `rules/meta-governance.md` (append a section; edit the "Learning promotion" lead-in)
- Modify: `rules/logging.md:71-74`
- Modify: `skills/tools/SKILL.md:182-187`
- Test: `tests/test_improvement_loop.py`

**Interfaces:**
- Produces: the literal heading `## User corrections` and the phrases `ask once`, `at the moment of the correction`, `2 distinct projects`, `scripts/ledger.py`, `never silently` in `rules/meta-governance.md`. Tasks 4 and 5 name `.claude/rules/meta-governance.md` and the ledger script; the test below pins those pointers.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_improvement_loop.py
"""The improvement loop (audit 2026-09-15 §3 P6; plan 2026-09-25).

One rule, in meta-governance.md, says what happens when the user corrects a shared skill,
agent or rule. The three places that used to carry the 3+ bar onto corrections point at it.
No SKILL.md carries a self-improvement closing block: that per-invocation tax was declined on
2026-09-16 and stays declined.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULE = (ROOT / "rules" / "meta-governance.md").read_text()


class TestTheRule(unittest.TestCase):
    def test_user_corrections_section_states_both_paths_and_the_threshold(self):
        i = RULE.index("## User corrections")
        s = RULE[i:]
        for phrase in ("ask once", "at the moment of the correction", "/promote",
                       "scripts/ledger.py", "2 distinct projects", "never silently"):
            self.assertIn(phrase, s, phrase)

    def test_the_three_plus_bar_is_scoped_to_log_inferred_learnings(self):
        i = RULE.index("## Learning promotion")
        j = RULE.index("## User corrections")
        self.assertIn("3+ projects", RULE[i:j])
        self.assertRegex(RULE[i:j], r"dispatch log|state file")
        self.assertNotIn("3+", RULE[j:], "the corrections section must not restate the 3+ bar")


class TestPointers(unittest.TestCase):
    def test_checkpoint_tools_learn_and_logging_point_at_the_rule_and_the_ledger(self):
        for rel in ("skills/checkpoint/SKILL.md", "skills/tools/SKILL.md", "rules/logging.md"):
            t = (ROOT / rel).read_text()
            self.assertIn("meta-governance.md", t, rel)
            self.assertIn("ledger.py", t, rel)
            self.assertNotIn("3+ projects", t, f"{rel} still carries the 3+ bar onto corrections")

    def test_promote_reads_the_ledger(self):
        t = (ROOT / "skills" / "promote" / "SKILL.md").read_text()
        self.assertIn("ledger.py show --open", t)
        self.assertIn("ledger.py mark", t)
        self.assertIn("REPEATED", t)


class TestNoClosingBlocks(unittest.TestCase):
    def test_no_skill_carries_a_self_improvement_closing_step(self):
        bad = []
        for p in (ROOT / "skills").glob("*/SKILL.md"):
            if re.search(r"skill-improvement\.md|Apply .*improvement rule", p.read_text()):
                bad.append(p.parent.name)
        self.assertEqual([], bad)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_improvement_loop.py -q`
Expected: 4 failures, 1 pass (`TestNoClosingBlocks`).

- [ ] **Step 3: Amend `rules/meta-governance.md`**

Replace the line `When a pattern has been validated across 3+ projects and the user confirms it:` with:

```markdown
This table is for learnings **inferred from the dispatch log and state file** — strikes,
escalations, first-pass scores. Inferred once, in one project, they are noise; the bar is
validation across 3+ projects and the user's confirmation. A user's own correction is not
inferred and is not governed by this bar — see "User corrections" below.

When a pattern has been validated across 3+ projects and the user confirms it:
```

Append at end of file:

```markdown

## User corrections

A user correcting the output of a shared skill, agent or rule — or naming an output as the
example to follow — is decided evidence, not a pattern to be counted. Two paths, and a
correction is **never silently** applied to the shared tree:

1. **At the moment of the correction, ask once:** "Make this permanent in `<target file>`?"
   On yes: edit through the link, run `scripts/check_fork.sh`, and land it with `/promote`,
   whose commit names the project it came from. On no, or when the correction is
   project-specific: a real-file override or a gotchas line in the project.
2. **Whatever the answer, `/checkpoint` records it** — one row in the shared ledger,
   `python3 .claude/scripts/ledger.py add`, and one report line. `/promote` reads the ledger
   (`ledger.py show --open`) and flags any target named by **2 distinct projects** as
   REPEATED. That is the signal that a correction declined or missed once is a recurring
   mistake, and it goes to the user with the rows attached.

The ledger is `docs/improvement-ledger.md` in the research-claude checkout. Rows are generic
(no dataset, journal or paper nouns). A row whose target is under `zotpilot-skills/` or
`ai-audit/` is reported as "upstream PR" and never edited here (`/promote` Step 2.5).

No skill carries a closing "apply the improvement rule" step: that is a per-invocation tax
across every SKILL.md, declined 2026-09-16 and declined again here. The rule is this section;
the mechanism is `/checkpoint` → ledger → `/promote`.
```

- [ ] **Step 4: Repoint `rules/logging.md` Learning Loop**

Replace lines 71–74 (`## Learning Loop` and its paragraph) with:

```markdown
## Learning Loop

Owned by `.claude/rules/meta-governance.md`. Two inputs: `/pipeline` surfaces suggested
learnings from the state file and dispatch log (3+ projects, user approves); `/checkpoint`
writes every pipeline-improvement candidate to the shared ledger with
`.claude/scripts/ledger.py add`, and `/promote` flags a target two projects named. `/promote`
lands both.
```

- [ ] **Step 5: Repoint `/tools learn`**

Replace the paragraph at `skills/tools/SKILL.md:185-187` (`A **correction** to a pipeline skill…lands it.`) with:

```markdown
A **correction** to a pipeline skill, agent or rule is not handled here and is never applied
silently. It follows `.claude/rules/meta-governance.md` (User corrections): ask once at the
moment of the correction and land on yes with `/promote`; `/checkpoint` records every
candidate in the shared ledger (`.claude/scripts/ledger.py add`), and `/promote` flags a
target two projects named.
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_improvement_loop.py tests/test_tools_contracts.py -q`
Expected: `TestTheRule` and `test_no_skill…` pass; `test_checkpoint_tools_learn_and_logging…` still fails on `skills/checkpoint/SKILL.md` (Task 4) and `test_promote_reads_the_ledger` fails (Task 5). `test_tools_contracts` passes (`learn` stays a pointer with no command block — confirm `section("learn")` has no triple-backtick fence).

- [ ] **Step 7: Commit**

```bash
./scripts/check_fork.sh && git add rules/meta-governance.md rules/logging.md skills/tools/SKILL.md tests/test_improvement_loop.py && git commit -q -m "feat(rules): user corrections — ask once, land via /promote, ledger at 2 projects; 3+ bar scoped to log-inferred learnings

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `/checkpoint` writes the ledger

**Files:**
- Modify: `skills/checkpoint/SKILL.md:73-79` (4a paragraph) and `:115-124` (report block)
- Modify: `tests/test_skill_contracts.py:72` (budget)

**Interfaces:**
- Consumes: `ledger.py add --project --target --note` (Task 1); rule section name from Task 3.
- Produces: report line `- Pipeline improvement candidates: [none | N — <skill>: <one-line correction> (L-NNN)]`.

- [ ] **Step 1: Measure the current body size**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 - <<'EOF'
import pathlib; t=pathlib.Path("skills/checkpoint/SKILL.md").read_text(); print(len(t.split("---",2)[2]))
EOF
```

Expected: 5496.

- [ ] **Step 2: Replace the 4a correction paragraph**

Replace `skills/checkpoint/SKILL.md:73-79` (from `**A \`feedback\` memory that corrects…` through `The report line is what carries it forward.`) with:

```markdown
**A `feedback` memory that corrects a pipeline skill, agent or rule** — rather than stating a
project preference — is also a ledger row and a Step 5 report line. Never edit the shared tree
and never prompt (`.claude/rules/meta-governance.md`, User corrections):

```bash
python3 .claude/scripts/ledger.py add --project "$(basename "$PWD")" \
  --target <shared file it would change> --note "<one generic sentence>"
```

The printed id goes on the report line. `/promote` reads the ledger and flags a target two
projects named.
```

- [ ] **Step 3: Update the report line**

In the report block (`Checkpoint saved:`), replace
`- Pipeline improvement candidates: [none | N — <skill>: <one-line correction>]` with
`- Pipeline improvement candidates: [none | N — <skill>: <one-line correction> (L-NNN)]`.

- [ ] **Step 4: Measure again and raise the budget with a note**

Run the Step 1 command. Expected: roughly 5,750–5,850. In `tests/test_skill_contracts.py` replace `"checkpoint": 5500,` with:

```python
    # 2026-09-25 (improvement loop, Task 4): checkpoint 5,500 -> 5,900. 4a appends the
    # correction to the shared ledger (one command, one id on the report line); measured <N>.
    "checkpoint": 5900,
```

Fill `<N>` with the measured size. If the measured size exceeds 5,900, shorten the 4a prose, not the command.

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_improvement_loop.py tests/test_skill_contracts.py -q`
Expected: only `test_promote_reads_the_ledger` still fails.

- [ ] **Step 6: Commit**

```bash
./scripts/check_fork.sh && git add skills/checkpoint/SKILL.md tests/test_skill_contracts.py && git commit -q -m "feat(checkpoint): record every pipeline-improvement candidate in the shared ledger; budget 5,500 -> 5,900

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `/promote` reads the ledger

**Files:**
- Modify: `skills/promote/SKILL.md` (new Step 2b after Step 2.5; a line in Step 4; a line in "What this skill does NOT do")

**Interfaces:**
- Consumes: `ledger.py show --open`, `ledger.py mark ID landed SHA`, `ledger.py mark ID declined REASON`.

- [ ] **Step 1: Insert Step 2b after Step 2.5 (before `## Step 3: Project overrides`)**

```markdown
## Step 2b: The improvement ledger

`/checkpoint` in every project appends its pipeline-improvement candidates to
`$RC/docs/improvement-ledger.md` (`.claude/rules/meta-governance.md`, User corrections).
Read it here — this is the only step that does:

```bash
python3 "$RC/scripts/ledger.py" show --open
```

The output is grouped by target file and sorted so targets named by the most projects come
first. A line ending **REPEATED** is a target two or more distinct projects corrected: present
those first, with their rows, and ask whether to land a fix now. For each row the user acts on:

- Landed here: after the upstream commit, `python3 "$RC/scripts/ledger.py" mark L-NNN landed <sha>`.
- Declined as project-specific or wrong: `python3 "$RC/scripts/ledger.py" mark L-NNN declined "<reason>"`.
- Target under `zotpilot-skills/` or `ai-audit/`: report "upstream PR" and leave the row open —
  the fork PR closes it (Step 2.5).

Rows for one project only are listed after; do not push them at the user unless asked. They
are there so the next project's correction of the same target becomes REPEATED.
```

- [ ] **Step 2: Add one line to Step 4**

After `**Refuse to commit a file naming a project, journal, or dataset.**` add the sentence:
`The same standard applies to a ledger row's note before it is quoted in a commit message.`

- [ ] **Step 3: Add to "What this skill does NOT do"**

`- Does not edit the ledger by hand — rows are added by `/checkpoint` and marked by `ledger.py mark`, never rewritten.`

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_improvement_loop.py tests/test_skill_contracts.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
./scripts/check_fork.sh && git add skills/promote/SKILL.md && git commit -q -m "feat(promote): Step 2b reads the improvement ledger; REPEATED targets first; mark landed/declined

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Bind the Quarto authoring reference

**Files:**
- Create: `references/quarto-authoring.md` (moved from `~/.claude/references/quarto-authoring.md`)
- Modify: `~/.claude/references/quarto-authoring.md` → symlink (outside the repo; D1)
- Modify: `agents/writer.md:40-52` (Artifact Reading Protocol), `agents/coder.md:64-71` (Stage 3), `skills/write/SKILL.md:135-139` (Quarto Conventions), `skills/talk/SKILL.md` (`/talk create` mode body), `rules/quarto-empirical.md:321-335` (Relation to Other Rules)
- Test: `tests/test_quarto_binding.py`

**Interfaces:**
- Produces: the path string `.claude/references/quarto-authoring.md` in each bound file; Task 7 extends the same test with the gate item.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quarto_binding.py
"""The Quarto authoring reference is bound where .qmd is written (ledger L-001..L-003).

The reference existed for three weeks with no shipped file naming it; two projects corrected
the same silent failures. Binding means: named in the step or protocol that writes the file,
not in a resources table (tests/test_skill_contracts.py has the same standard).
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ".claude/references/quarto-authoring.md"
BOUND = [
    ("agents/writer.md", r"## Artifact Reading Protocol"),
    ("agents/coder.md", r"### Stage 3"),
    ("skills/write/SKILL.md", r"## Quarto Conventions"),
    ("skills/talk/SKILL.md", r"### `/talk create"),
    ("rules/quarto-empirical.md", r"## Relation to Other Rules"),
]


def section(text, heading_re):
    m = re.search(r"^(#{2,4}) [^\n]*" + heading_re, text, flags=re.M)
    assert m, heading_re
    rest = text[m.end():]
    n = re.search(r"^" + m.group(1) + r" ", rest, flags=re.M)
    return rest[: n.start()] if n else rest


class TestReferenceShips(unittest.TestCase):
    def test_reference_is_in_the_shipped_tree_and_generic(self):
        p = ROOT / "references" / "quarto-authoring.md"
        self.assertTrue(p.exists())
        t = p.read_text()
        self.assertIn("## The gotchas ledger", t)
        self.assertNotRegex(t, r"\bNAR\b|zoning2026|POGM", "project noun in a shipped reference")


class TestBinding(unittest.TestCase):
    def test_every_qmd_writer_names_the_reference_in_its_writing_step(self):
        missing = [f"{rel} /{h}/" for rel, h in BOUND
                   if REF not in section((ROOT / rel).read_text(), h)]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_quarto_binding.py -q`
Expected: 2 failures.

- [ ] **Step 3: Move the reference; make the global path a symlink**

```bash
cd /Users/andrew.mueller/Academic/research-claude && \
test -f ~/.claude/references/quarto-authoring.md && ! test -L ~/.claude/references/quarto-authoring.md && \
mv ~/.claude/references/quarto-authoring.md references/quarto-authoring.md && \
ln -s "$PWD/references/quarto-authoring.md" ~/.claude/references/quarto-authoring.md && \
ls -la ~/.claude/references/ && head -3 ~/.claude/references/quarto-authoring.md
```

Expected: the global path is a symlink and its first line is `# Quarto Authoring Reference — how to write each object so it actually renders`.

Then edit the file's own header so the "Lives in" cell of the **This file** row reads
`` `references/quarto-authoring.md` in research-claude, linked into every project as `.claude/references/quarto-authoring.md`; `~/.claude/references/quarto-authoring.md` is a symlink to it for `~/Courses/` ``.

- [ ] **Step 4: Bind it in five places**

`agents/writer.md`, Artifact Reading Protocol — insert as the new item 1 (renumber the rest):
`1. Read `.claude/references/quarto-authoring.md` before the first edit to any `.qmd` — its gotchas ledger is the list of ways a `.qmd` fails silently; write to the intersection of every format the document renders to`

`agents/coder.md`, Stage 3 — append the sentence:
`Before writing any `tbl-`/`fig-` chunk, read `.claude/references/quarto-authoring.md` (Tables, Figures, Cross-references): a table note wider than the text block clips without an error, and `escape` rules differ by output format.`

`skills/write/SKILL.md`, Quarto Conventions — add a first bullet:
`- Read `.claude/references/quarto-authoring.md` before editing the `.qmd`; the writer is told the same, and the post-render check (`.claude/rules/quarto-empirical.md`, gate item 4) is what proves it took.`

`skills/talk/SKILL.md`, `/talk create` mode — add one line where the `.qmd` is written (near `Save to `talks/[format]_talk.qmd``):
`Read `.claude/references/quarto-authoring.md` (Format matrix, Diagrams) first: RevealJS accepts raw HTML that Beamer and PDF drop, and a `{dot}`/`{mermaid}` cell without `fig-width` overflows the slide silently.`

`rules/quarto-empirical.md`, Relation to Other Rules — add a table row after `quarto-word.md`:
`| `.claude/references/quarto-authoring.md` | **Required reading before any `.qmd` edit** — tool mechanics: what renders in which format, what drops silently; its post-render checklist is gate item 4 |`

Measure `write` afterwards (budget 8,200) with the Task 4 Step 1 command on `skills/write/SKILL.md`; if over, trim the bullet, not the path.

- [ ] **Step 5: Run the tests and the fork gate**

Run: `python3 -m pytest tests/test_quarto_binding.py tests/test_skill_contracts.py tests/test_check_refs.py -q && ./scripts/check_fork.sh`
Expected: pass; `check_fork` PASS on every line (the identity scan covers `references/`).

- [ ] **Step 6: Commit**

```bash
git add references/quarto-authoring.md agents/writer.md agents/coder.md skills/write/SKILL.md skills/talk/SKILL.md rules/quarto-empirical.md tests/test_quarto_binding.py && git commit -q -m "feat(quarto): ship the authoring reference in references/ and bind it where .qmd is written (ledger L-001..L-003)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: The post-render check as write-gate item 4

**Files:**
- Create: `scripts/check_render.py`; append to `scripts/SHIPPED`
- Test: `tests/test_check_render.py`; extend `tests/test_quarto_binding.py`
- Modify: `rules/quarto-empirical.md:199-205` (write gate), `skills/tools/SKILL.md:84-102` (`/tools render`), `agents/coder.md:70-71` (Done means)

**Interfaces:**
- Produces: CLI `check_render.py <file.pdf|file.txt> [--expect TEXT]... [--columns "Table N: a,b,c"]...` → exit 0 clean, 1 findings (one per line, `KIND: detail`), 2 cannot run. Finding kinds: `UNRESOLVED`, `LITERAL_TEX`, `LITERAL_MD`, `LITERAL_HTML`, `DOUBLED`, `MISSING`, `COLUMN`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_check_render.py
"""check_render.py — the rendered page is the only place Quarto's failures show (L-002).

Every check here is a row of the authoring reference's gotchas ledger or post-render
checklist, run mechanically on pdftotext output. Fixtures are text so no PDF is needed.
"""
import pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_render.py"

CLEAN = """Effects of Policy on Outcomes
Keywords: housing; land use; supply
1 Introduction
As Table 1 shows, the estimate is 0.42 (see Section 3).
Table 1: Main estimates
Outcome  Estimate  SE  N
Figure 1: Event study
Notes: Standard errors clustered by state. The parallel-trends assumption IS NOT MET.
"""


def run(text, *args):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text); path = f.name
    return subprocess.run([sys.executable, str(SCRIPT), path, *args], capture_output=True, text=True)


class TestCheckRender(unittest.TestCase):
    def test_clean_text_exits_0(self):
        r = run(CLEAN)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_unresolved_crossref(self):
        r = run(CLEAN + "See ?@tbl-robust for details.\n")
        self.assertEqual(1, r.returncode)
        self.assertIn("UNRESOLVED: ?@tbl-robust", r.stdout)

    def test_literal_tex_markdown_and_html(self):
        r = run(CLEAN + "\\textbf{bold} and *stars* and <span>x</span>\n")
        self.assertIn("LITERAL_TEX: \\textbf{", r.stdout)
        self.assertIn("LITERAL_MD: *stars*", r.stdout)
        self.assertIn("LITERAL_HTML: <span>", r.stdout)

    def test_doubled_exhibit_number(self):
        r = run(CLEAN + "Table 2: Table 2: Robustness\n")
        self.assertIn("DOUBLED: Table 2", r.stdout)

    def test_expect_phrase_missing_and_present_across_line_wrap(self):
        r = run(CLEAN, "--expect", "IS NOT MET", "--expect", "Keywords:")
        self.assertEqual(0, r.returncode, r.stdout)
        wrapped = CLEAN.replace("assumption IS NOT MET", "assumption IS\nNOT MET")
        r = run(wrapped, "--expect", "IS NOT MET")
        self.assertEqual(0, r.returncode, "a line wrap is not a missing phrase")
        clipped = CLEAN.replace(" IS NOT MET", "")
        r = run(clipped, "--expect", "IS NOT MET")
        self.assertIn("MISSING: IS NOT MET", r.stdout)

    def test_expect_ignores_ligatures(self):
        lig = CLEAN.replace("Outcomes", "Ef\ufb01ciency")  # pdftotext emits the fi ligature
        r = run(lig, "--expect", "Efficiency")
        self.assertEqual(0, r.returncode, r.stdout)

    def test_significance_stars_are_not_literal_markdown(self):
        r = run(CLEAN + "0.42*** (0.03)** and 0.10*\n")
        self.assertNotIn("LITERAL_MD", r.stdout)

    def test_columns_present_and_dropped(self):
        r = run(CLEAN, "--columns", "Table 1: Outcome,Estimate,SE,N")
        self.assertEqual(0, r.returncode, r.stdout)
        r = run(CLEAN.replace("Outcome  Estimate  SE  N", "Outcome  Estimate  SE"), "--columns", "Table 1: Outcome,Estimate,SE,N")
        self.assertIn("COLUMN: Table 1: N", r.stdout)

    def test_missing_input_exits_2(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent.pdf"], capture_output=True, text=True)
        self.assertEqual(2, r.returncode)

    def test_shipped(self):
        self.assertIn("check_render.py", (ROOT / "scripts" / "SHIPPED").read_text().split())


if __name__ == "__main__":
    unittest.main()
```

Also append to `tests/test_quarto_binding.py`:

```python
class TestGate(unittest.TestCase):
    def test_write_gate_has_item_4_and_render_runs_it(self):
        rule = (ROOT / "rules" / "quarto-empirical.md").read_text()
        self.assertRegex(rule, r"\[ \] 4\. .*check_render\.py")
        tools = (ROOT / "skills" / "tools" / "SKILL.md").read_text()
        self.assertIn("check_render.py", section(tools, r"`/tools render"))
        coder = (ROOT / "agents" / "coder.md").read_text()
        self.assertIn("check_render.py", section(coder, r"### Stage 3"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_check_render.py tests/test_quarto_binding.py -q`
Expected: 10 + 1 failures.

- [ ] **Step 3: Write the script**

```python
#!/usr/bin/env python3
"""check_render.py — post-render checks on the RENDERED output (write gate item 4).

Why it exists. Quarto fails silently: an unresolved `@ref` prints `?@name` and exits 0; a
table note wider than the text block clips words out of a sentence; an overwide table drops
a column; a declared `keywords:` never reaches the page; a `fig-` label in a manually-numbered
document prints a second number. `quarto_structure_check.py` reads the SOURCE. This reads the
PAGE, through `pdftotext`, and does what the authoring reference's post-render checklist asks
a human to do by eye — which two projects showed nobody does.

Usage: check_render.py <manuscript.pdf | rendered.txt> [--expect TEXT]... [--columns "Table N: a,b,c"]...
  --expect   a phrase that must appear (keywords line, a mandated note phrase); whitespace and
             ligatures are normalised, so a line wrap is not a miss.
  --columns  a table's caption prefix and its column headers; each header must appear after
             that caption and before the next "Table"/"Figure" caption.
Exit 0 = clean. Exit 1 = findings, one per line as KIND: detail. Exit 2 = cannot run.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIG = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\u2019": "'"}


def norm(s: str) -> str:
    for k, v in LIG.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s)


def load(path: Path) -> str:
    if not path.exists():
        sys.exit(f"check_render: {path} not found")
    if path.suffix.lower() == ".pdf":
        if not shutil.which("pdftotext"):
            sys.exit("check_render: pdftotext not on PATH (brew install poppler)")
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"check_render: pdftotext failed: {r.stderr.strip()}")
        return r.stdout
    return path.read_text(errors="replace")


def findings(text: str, expect: list[str], columns: list[str]) -> list[str]:
    out = []
    for m in re.finditer(r"\?@[\w:.-]+", text):
        out.append(f"UNRESOLVED: {m.group(0)}")
    for m in re.finditer(r"\\[A-Za-z]+\{", text):
        out.append(f"LITERAL_TEX: {m.group(0)}")
    for m in re.finditer(r"(?<![\w)])\*{1,2}(?=\S)[^*\n]{1,80}?(?<=\S)\*{1,2}(?!\w)", text):
        out.append(f"LITERAL_MD: {m.group(0)}")
    for m in re.finditer(r"</?(span|div|br|b|i|em|strong|sup|sub)\b[^>]*>", text):
        out.append(f"LITERAL_HTML: {m.group(0)}")
    for m in re.finditer(r"\b(Table|Figure)\s+(\d+[A-Za-z]?)\W{0,3}(Table|Figure)\s+\2\b", text):
        out.append(f"DOUBLED: {m.group(1)} {m.group(2)}")
    flat = norm(text)
    for e in expect:
        if norm(e) not in flat:
            out.append(f"MISSING: {e}")
    caps = list(re.finditer(r"^\s*(Table|Figure)\s+\d+[A-Za-z]?[:.]", text, flags=re.M))
    for spec in columns:
        head, _, cols = spec.partition(":")
        head = head.strip()
        block = None
        for i, c in enumerate(caps):
            if text[c.start():c.end()].strip().startswith(head):
                end = caps[i + 1].start() if i + 1 < len(caps) else len(text)
                block = norm(text[c.start():end]); break
        if block is None:
            out.append(f"COLUMN: {head}: caption not found"); continue
        for col in [c.strip() for c in cols.split(",") if c.strip()]:
            if norm(col) not in block:
                out.append(f"COLUMN: {head}: {col}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--expect", action="append", default=[])
    ap.add_argument("--columns", action="append", default=[])
    a = ap.parse_args()
    fs = findings(load(a.path), a.expect, a.columns)
    for f in fs:
        print(f)
    print(f"check_render: {len(fs)} finding(s)")
    return 1 if fs else 0


if __name__ == "__main__":
    sys.exit(main())
```

Then: `echo check_render.py >> scripts/SHIPPED && chmod +x scripts/check_render.py`.

- [ ] **Step 4: Run the checker tests**

Run: `python3 -m pytest tests/test_check_render.py -q`
Expected: 10 passed. If `test_literal_tex_markdown_and_html` reports `LITERAL_MD` on the `*stars*` fixture but the CLEAN text also trips on something, tighten the fixture, not the regex, and record why in the test.

- [ ] **Step 5: Wire the gate**

`rules/quarto-empirical.md` write gate block becomes:

```
[ ] 1. Raw data is in place: every file referenced in cache.extra exists in data/raw/
[ ] 2. quarto render manuscript_<project>.qmd exits 0 with no NA/NaN in inline expressions
[ ] 3. python3 .claude/scripts/prose_number_check.py manuscript_<project>.qmd exits 0
[ ] 4. python3 .claude/scripts/check_render.py <rendered .pdf> --expect "<each phrase the page must show>" exits 0
```

and after `No script inventory. No registry coverage audit. No timestamp check.` add:

```markdown
**Item 4 reads the page, not the source.** Item 2 proves the render ran; it proves nothing
about what the page shows, because Quarto's failures are silent: an unresolved `@ref` prints
`?@name` at exit 0, a note wider than the text block clips words out of its own sentence, an
overwide table drops a column, a declared `keywords:` never appears. Two projects corrected
these by hand before this line existed (`docs/improvement-ledger.md`, L-001..L-003). Pass
`--expect` for every phrase a journal or an invariant requires on the page, and `--columns`
for every wide table. The check is `.claude/references/quarto-authoring.md`'s post-render
checklist, executed.
```

`skills/tools/SKILL.md` `/tools render` — replace the paragraph starting `Pass: exit 0, output artifact newer than the source.` with:

```markdown
Pass: exit 0, output artifact newer than the source, and the rendered page checked:
```bash
python3 .claude/scripts/check_render.py "${MS%.qmd}.pdf" --expect "<mandated phrases>"
```
That is write-gate item 4 (`.claude/rules/quarto-empirical.md`): unresolved `?@` refs, literal
`\commands`/`*markup*`/`<tags>`, doubled exhibit numbers, missing phrases, dropped columns
(`--columns "Table N: a,b,c"`). A clean render says nothing about hardcoded prose numbers —
that is `prose_number_check.py` (INV-11). Do not invoke xelatex or pandoc by hand unless
debugging a render failure — `quarto render` is the only build step.
```

`agents/coder.md` Stage 3 "Done means" becomes:
`**Done means:** `quarto render` exits 0, `python3 .claude/scripts/prose_number_check.py` exits 0, `python3 .claude/scripts/check_render.py <pdf>` exits 0, and the coder-critic has scored the manuscript's chunks.`

- [ ] **Step 6: Run everything**

Run: `python3 -m pytest tests/ -q && ./scripts/check_fork.sh`
Expected: all pass, including `test_tools_contracts` (render section still has `pipeline.py manuscript`, still no `manuscript_<project>.qmd`), `test_quarto_binding.TestGate`, and `TestNoPhantomLimits` (unaffected).

- [ ] **Step 7: Prove it on a real render**

```bash
cd ~/Research/NAR_settlement && MS=$(python3 .claude/scripts/pipeline.py manuscript) && ls -la "${MS%.qmd}.pdf" && python3 /Users/andrew.mueller/Academic/research-claude/scripts/check_render.py "${MS%.qmd}.pdf" --expect "IS NOT MET"; echo "exit $?"
```

Expected: the checker runs on the existing PDF (do **not** re-render; the PDF may be stale and that is fine for a smoke test). Record the finding count in the commit message. A non-zero exit here is information about the manuscript, not a failure of this task.

- [ ] **Step 8: Mark the ledger rows landed and commit**

```bash
cd /Users/andrew.mueller/Academic/research-claude && git add scripts/check_render.py scripts/SHIPPED rules/quarto-empirical.md skills/tools/SKILL.md agents/coder.md tests/test_check_render.py tests/test_quarto_binding.py && git commit -q -m "feat(quarto): check_render.py — post-render page check as write-gate item 4; /tools render and coder run it

Smoke test on a live manuscript PDF: <N> finding(s).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && SHA=$(git rev-parse --short HEAD) && for i in 001 002 003; do python3 scripts/ledger.py mark L-$i landed "$SHA"; done && git add docs/improvement-ledger.md && git commit -q -m "docs(ledger): L-001..L-003 landed

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && python3 scripts/ledger.py show
```

Expected: `ledger: no rows` is **not** printed (rows are landed, still listed); `show --open` prints `ledger: no rows`.

---

### Task 8: Merge, re-link the fleet, close out

**Files:**
- Modify: `docs/SESSION_REPORT.md` (append), `CLAUDE.md` (Start here paragraph), `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md` (strike the P6 bullet), this plan's Status line
- Each paper repo: `.claude/pipeline.lock` refresh (committed there, as on 2026-09-25)

- [ ] **Step 1: Merge**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && git checkout main && git merge --no-ff improvement-loop -m "Merge improvement-loop

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 2: Re-link every project (three new shipped files: one reference, two scripts)**

All six locks read `# installed via: pinned` and every link resolves to this checkout
(`readlink ~/Research/NAR_settlement/.claude/skills/write` → `../../../../Academic/research-claude/skills/write`,
verified 2026-09-25). Re-link without `--tip`, as the 2026-09-25 refresh did:

```bash
for p in ~/Research/BRI ~/Research/ESG ~/Research/NAR_settlement ~/Research/POGM4 ~/Research/affordable_housing_2026 ~/Research/zoning2026; do
  /Users/andrew.mueller/Academic/research-claude/apply.sh --project-dir "$p" --link;
done && /Users/andrew.mueller/Academic/research-claude/scripts/check_install.sh --all
```

Expected: `check_install --all` PASS ×6; each lock still says `pinned` with the new merge SHA. Each project shows `.claude/references/quarto-authoring.md`, `.claude/scripts/ledger.py`, `.claude/scripts/check_render.py` as links.

- [ ] **Step 3: Commit each lock refresh in its paper repo**

```bash
for p in ~/Research/BRI ~/Research/ESG ~/Research/NAR_settlement ~/Research/POGM4 ~/Research/affordable_housing_2026 ~/Research/zoning2026; do
  git -C "$p" add .claude/pipeline.lock && git -C "$p" commit -q -m "chore: pipeline lock refresh (ledger, check_render, quarto-authoring reference)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && echo "committed $p";
done
```

- [ ] **Step 4: Verify the global symlink survives from a courses path**

```bash
head -1 ~/.claude/references/quarto-authoring.md && readlink ~/.claude/references/quarto-authoring.md
```

Expected: the title line and the research-claude path.

- [ ] **Step 5: Close out the docs**

- In `docs/plans/2026-09-24-option-gates-subagent-routing-evals.md`, strike the `**P6 self-improvement rule.**` bullet the way the `/tools validate-bib` bullet is struck, ending with `**Closed 2026-09-25** by `docs/plans/2026-09-25-improvement-loop-and-quarto-render-gate.md`.`
- In `CLAUDE.md` "Start here", replace `the P6 self-improvement rule (needs its own decision against `rules/meta-governance.md`'s 3+ project bar)` with a sentence that P6 closed on 2026-09-25 under this plan (correction rule at 2 projects, `docs/improvement-ledger.md`, `scripts/check_render.py` as gate item 4) and that the remaining open items are the vendored P1 offenders and the evals.
- Set this plan's **Status** line to `complete (2026-09-25)` with the merge SHA.
- Append the session entry to `docs/SESSION_REPORT.md` in the format of the existing entries: scope, the decision (Rationale §1–§5 in three sentences), what shipped with SHAs, the smoke-test finding count, fleet results, and "Still open" (vendored P1 offenders; evals for 20 skills; the 3+ bar for log-inferred learnings remains unenforced — no cross-project source for it exists, recorded here rather than built).

- [ ] **Step 6: Final gates and commit**

```bash
cd /Users/andrew.mueller/Academic/research-claude && python3 -m pytest tests/ -q && ./scripts/check_fork.sh && ./scripts/check_install.sh --all && git add CLAUDE.md docs/ && git commit -q -m "docs: close P6 — improvement loop and Quarto render gate; session entry 2026-09-25

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && git log --oneline -3
```

Nothing is pushed. `main` stays ahead of `origin` until the user pushes.

---

## What this plan deliberately leaves open

- **The 3+ bar for log-inferred learnings is still unenforced.** `/pipeline` reads one
  project's state file and dispatch log; the dispatch log holds agent, timestamp and session
  only, so a cross-project count would carry no cause. If a case for it ever arises, the
  ledger's `add` is the landing place (a `--source pipeline` flag), not a second file.
- **`check_render.py` is not a critic and not a hook.** It is gate item 4 and a `/tools
  render` step. Wiring it into `pipeline.py`'s `render` predicate (which already fails on an
  unresolved-crossref WARNING per INV-13) is a separate decision: the predicate would need
  the `--expect` list from somewhere, and the project `CLAUDE.md` is the only candidate.
- **Vendored skills that write `.qmd`** (`ztp-tutor` writes annotations, not `.qmd`; none of
  the others do) — no binding needed; recorded so the next audit does not ask.

## Progress Log

| Task | Status | Commit | Notes |
|---|---|---|---|
| 0 | | | |
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
