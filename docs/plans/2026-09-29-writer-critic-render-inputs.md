# writer-critic render inputs (ledger L-005) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: complete (2026-09-29), merged as `6fc61f0`.**

## Decisions (user, 2026-09-29)

1. **Render on every review.** `critic-inputs` always renders the declared manuscript, never skips as fresh, and every route that dispatches writer-critic runs it first (Tasks 1 and 3).
2. **`.md` manuscripts stay unscored.** No pandoc build is wired; a Markdown manuscript's Build is reported NOT SCORED (Task 2, "Out of scope").
3. **Commit unlogged.** The `critic-inputs` logs are session mechanics: `*.log` stays gitignored and no log is ever committed.
4. **Execution is inline** (`superpowers:executing-plans`), in this session, not subagent-driven.

**Goal:** writer-critic scores its Render category from a render/prose-check/page-check log the dispatching skill produces and names in the dispatch, and marks the category NOT SCORED when no log is given. The critic does not get Bash back.

**Architecture:** A new `pipeline.py critic-inputs` subcommand always renders the declared manuscript. It also runs `prose_number_check.py` and, on a fresh PDF, `check_render.py`. It writes all three outputs to one timestamped log and prints the path. Every skill that dispatches writer-critic (`/write`, `/review`, `/revise`) runs it right before the dispatch and puts the path in the prompt. The rubric's category 6 is rewritten to read that log, and to report NOT SCORED when there isn't one. This is the same division of labour §2 of `rules/agents.md` already sets up for report-saving: the skill has the tools, and the critic judges what it is handed.

**Tech Stack:** Python 3.9 stdlib (`scripts/pipeline.py`), unittest/pytest, Quarto (the fixture renders a real PDF), `claude -p` live evals under `tests/evals/`.

**Spec:** `docs/improvement-ledger.md` row L-005. The option it offered of granting Bash is **rejected** under `rules/agents.md` §2 (read in full, 2026-09-29): writer-critic's `Bash` was removed on purpose, and nothing may restore it.

## Evidence this plan argues from (all read in full, 2026-09-29)

- `agents/writer-critic.md`: `tools: Read, Grep, Glob`. It has no Bash.
- `skills/review/templates/manuscript-review-8-categories.md` §6 tells the critic to *run* `quarto render` (-20 on fail, -3 per warning, -3 per unresolved ref) and *run* `prose_number_check.py` (-10 per hardcoded value). The critic can do neither.
- `skills/write/SKILL.md` step 5 and the humanize paragraph, the Comprehensive and `--proofread` routes in `skills/review/SKILL.md`, and step 5 of `skills/revise/SKILL.md` all dispatch writer-critic. None of them passes it a render log.
- `skills/review/templates/manuscript-review-conceptual.md` §6 (Build) has the same defect.
- `scripts/pipeline.py`: `do_render()` and the `prose-check` predicate already run these commands. `render` skips when fresh, which leaves no log for a critic to count warnings from.
- `seeds/gitignore` ignores `*.log`, so the new logs are session mechanics and never enter a project's git history. `hooks/protect-files.sh` guards `*-critic_*.md`, not `.log`.

## Global Constraints

- **Branch first.** Edits to `agents/`, `skills/`, `rules/` and `scripts/` are live in all six paper repos the moment they are saved (`CLAUDE.md`). Work in a worktree on branch `writer-critic-inputs`. Paper repos link to the main checkout, so worktree edits stay unseen until the merge.
- **writer-critic's frontmatter stays `tools: Read, Grep, Glob`.** A test in Task 2 enforces this.
- **Never put a time limit on a live eval.** Leave `EVAL_TIMEOUT` unset (`CLAUDE.md`, user ruling 2026-09-25).
- Nothing project-specific in `agents/ skills/ rules/ hooks/ templates/`. `./scripts/check_fork.sh` must exit 0 before every commit that touches them.
- No arrow notation pairing a creator with its critic in any `.md` under `rules/`, `skills/` or `agents/` (e.g. `writer → writer-critic`). `pipeline.py registry check` [registry-authority] fails on it.
- Quiet output: redirect long test/render/eval logs to the scratchpad and print only the exit status and failure lines.
- End every commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Out of scope (deliberately)

- **A pandoc build for Markdown manuscripts.** `declared_manuscript()` accepts only `.qmd`. A conceptual-review `.md` manuscript therefore gets Build NOT SCORED, which the report says visibly. Wiring a pandoc build is a separate change.
- **L-004** (configurable exhibit-label glob): separate ledger row, separate plan.
- The hard gate is unchanged. `pipeline.py post writer` already runs `render` and `prose-check` itself (writer `produces:` in `rules/registry.yaml`). This plan fixes the *scored* category, not the gate.

---

### Task 0: Worktree

