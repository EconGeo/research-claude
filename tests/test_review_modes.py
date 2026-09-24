"""Every flag /review advertises must have a mode section that dispatches and records.

A routing line with no mode section is worse than an undocumented flag: it tells the model
the mode exists, and the model then invents the dispatch. `--theory` was advertised in the
flag list and in pipeline/references/adopt.md as the critic-only route for a weight-20
component, and no section in the skill dispatched anything.

`--variance` is the mirror case: fully specified in agents/editor.md, ruled NOT to be wired
(D-19, 2026-09-24 — a named third referee is wanted instead of N-way sampling). The skill
must therefore name the flag and refuse it, so the model neither invents a dispatch nor
reads editor.md's variance section as reachable.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "review" / "SKILL.md").read_text()
EDITOR = (ROOT / "agents" / "editor.md").read_text()
RUBRICS = (ROOT / "skills" / "review" / "config" / "scoring-rubrics.md").read_text()


def mode_section(flag):
    i = SKILL.index(f"`{flag}`", SKILL.index("## Mode Details"))
    return SKILL[i:SKILL.index("\n### ", i + 1)] if "\n### " in SKILL[i:] else SKILL[i:]


class TestAdvertisedFlagsHaveModes(unittest.TestCase):
    def test_theory_has_a_mode_section(self):
        self.assertRegex(SKILL, r"(?m)^### .*`--theory`")

    def test_theory_dispatches_its_critic_and_records_the_component(self):
        """adopt.md routes the `theory` component here; registry weight is 20."""
        section = mode_section("--theory")
        self.assertIn("theorist-critic", section)
        self.assertIn("record-score theory", section)
        self.assertIn(".claude/skills/review/templates/theory-review-4-phases.md", section)

    def test_variance_is_named_and_refused_not_improvised(self):
        """editor.md specifies the mode and says /review does not reach it; the skill must
        agree in its own text, and must not advertise the flag in argument-hint."""
        self.assertIn("--variance", EDITOR)
        self.assertIn("--variance", SKILL)
        self.assertNotIn("--variance", re.search(r"argument-hint:.*", SKILL).group(0))
        self.assertRegex(SKILL, r"--variance[^\n]*(not wired|refuse)")

    def test_stress_does_not_record_a_score(self):
        """editor.md stress mode writes no editorial_decision.md to record from."""
        section = mode_section("--stress")
        self.assertNotIn("record-score referees", section)
        self.assertIn("records no score", section)

    def test_scoring_table_lists_every_recording_mode(self):
        table = SKILL[SKILL.index("## Scoring"):]
        for mode in ("Theory", "Replication"):
            self.assertIn(mode, table)


class TestRefereesScoreHasASource(unittest.TestCase):
    """D3(a): `record-score referees` needs a number the editor actually produces."""

    def test_editorial_decision_carries_an_overall_score_line(self):
        fmt = EDITOR[EDITOR.index("# Editorial Decision:"):EDITOR.index("## Variance synthesis mode")]
        self.assertRegex(fmt, r"\*\*Overall score:\*\*")

    def test_rubrics_have_an_editor_section(self):
        self.assertRegex(RUBRICS, r"(?m)^## Editor\b")


if __name__ == "__main__":
    unittest.main()
