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


class TestCriticInputsSourceSection(unittest.TestCase):
    def test_critic_inputs_has_source_section(self):
        import sys, tempfile, shutil, os, io, contextlib
        from unittest import mock
        sys.path.insert(0, str(ROOT / "scripts"))
        import pipeline
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            (tmp / "CLAUDE.md").write_text("manuscript: paper.qmd\n")
            (tmp / "paper.qmd").write_text('A claim [about a rule]{.src ref="nope" id="t9"} here.\n')
            (tmp / ".claude").mkdir()
            (tmp / ".claude" / "scripts").symlink_to(ROOT / "scripts")
            buf = io.StringIO()
            with mock.patch.object(pipeline, "run_render", return_value=(0, "ok\n")), contextlib.redirect_stdout(buf):
                self.assertEqual(pipeline.critic_inputs(tmp), 0)
            log = next((tmp / "quality_reports" / "critic_inputs").glob("*.log")).read_text()
            self.assertRegex(log, r"## source_check\.py \d+ ms — exit 0\n")
            self.assertIn("source-check: FAILED t9", log)
            self.assertRegex(buf.getvalue(), r"source-check [1-9]\d* warnings")
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