- [ ] **Step 1:** Create the worktree and branch with `superpowers:using-git-worktrees`. Branch name: `writer-critic-inputs`, off `main` at or after `ef0e1c8`.
- [ ] **Step 2:** Baseline: `python3 -m pytest tests/ -q > "$SCRATCH/baseline.log" 2>&1; echo $?; tail -1 "$SCRATCH/baseline.log"`. Expected: exit 0, `562 passed`. Record the count.

---

### Task 1: `pipeline.py critic-inputs`

**Files:**
- Modify: `scripts/pipeline.py` (`do_render` ~l.281, `prose-check` branch of `evaluate` ~l.389, `main` ~l.554)
- Test: `tests/test_pipeline.py` (new class `TestCriticInputs`, placed before the `if __name__` line at l.772)

**Interfaces:**
- Produces: CLI `python3 .claude/scripts/pipeline.py critic-inputs`. Its last stdout line is exactly `critic-inputs: quality_reports/critic_inputs/writer-critic_<YYYY-MM-DD_HHMMSS>[_N].log`. It exits 0 whenever the log was written. The log has three `## ` sections, in order: `## quarto render <ms> — exit <n>`, `## prose_number_check.py <ms> — exit <n>|skipped: …`, `## check_render.py … — exit <n>|skipped: …`.
- Produces (internal): `run_render(root, target) -> Tuple[int, str]`, `run_script(root, name, *args) -> Tuple[Optional[int], str]`, `critic_inputs(root) -> int`.

- [ ] **Step 1: Write the failing tests.** Add to `tests/test_pipeline.py`, before `if __name__ == "__main__": unittest.main()`:

```python
class TestCriticInputs(FixtureCase):
    """`critic-inputs` (ledger L-005): writer-critic has no Bash (.claude/rules/agents.md §2), so
    the dispatching skill runs the mechanical checks its Render category scores and hands it the
    log. The log must exist even when the render fails — a failed render is the finding."""
    def setUp(self):
        super().setUp()
        os.symlink(ROOT / "scripts" / "check_render.py", self.t / ".claude" / "scripts" / "check_render.py")
    def _log(self, out):
        last = out.strip().splitlines()[-1]
        self.assertTrue(last.startswith("critic-inputs: quality_reports/critic_inputs/writer-critic_"), out)
        p = self.t / last.split(": ", 1)[1]; self.assertTrue(p.is_file(), out); return p.read_text()

    def test_clean_fixture_logs_all_three_sections(self):
        rc, out = run("critic-inputs", root=self.t); self.assertEqual(rc, 0, out)
        log = self._log(out)
        self.assertIn("## quarto render manuscript_fixture.qmd — exit 0", log)
        self.assertIn("## prose_number_check.py manuscript_fixture.qmd — exit 0", log)
        self.assertIn("## check_render.py", log)

    def test_renders_even_when_the_output_is_fresh(self):
        """`render` the predicate skips a fresh manuscript; the critic counts WARNINGs, so this
        must not — a skipped render leaves nothing to count."""
        subprocess.run(["quarto", "render", "manuscript_fixture.qmd"], cwd=self.t, capture_output=True)
        self.assertEqual(run("fresh", root=self.t)[0], 0)
        rc, out = run("critic-inputs", root=self.t); self.assertEqual(rc, 0, out)
        self.assertIn("Output created", self._log(out))

    def test_a_failed_render_still_writes_the_log_and_skips_the_page_check(self):
        ms = self.t / "manuscript_fixture.qmd"
        ms.write_text(ms.read_text() + '\n```{r}\n#| label: boom\nstop("critic-inputs test")\n```\n')
        rc, out = run("critic-inputs", root=self.t); self.assertEqual(rc, 0, out)
        log = self._log(out)
        self.assertRegex(log, r"## quarto render manuscript_fixture\.qmd — exit [1-9]")
        self.assertIn("skipped: render failed", log)

    def test_a_typed_prose_number_is_in_the_log(self):
        ms = self.t / "manuscript_fixture.qmd"
        ms.write_text(ms.read_text() + "\n\nThe effect is 0.42 points.\n")
        rc, out = run("critic-inputs", root=self.t); self.assertEqual(rc, 0, out)
        self.assertRegex(self._log(out), r"## prose_number_check\.py manuscript_fixture\.qmd — exit [1-9]")

    def test_two_runs_never_share_a_log(self):
        rc1, out1 = run("critic-inputs", root=self.t); rc2, out2 = run("critic-inputs", root=self.t)
        self.assertEqual((rc1, rc2), (0, 0))
        self.assertNotEqual(out1.strip().splitlines()[-1], out2.strip().splitlines()[-1])
        self.assertEqual(len(list((self.t / "quality_reports" / "critic_inputs").glob("*.log"))), 2)
