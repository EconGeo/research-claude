"""Plan Part B residue (Tasks B4–B6): context that should not be held in the main session.

B4 — /checkpoint's Obsidian sync deliberately stays in the main context (D4b) and says why.
B5 — /discover ideate checks novelty against the local index through lit-scout.
B6 — /revise and /write LIST the manuscript's labels and headings in the main context; the
     dispatched agent reads the sections it works on.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHK = (ROOT / "skills" / "checkpoint" / "gotchas.md").read_text()
DIS = (ROOT / "skills" / "discover" / "SKILL.md").read_text()
REV = (ROOT / "skills" / "revise" / "SKILL.md").read_text()
WRI = (ROOT / "skills" / "write" / "SKILL.md").read_text()


def section(text, start_re, end_re):
    i = re.search(start_re, text, flags=re.M); j = re.search(end_re, text[i.end():], flags=re.M)
    return text[i.end(): i.end() + j.start()] if j else text[i.end():]


class TestB4CheckpointObsidianStaysHome(unittest.TestCase):
    def test_gotchas_records_the_reason(self):
        self.assertIn("main context", CHK)
        self.assertRegex(CHK, r"machine-specific|user-configured")


class TestB5IdeateNovelty(unittest.TestCase):
    def test_ideate_routes_novelty_through_lit_scout(self):
        body = section(DIS, r"^### `/discover ideate", r"^### |^Known failure")
        self.assertIn("lit-scout", body)
        self.assertIn(".claude/agents/lit-scout.md", body)


class TestB6TheAgentReadsTheManuscript(unittest.TestCase):
    def test_write_step_1_lists_rather_than_reads(self):
        step1 = section(WRI, r"^#### 1\. Context Gathering", r"^#### 2\.")
        self.assertNotIn("read the declared manuscript in full", step1)
        self.assertRegex(step1, r"#\| label:")

    def test_revise_step_1_lists_rather_than_reads(self):
        step1 = section(REV, r"^### Step 1: Parse Inputs", r"^### Step 2")
        self.assertNotRegex(step1, r"^\d\. Read the manuscript \(", )
        self.assertRegex(step1, r"#\| label:")


if __name__ == "__main__":
    unittest.main()
