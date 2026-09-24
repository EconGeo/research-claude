"""Contracts for /tools.

A documented default that disagrees with the script is worse than no default: the user reads
`/tools lint` as covering explorations/ and it silently covers scripts/acquire only.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "tools" / "SKILL.md").read_text()
LINT = (ROOT / "hooks" / "lint-scripts.sh").read_text()


def section(name):
    i = SKILL.index(f"### `/tools {name}")
    j = SKILL.index("\n### ", i + 1) if "\n### " in SKILL[i + 1:] else len(SKILL)
    return SKILL[i:j]


class TestTools(unittest.TestCase):
    def test_render_resolves_the_declared_manuscript(self):
        s = section("render")
        self.assertIn("pipeline.py manuscript", s)
        self.assertNotIn("manuscript_<project>.qmd", s)

    def test_the_documented_lint_default_matches_the_script(self):
        default = re.search(r'TARGET="\$\{1:-([^}"]+)\}"', LINT).group(1)
        line = next(l for l in section("lint").splitlines() if "**Default:**" in l)
        self.assertIn(default, line)
        self.assertNotIn("explorations/", line)

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


if __name__ == "__main__":
    unittest.main()