```

- [ ] **Step 2: Run them and confirm they fail.**
  Run: `python3 -m pytest tests/test_pipeline.py -q -k CriticInputs 2>&1 | tail -5`
  Expected: 5 failures, argparse `invalid choice: 'critic-inputs'`.

- [ ] **Step 3: Implement.** In `scripts/pipeline.py`:

  (a) Replace the body of `do_render` so it goes through a shared runner. Keep the docstring:

```python
def run_render(root: Path, target: Path) -> Tuple[int, str]:
    """`quarto render <target>` from the project root: (exit code, stdout + stderr)."""
    p = subprocess.run(["quarto", "render", str(target.relative_to(root))], cwd=root, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

def do_render(root: Path, target: Path) -> Tuple[bool, str]:
    """...existing docstring, unchanged..."""
    rc, out = run_render(root, target)
    lines = out.strip().splitlines()
    if rc != 0:
        return False, lines[-1] if lines else ""
    warn = RENDER_WARNING_RE.search(out)
    if warn:
        return False, f"exit 0 but {warn.group(0).strip()}"
    return True, ""
```

  (b) Add, directly after `do_render`:

```python
def run_script(root: Path, name: str, *args: str) -> Tuple[Optional[int], str]:
    """A linked `.claude/scripts/<name>` run from the project root: (exit code, stdout + stderr),
    or (None, why) when the project does not link it."""
    script = root / ".claude" / "scripts" / name
    if not script.exists(): return None, f".claude/scripts/{name} not linked"
    p = subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

CRITIC_INPUTS_REL = Path("quality_reports") / "critic_inputs"

def critic_inputs(root: Path) -> int:
    """The mechanical half of writer-critic's Render category (ledger L-005). The critic has no
    Bash — `.claude/rules/agents.md` §2 removed it on purpose — so the dispatching skill runs
    this and names the log in the dispatch. Always renders: the category counts WARNINGs, and a
    render skipped as fresh leaves nothing to count. Exit 0 whenever the log is written: a
    failing render or a typed number is a finding for the critic to score, not a reason to
    withhold the log. `*.log` is gitignored by the seeded .gitignore — session mechanics."""
    ms = declared_manuscript(root); rel = str(ms.relative_to(root))
    d = root / CRITIC_INPUTS_REL; d.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    log = d / f"writer-critic_{stamp}.log"; n = 2
    while log.exists(): log = d / f"writer-critic_{stamp}_{n}.log"; n += 1
    parts = [f"# critic-inputs: {rel} at {now()}"]; summary = []
    rrc, out = run_render(root, ms)
    parts.append(f"## quarto render {rel} — exit {rrc}\n{out.rstrip()}"); summary.append(f"render exit {rrc}")
    prc, out = run_script(root, "prose_number_check.py", rel)
    parts.append(f"## prose_number_check.py {rel} — " + (f"skipped: {out}" if prc is None else f"exit {prc}\n{out.rstrip()}"))
    summary.append("prose-check " + ("skipped" if prc is None else f"exit {prc}"))
    pdf = ms.with_suffix(".pdf")
    if rrc != 0:
        why = "render failed — any PDF on disk predates this run"
    elif not pdf.exists():
        why = f"no {pdf.name} (not a PDF render)"
    else:
        why = None
    if why:
        parts.append(f"## check_render.py — skipped: {why}"); summary.append("check_render skipped")
    else:
        crc, out = run_script(root, "check_render.py", str(pdf.relative_to(root)))
        parts.append(f"## check_render.py {pdf.name} — " + (f"skipped: {out}" if crc is None else f"exit {crc}\n{out.rstrip()}"))
        summary.append("check_render " + ("skipped" if crc is None else f"exit {crc}"))
    log.write_text("\n\n".join(parts) + "\n")
    print(" · ".join(summary)); print(f"critic-inputs: {log.relative_to(root)}"); return 0
```

  (c) In `evaluate`, replace the `prose-check` branch with the shared runner. The message text stays as it was:

```python
    if t == "prose-check":
        rc, out = run_script(root, "prose_number_check.py", str(ctx.ms.relative_to(root)))
        if rc is None: return False, "prose-check: " + out
        return rc == 0, "prose_number_check.py exit " + str(rc)
```

  (d) In `main`: change `sub.add_parser("manuscript"); sub.add_parser("fresh"); sub.add_parser("next")` to also add `sub.add_parser("critic-inputs")`. After the `if a.cmd == "fresh":` block, add `if a.cmd == "critic-inputs": return critic_inputs(root)`.

- [ ] **Step 4: Run the new tests, then the whole file.**
  Run: `python3 -m pytest tests/test_pipeline.py -q > "$SCRATCH/t1.log" 2>&1; echo $?; tail -3 "$SCRATCH/t1.log"`
  Expected: exit 0. If `test_a_typed_prose_number_is_in_the_log` still passes the prose check, read `scripts/prose_number_check.py` in full to find the literal shape it flags. Change the test sentence to that shape. Do not weaken the assertion.
  If `pdftotext` is missing on the machine, `check_render.py` exits 2. The log then records `exit 2` and the tests still pass, because they only assert the section header.

- [ ] **Step 5:** Read `rules/lifecycle.md` in full. If it lists `pipeline.py` subcommands, add one line: `critic-inputs — renders the declared manuscript, runs prose_number_check.py and check_render.py, writes quality_reports/critic_inputs/writer-critic_<stamp>.log for the writer-critic dispatch (always renders; exit 0 once the log is written)`.

- [ ] **Step 6: Commit.**
```bash
./scripts/check_fork.sh >/dev/null && git add scripts/pipeline.py tests/test_pipeline.py rules/lifecycle.md && git commit -m "feat(pipeline): critic-inputs renders and checks for a Bash-less writer-critic (L-005)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The critic reads the log, or says NOT SCORED

**Files:**
- Modify: `skills/review/templates/manuscript-review-8-categories.md` (§6 and the Report Format `## Render:` line)
- Modify: `skills/review/templates/manuscript-review-conceptual.md` (§6)
- Modify: `agents/writer-critic.md` (Resources list). Frontmatter **unchanged**.
- Modify: `rules/agents.md` §2 (one new paragraph after the one ending "…so that tool is now removed. The model is … orchestrates report-saving.\"*")
- Create: `tests/test_writer_critic_inputs.py`

**Interfaces:**
- Consumes: the Task 1 log path shape `quality_reports/critic_inputs/writer-critic_<stamp>.log` and its three section headers.
- Produces: the NOT SCORED wording `## Render: NOT SCORED — no critic-inputs log in the dispatch`. Task 3's skill text refers to it.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_writer_critic_inputs.py`:

```python
"""Ledger L-005: writer-critic scores a Render category it cannot run. The fix hands it a log
(`pipeline.py critic-inputs`) rather than a tool: .claude/rules/agents.md §2 removed its Bash on
purpose. These are contracts over the shipped text, so the fix cannot quietly drift back."""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
def read(rel): return (ROOT / rel).read_text()
def section(text, n):
    m = re.search(rf"^## {n}\. .*?(?=^## |\Z)", text, re.M | re.S); return m.group(0) if m else ""

EIGHT = "skills/review/templates/manuscript-review-8-categories.md"
CONCEPTUAL = "skills/review/templates/manuscript-review-conceptual.md"


class TestWriterCriticStaysWithoutBash(unittest.TestCase):
    def test_tools_line_has_no_bash(self):
        front = read("agents/writer-critic.md").split("---")[1]
        tools = re.search(r"^tools:\s*(.*)$", front, re.M).group(1)
        self.assertNotIn("Bash", tools, "rules/agents.md §2: writer-critic's Bash was removed on purpose")

    def test_agent_names_the_dispatched_log(self):
        self.assertIn("critic-inputs", read("agents/writer-critic.md"))

    def test_the_rule_names_the_mechanism(self):
        self.assertIn("critic-inputs", read("rules/agents.md"))


class TestRenderIsScoredFromTheLog(unittest.TestCase):
    def test_render_category_reads_the_log_and_runs_nothing(self):
        s = section(read(EIGHT), 6)
        self.assertIn("critic-inputs", s)
        self.assertIn("NOT SCORED", s)
        self.assertNotRegex(s, r"Run\s+`python3", "a Bash-less critic cannot run a script")
        self.assertNotIn("Does `quarto render", s)

    def test_report_format_allows_not_scored(self):
        self.assertIn("## Render: [PASS/WARNINGS/FAIL/NOT SCORED]", read(EIGHT))

    def test_conceptual_build_is_scored_from_a_log(self):
        s = section(read(CONCEPTUAL), 6)
        self.assertIn("NOT SCORED", s)
        self.assertIn("critic-inputs", s)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and confirm failure.** `python3 -m pytest tests/test_writer_critic_inputs.py -q 2>&1 | tail -3`. Expected: 5 failed, 1 passed (`test_tools_line_has_no_bash` already holds).

- [ ] **Step 3: Rewrite §6 of `manuscript-review-8-categories.md`.** Replace everything from `## 6. Render` up to (not including) `## 7. Voice Fidelity` with:

```markdown
## 6. Render

**You run nothing.** You have no Bash (`.claude/rules/agents.md` §2). The dispatching skill runs
`python3 .claude/scripts/pipeline.py critic-inputs` immediately before dispatching you and names
the log it wrote — `quality_reports/critic_inputs/writer-critic_<stamp>.log` — in your prompt.
Read that log in full. It has three sections: `quarto render`, `prose_number_check.py` and
`check_render.py` (the page check on the rendered PDF; skipped for a non-PDF or failed render).

- Render section exit ≠ 0: -20
- Each `WARNING` line in the render section that is not a cross-reference warning: -3
- Each unresolved cross-reference: -3. Count from check_render's `UNRESOLVED:` lines when that
  section ran, otherwise from the render section's "Unable to resolve crossref" warnings — never
  both for the same reference.
- Each `@key` cited in the manuscript but absent from `references.bib` (Grep the source): -3
- Each hardcoded value `prose_number_check.py` lists: -10 (INV-11). A clean render proves the
  inline expressions *evaluated*, never that a typed literal is right.

**No log named in your prompt, or the named file does not exist:** report
`## Render: NOT SCORED — no critic-inputs log in the dispatch`, deduct nothing in this category,
and make that the first line under Score Breakdown so the dispatching session sees it. Never infer
a render result from the source, and never ask for Bash.

```

  In Report Format, change `## Render: [PASS/WARNINGS/FAIL]` to `## Render: [PASS/WARNINGS/FAIL/NOT SCORED]`.

- [ ] **Step 4: Rewrite §6 of `manuscript-review-conceptual.md`.** Replace from `## 6. Build (replaces Render)` up to `## 7. Voice Fidelity` with:

```markdown
## 6. Build (replaces Render)
Scored only from the build log named in your dispatch — for a `.qmd` manuscript, the
`pipeline.py critic-inputs` log (`manuscript-review-8-categories.md` § 6 says how to read it). You
run nothing.
- The declared build exits 0; every figure resolves.
- The profile's word definition is met, counted by the project's word-count gate if one exists
  (its output comes in the dispatch too, or the count is NOT SCORED).
No log named → `## Build: NOT SCORED — no build log in the dispatch`, no deduction, first line
under Score Breakdown. `critic-inputs` builds only the declared `.qmd`; a Markdown manuscript's
pandoc build is not wired, so its Build is NOT SCORED until it is.

```

- [ ] **Step 5: `agents/writer-critic.md`.** In `## Resources`, after the `- Format:` bullet, add:

```markdown
- Render inputs: the `pipeline.py critic-inputs` log named in your dispatch — category 6 is scored from it and nothing else. You have no Bash and run no build; no log → Render NOT SCORED (8-categories template § 6)
```

- [ ] **Step 6: `rules/agents.md` §2.** Insert this paragraph after the one ending with the civilize-auditor quotation (`…the skill orchestrates report-saving."*`) and before `**Every returned report is saved the instant it comes back`:

```markdown
**Mechanical inputs come from the dispatching skill, not from a tool grant.** Where a critic's
rubric scores something only a command can establish — writer-critic's Render category — the
skill runs `python3 .claude/scripts/pipeline.py critic-inputs` immediately before the dispatch
and names the log path in the prompt; with no log the critic reports the category NOT SCORED
rather than guessing. Giving the critic `Bash` to run the build itself is ruled out: a reviewer
with a shell can write any file through it, which is what withholding `Write` exists to prevent.
```

- [ ] **Step 7: Run the tests, the registry check and the fork check.**
  `python3 -m pytest tests/test_writer_critic_inputs.py -q 2>&1 | tail -2; python3 scripts/pipeline.py --root . registry check | grep -v PASS; ./scripts/check_fork.sh >/dev/null; echo fork=$?`
  Expected: 6 passed; no non-PASS registry lines; `fork=0`.

- [ ] **Step 8: Commit.**
```bash
git add skills/review/templates/manuscript-review-8-categories.md skills/review/templates/manuscript-review-conceptual.md agents/writer-critic.md rules/agents.md tests/test_writer_critic_inputs.py && git commit -m "fix(writer-critic): score Render from the dispatched critic-inputs log; NOT SCORED without one (L-005)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Every dispatch site runs `critic-inputs`

**Files:**
- Modify: `skills/write/SKILL.md` (step 5, ~l.68–71; humanize paragraph, ~l.119)
- Modify: `skills/review/SKILL.md` (a lead paragraph under `## Mode Details`, ~l.37; Comprehensive item 2, ~l.42)
- Modify: `skills/revise/SKILL.md` (step 5 bullets, ~l.71–72)
- Modify: `tests/test_writer_critic_inputs.py` (add a class)

**Interfaces:**
- Consumes: the Task 1 CLI and its `critic-inputs: <path>` last line, and the Task 2 NOT SCORED wording.

- [ ] **Step 1: Write the failing test.** Append to `tests/test_writer_critic_inputs.py`, above `if __name__`:

```python
class TestEveryDispatchSiteRunsCriticInputs(unittest.TestCase):
    SITES = {"skills/write/SKILL.md": 2, "skills/review/SKILL.md": 1, "skills/revise/SKILL.md": 1}

    def test_each_known_site(self):
        for rel, n in self.SITES.items():
            self.assertGreaterEqual(read(rel).count("pipeline.py critic-inputs"), n, rel)

    def test_no_unlisted_skill_dispatches_writer_critic(self):
        for f in sorted((ROOT / "skills").rglob("SKILL.md")):
            rel = str(f.relative_to(ROOT))
            if re.search(r"[Dd]ispatch\w*\W{0,4}(\*\*)?writer-critic", f.read_text()):
                self.assertIn(rel, self.SITES, f"{rel} dispatches writer-critic without being a known critic-inputs site")
```

- [ ] **Step 2: Run and confirm failure.** `python3 -m pytest tests/test_writer_critic_inputs.py -q -k DispatchSite 2>&1 | tail -3`. Expected: `test_each_known_site` fails on `skills/write/SKILL.md`. If `test_no_unlisted_skill_dispatches_writer_critic` flags another file, read that file in full. If it really dispatches writer-critic, add the same step there and add it to `SITES`. Never loosen the regex to make it pass.

- [ ] **Step 3: `skills/write/SKILL.md` step 5.** Directly under `#### 5. Dispatch writer-critic (every mode that touches prose)`, before `Dispatch **writer-critic** in section mode.`, insert:

```markdown
Run `python3 .claude/scripts/pipeline.py critic-inputs` first. It renders the manuscript, runs the
prose-number and page checks, and prints the log path on its last line
(`critic-inputs: quality_reports/critic_inputs/writer-critic_<stamp>.log`); name that path in the
dispatch prompt. writer-critic has no Bash and scores Render (category 6) from that log only
(`.claude/rules/agents.md` §2). A failing render inside an exit-0 log is normal — the critic
scores it; do not fix and re-run before dispatching.
```

  In the humanize paragraph, change `After the cleanup pass, dispatch **writer-critic** in **proofread mode**` to `After the cleanup pass, run `python3 .claude/scripts/pipeline.py critic-inputs` and dispatch **writer-critic** in **proofread mode** with the log path it prints (as in step 5)`.

- [ ] **Step 4: `skills/review/SKILL.md`.** Directly under `## Mode Details`, before `### Comprehensive Review`, insert:

```markdown
**Every route that dispatches writer-critic** (Comprehensive, `--proofread`, `--all`) first runs
`python3 .claude/scripts/pipeline.py critic-inputs` and names the log path it prints in the
writer-critic dispatch prompt. writer-critic has no Bash; it scores Render (category 6) from that
log only (`.claude/rules/agents.md` §2). In Comprehensive mode run it before the first
`git status --porcelain`, so its render can never read as a verifier tree change.
```

  In Comprehensive item 2, change `2. **writer-critic** — manuscript polish (6 categories).` to `2. **writer-critic** — manuscript polish (6 categories), with the critic-inputs log path in its prompt.`

- [ ] **Step 5: `skills/revise/SKILL.md` step 5.** Replace the first two bullets:

```markdown
- CLARIFICATION/REWRITE → dispatch writer; run `python3 .claude/scripts/pipeline.py critic-inputs`; dispatch writer-critic naming the log path it prints (it has no Bash and scores Render from that log — `.claude/rules/agents.md` §2); record the score
- NEW ANALYSIS → after user approval dispatch coder, then coder-critic; record the score. Then dispatch writer, run `critic-inputs`, and dispatch writer-critic with its log path for the affected section; record the score.
```

  Keep the two indented `record-score` sub-bullets under NEW ANALYSIS as they are.

- [ ] **Step 6: Run the file, the revise contracts and the fork check.**
  `python3 -m pytest tests/test_writer_critic_inputs.py tests/test_revise_contracts.py -q 2>&1 | tail -2; ./scripts/check_fork.sh >/dev/null; echo fork=$?`
  Expected: all pass; `fork=0`.

- [ ] **Step 7: Commit.**
```bash
git add skills/write/SKILL.md skills/review/SKILL.md skills/revise/SKILL.md tests/test_writer_critic_inputs.py && git commit -m "fix(skills): run critic-inputs before every writer-critic dispatch and pass its log (L-005)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Evals assert the mechanism

**Files:**
- Modify: `tests/evals/check_write.py`, `tests/evals/check_review.py`
- Modify: `tests/test_eval_write.py`, `tests/test_eval_review.py`

**Interfaces:**
- Consumes: `evallib.first`, `evallib.agent`, and `tool_uses` entries of the form `(name, input, id)`. An Agent input carries `prompt`.

- [ ] **Step 1: Write the failing checker tests.** Replace the transcript `T` in `tests/test_eval_write.py` and the tests that index into it, and add two tests:

```python
CHECK = ROOT / "tests" / "evals" / "check_write.py"
LOGP = "quality_reports/critic_inputs/writer-critic_2026-09-29_120000.log"
T = (use("u1", "Bash", command="python3 .claude/scripts/pipeline.py manuscript")
     + use("u2", "Agent", subagent_type="writer", prompt="x")
     + use("c1", "Bash", command="python3 .claude/scripts/pipeline.py critic-inputs")
     + use("u3", "Agent", subagent_type="writer-critic", prompt=f"section mode; render inputs: {LOGP}")
     + use("u4", "Write", file_path="/p/quality_reports/reviews/writer-critic_2026-09-25.md", content="r")
     + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score manuscript 88 --critic writer-critic --deductions 12 --report quality_reports/reviews/writer-critic_2026-09-25.md --scope section:Conclusion"))


class TestWriteChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p", 0); self.assertEqual(rc, 0, out)

    def test_dispatch_before_resolve_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + "".join(lines[2:]), "/p", 0); self.assertEqual(rc, 1); self.assertIn("before the manuscript was resolved", out)

    def test_unscoped_score_fails(self):
        rc, out = go(CHECK, T.replace(" --scope section:Conclusion", ""), "/p", 0); self.assertEqual(rc, 1); self.assertIn("not scoped", out)

    def test_score_before_report_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:4]) + lines[5] + lines[4], "/p", 0); self.assertEqual(rc, 1); self.assertIn("not Written before", out)

    def test_prose_check_red_fails(self):
        rc, out = go(CHECK, T, "/p", 1); self.assertEqual(rc, 1); self.assertIn("prose_number_check exited 1", out)

    def test_no_critic_inputs_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:2] + lines[3:]), "/p", 0); self.assertEqual(rc, 1); self.assertIn("critic-inputs` never ran", out)

    def test_dispatch_without_the_log_path_fails(self):
        rc, out = go(CHECK, T.replace(f"render inputs: {LOGP}", "no log"), "/p", 0); self.assertEqual(rc, 1); self.assertIn("does not name a critic_inputs/ log", out)
