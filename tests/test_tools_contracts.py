"""Contracts for /tools."""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "tools" / "SKILL.md").read_text()


def section(name):
    i = SKILL.index(f"### `/tools {name}")
    j = SKILL.index("\n### ", i + 1) if "\n### " in SKILL[i + 1:] else len(SKILL)
    return SKILL[i:j]


class TestTools(unittest.TestCase):
    def test_render_resolves_the_declared_manuscript(self):
        s = section("render")
        self.assertIn("pipeline.py manuscript", s)
        self.assertNotIn("manuscript_<project>.qmd", s)

    def test_every_advertised_subcommand_has_a_command_or_an_explicit_pointer(self):
        """`learn` is deliberately a pointer at meta-governance; every other subcommand the
        argument-hint advertises needs a command block. `context` was deleted 2026-09-24: the
        hook that computes context usage needs a transcript_path only the harness supplies,
        and Claude Code's built-in /context already reports the real figure."""
        hint = re.search(r"argument-hint:.*?\[subcommand:\s*([^\]]+)\]", SKILL).group(1)
        names = [n.strip() for n in hint.split("|")]
        self.assertNotIn("context", names)
        stepless = [n for n in names if n != "learn" and "```" not in section(n)]
        self.assertEqual([], stepless)

    def test_no_bundled_resources_catalogue(self):
        self.assertNotIn("## Bundled Resources", SKILL)

    def test_journal_is_appended_from_the_state_not_regenerated(self):
        """rules/logging.md: append only, one entry per agent invocation, derived from the
        state file — never the reverse, and never a source for where the pipeline starts."""
        s = section("journal")
        self.assertIn("research_journal.md", s)
        self.assertIn("pipeline_state.json", s)
        self.assertNotRegex(s, r"(?i)regenerate")
        self.assertIn("pipeline.py next", s)


class TestCommitConfirmationGates(unittest.TestCase):
    """Audit 2026-09-15 P4: `/tools commit` had no confirmation before commit or before
    PR/merge. Two binary gates, each honouring --yes so a driver can pass through; --yes
    never skips Step 0's blocking checks, which are safety gates, not HITL waits."""

    def setUp(self):
        self.s = section("commit")

    def test_yes_is_advertised(self):
        self.assertIn("--yes", re.search(r"argument-hint:.*", SKILL).group(0))
        self.assertIn("--yes", self.s)

    def test_a_wait_precedes_the_commit_and_another_precedes_the_pr(self):
        # Gate A sits between staging (step 3) and `git commit` (step 4)
        i_stage = self.s.index("Stage named files")
        i_commit = self.s.index("git commit")
        gate_a = self.s[i_stage:i_commit]
        self.assertRegex(gate_a, r"(?i)wait|confirm")
        # Gate B sits between the commit and `gh pr create`
        i_pr = self.s.index("gh pr create")
        gate_b = self.s[i_commit:i_pr]
        self.assertRegex(gate_b, r"(?i)wait|confirm")

    def test_yes_does_not_skip_step_zero(self):
        self.assertRegex(self.s, r"--yes[^\n]*(never|does not|not)[^\n]*Step 0|Step 0[^\n]*(never|not)[^\n]*--yes")


if __name__ == "__main__":
    unittest.main()
