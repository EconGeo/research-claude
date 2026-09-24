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


class TestDepositModeExists(unittest.TestCase):
    """Phase 3.5: `/submit`'s description claimed to replace `data-deposit`; `/submit package`
    only assembled a replication package, and nothing deposited it anywhere. A real `deposit`
    mode must exist and actually record the result through pipeline.py, not just narrate it."""

    def test_deposit_mode_section_exists(self):
        body = mode_body(SUBMIT.read_text(), re.escape("`/submit deposit"))
        self.assertIsNotNone(body, "submit has no `/submit deposit` mode section")

    def test_deposit_mode_records_through_pipeline_py(self):
        body = mode_body(SUBMIT.read_text(), re.escape("`/submit deposit"))
        self.assertIn("state record-deposit", body)

    def test_deposit_mode_requires_package_and_audit_first(self):
        body = mode_body(SUBMIT.read_text(), re.escape("`/submit deposit"))
        self.assertIn("/submit package", body)
        self.assertIn("/submit audit", body)


if __name__ == "__main__":
    unittest.main()