```

  In `tests/test_eval_review.py`, replace `T` and the two tests that match on the writer-critic `use(...)` string, and add two tests:

```python
LOGP = "quality_reports/critic_inputs/writer-critic_2026-09-29_120000.log"
WC = use("u3", "Agent", subagent_type="writer-critic", prompt=f"render inputs: {LOGP}")
CI = use("c1", "Bash", command="python3 .claude/scripts/pipeline.py critic-inputs")
T = (CI + use("u1", "Bash", command="git status --porcelain")
     + use("u2", "Agent", subagent_type="strategist-critic", prompt="x") + WC + use("u4", "Agent", subagent_type="verifier", prompt="x")
     + use("u5", "Bash", command="git status --porcelain")
     + use("w1", "Write", file_path="/p/quality_reports/reviews/strategist-critic_d.md", content="r") + rec("strategy", "strategist-critic", "quality_reports/reviews/strategist-critic_d.md")
     + use("w2", "Write", file_path="/p/quality_reports/reviews/writer-critic_d.md", content="r") + rec("manuscript", "writer-critic", "quality_reports/reviews/writer-critic_d.md")
     + use("w3", "Write", file_path="/p/quality_reports/verification_report.md", content="r") + rec("replication", "verifier", "quality_reports/verification_report.md"))
