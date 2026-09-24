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
