"""Contracts between the review skill, the critic rubrics and the verifier.

Each test pins a defect the 2026-09-13 adoption runs surfaced, where two shipped files
disagreed and the agent followed whichever one it happened to read:

- the strategist-critic rubric had no point values, so two critics invented different
  weightings and their scores (41, 48) were not comparable;
- the verifier had two pass/fail definitions — `skills/review/SKILL.md` and
  `agents/verifier.md` — and both papers passed one and failed the other;
- the verifier ran a project's own gate script, which rewrote two tracked files.
"""
import pathlib, re, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
RUBRICS = ROOT / "skills" / "review" / "config" / "scoring-rubrics.md"
VERIFIER = ROOT / "agents" / "verifier.md"
REVIEW = ROOT / "skills" / "review" / "SKILL.md"
INVARIANTS = ROOT / "rules" / "content-invariants.md"

def section(text, heading_re, level="##"):
    """Body of the first `level` heading matching heading_re, up to the next heading of that level."""
    m = re.search(rf"^{level} {heading_re}.*$", text, re.M)
    if not m: return None
    nxt = re.search(rf"^{level} ", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]

class TestStrategistRubric(unittest.TestCase):
    def body(self):
        b = section(RUBRICS.read_text(), r"Strategist-Critic")
        self.assertIsNotNone(b, "scoring-rubrics.md has no Strategist-Critic section"); return b

    def deduction(self, body, severity):
        m = re.search(rf"^\|\s*\*\*{severity}\*\*.*\|\s*-(\d+)[^|]*\|\s*$", body, re.M)
        self.assertIsNotNone(m, f"no point value for {severity} in the Strategist-Critic rubric"); return int(m.group(1))

    def test_every_severity_carries_a_point_value(self):
        b = self.body()
        crit, major, minor = (self.deduction(b, s) for s in ("CRITICAL", "MAJOR", "MINOR"))
        self.assertGreater(crit, major); self.assertGreater(major, minor); self.assertGreater(minor, 0)

    def test_one_critical_alone_fails_the_commit_gate(self):
        """CRITICAL is "identification is wrong or unsupported". A rubric under which a paper
        with one such flaw and nothing else still clears 80 does not mean what it says."""
        self.assertLess(100 - self.deduction(self.body(), "CRITICAL"), 80)

    def test_nothing_still_says_there_is_no_point_rubric(self):
        for f in [RUBRICS, ROOT / "skills" / "review" / "gotchas.md", ROOT / "agents" / "strategist-critic.md"]:
            self.assertNotRegex(f.read_text(), r"(?i)not (use )?a point-deduction rubric", f.name)

    def test_strategist_critic_names_its_rubric_by_a_resolvable_path(self):
        self.assertIn(".claude/skills/review/config/scoring-rubrics.md", (ROOT / "agents" / "strategist-critic.md").read_text())

class TestVerifierDefinition(unittest.TestCase):
    def mandatory(self):
        m = re.search(r"^\*\*Mandatory:\*\*.*$", VERIFIER.read_text(), re.M)
        self.assertIsNotNone(m); return set(re.findall(r"INV-\d+", m.group(0)))

    def test_agent_and_invariants_table_name_the_same_invariants(self):
        row = re.search(r"^\|\s*\*\*verifier\*\*\s*\|(.*)$", INVARIANTS.read_text(), re.M)
        self.assertIsNotNone(row, "content-invariants.md has no verifier row")
        self.assertEqual(self.mandatory(), set(re.findall(r"INV-\d+", row.group(1))))

    def test_every_mandatory_invariant_is_a_numbered_check_in_the_report(self):
        """A FAIL condition the report table has no row for is a FAIL the reader never sees."""
        text = VERIFIER.read_text()
        checks = section(text, r"Standard checks")
        # Not section(): the report template's own `## Verification Report` line sits inside a code
        # fence and would end the section before the table it introduces.
        report = text[text.index("## Report"): text.index("## Rules")] if "## Report" in text and "## Rules" in text else None
        self.assertIsNotNone(checks); self.assertIsNotNone(report)
        for inv in self.mandatory():
            self.assertIn(inv, checks, f"{inv} is mandatory but no standard check names it")
        self.assertRegex(report, r"\|\s*4c\s*\|")

    def test_the_review_skill_defers_to_the_agent_rather_than_restating(self):
        b = section(REVIEW.read_text(), r"Verifier Pass/Fail Definition")
        self.assertIsNotNone(b)
        self.assertIn(".claude/agents/verifier.md", b)
        # A restated manuscript definition is what diverged; none of its terms may come back.
        for term in ("prose_number_check", "references.bib", "quarto render", "absolute paths"):
            self.assertNotIn(term, b, f"review SKILL restates the verifier's definition ({term})")

class TestVerifierLeavesTheTreeAlone(unittest.TestCase):
    def test_project_gate_scripts_are_out_of_scope(self):
        text = VERIFIER.read_text()
        self.assertRegex(text, r"(?i)only the commands this file names")
        self.assertIn("git status --porcelain", text)

    def test_the_review_skill_checks_the_tree_around_the_verifier(self):
        self.assertIn("git status --porcelain", REVIEW.read_text())

if __name__ == "__main__": unittest.main()