```

  Change `test_missing_critic_fails` to `T.replace(WC, "")`, and add inside `TestReviewChecker`:

```python
    def test_no_critic_inputs_fails(self):
        rc, out = go(CHECK, T.replace(CI, ""), "/p"); self.assertEqual(rc, 1); self.assertIn("critic-inputs` never ran", out)

    def test_dispatch_without_the_log_path_fails(self):
        rc, out = go(CHECK, T.replace(f"render inputs: {LOGP}", "x"), "/p"); self.assertEqual(rc, 1); self.assertIn("does not name a critic_inputs/ log", out)
```

  `test_pool_read_in_subagent_passes` uses parent `"u3"`, which still names the writer-critic dispatch. Leave it unchanged.

- [ ] **Step 2: Run and confirm the new tests fail.** `python3 -m pytest tests/test_eval_write.py tests/test_eval_review.py -q 2>&1 | tail -3`. Expected: the four new tests fail and the rest pass.

- [ ] **Step 3: Checkers.** In `tests/evals/check_write.py`, after the `elif w is not None and c < w:` line, add:

```python
ci = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"pipeline\.py\s+critic-inputs\b", a.get("command", "")))
if ci is None: fails.append("`pipeline.py critic-inputs` never ran")
elif c is not None and ci > c: fails.append("critic-inputs ran after writer-critic was dispatched")
if c is not None and "critic_inputs/" not in str(uses[c][1].get("prompt", "")): fails.append("the writer-critic dispatch does not name a critic_inputs/ log")
```

  and extend its docstring's first sentence with `; critic-inputs runs before writer-critic and its log path is in the dispatch prompt`.

  In `tests/evals/check_review.py`, after the `for a, i in d.items():` loop, add the same four lines with `c = d["writer-critic"]` defined first:

```python
c = d["writer-critic"]
ci = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"pipeline\.py\s+critic-inputs\b", a.get("command", "")))
if ci is None: fails.append("`pipeline.py critic-inputs` never ran")
elif c is not None and ci > c: fails.append("critic-inputs ran after writer-critic was dispatched")
if c is not None and "critic_inputs/" not in str(uses[c][1].get("prompt", "")): fails.append("the writer-critic dispatch does not name a critic_inputs/ log")
```

  Extend its docstring the same way. `c` is unused elsewhere in `check_review.py`, so there is no shadowing.

- [ ] **Step 4: Run the checker tests.** `python3 -m pytest tests/test_eval_write.py tests/test_eval_review.py -q 2>&1 | tail -2`. Expected: all pass.

- [ ] **Step 5: Commit.**
```bash
git add tests/evals/check_write.py tests/evals/check_review.py tests/test_eval_write.py tests/test_eval_review.py && git commit -m "test(evals): /write and /review must run critic-inputs and pass its log to writer-critic (L-005)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Live evals — no timeout.** Run each on its own, from the worktree, with `EVAL_TIMEOUT` unset. Run in the background and wait for completion; never kill a slow run.
  `bash tests/evals/write.sh > "$SCRATCH/eval-write.log" 2>&1; echo write=$?; tail -8 "$SCRATCH/eval-write.log"`
  `bash tests/evals/review.sh > "$SCRATCH/eval-review.log" 2>&1; echo review=$?; tail -8 "$SCRATCH/eval-review.log"`
  Expected: both `PASS`. On a red, read the kept `$E/eval.stream.jsonl`. Find the writer-critic dispatch and its category 6 text. Decide whether the skill text or the checker is wrong, and fix whichever it is. Report a red that turns out to be about the skill, not the harness, as a finding, the same way `docs/plans/2026-09-25-remaining-skill-evals.md` did. Also open the saved `writer-critic_*.md` report in `$E/quality_reports/reviews/`. Confirm its `## Render:` line is scored from the log (PASS/WARNINGS/FAIL), not NOT SCORED.

---

### Task 5: Verify, merge, close out

- [ ] **Step 1: Full gates on the branch.**
  `python3 -m pytest tests/ -q > "$SCRATCH/full.log" 2>&1; echo $?; tail -1 "$SCRATCH/full.log"; ./scripts/check_fork.sh >/dev/null; echo fork=$?`
  Expected: exit 0, and the pass count equals the Task 0 baseline plus the new tests (5 in `test_pipeline.py` + 8 in `test_writer_critic_inputs.py` + 4 checker tests = 17). `fork=0`.
- [ ] **Step 2: Merge.** `superpowers:finishing-a-development-branch`, `--no-ff` into `main`. On `main`: re-run step 1 and `./scripts/check_install.sh --all >/dev/null; echo install=$?`. Expected: `install=0`. No file was added under `agents/ skills/ rules/ hooks/`, so no re-link is needed. Edits reach all six paper repos through the links on merge.
- [ ] **Step 3: Close the ledger row.** Read `scripts/ledger.py` in full. If it has a status/land operation, use it. Otherwise edit L-005's status cell in `docs/improvement-ledger.md` to `landed <merge-sha>`, the same way L-007 was closed in `9c2ce0c`.
- [ ] **Step 4: Session report.** Append a `## 2026-09-29 — writer-critic render inputs (L-005)` entry to `docs/SESSION_REPORT.md`, in the house format. It must cover:
  - Scope.
  - The rejected Bash option and why.
  - The commits.
  - Test counts.
  - Both live-eval results.
  - Out-of-scope items: the `.md` build and L-004.
  - One line recording `ef0e1c8` (hooks through `run-hook.sh`; critic-pairing across sessions), which landed 2026-09-29 without an entry. The fleet is at that lock, with `run-hook.sh` tracked in all six repos (checked 2026-09-29).
- [ ] **Step 5: Pointer.** In `CLAUDE.md` § Start here, change `**Open in this repo:** rows L-004 and L-005 in docs/improvement-ledger.md.` to name L-004 only, and mention that L-005 closed under this plan. Set this plan's `**Status:**` line to `complete (2026-09-29)` with the merge sha.
- [ ] **Step 6: Commit docs**, then ask the user before pushing.
```bash
git add docs/improvement-ledger.md docs/SESSION_REPORT.md CLAUDE.md docs/plans/2026-09-29-writer-critic-render-inputs.md && git commit -m "docs: L-005 closed (writer-critic render inputs); record ef0e1c8

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
