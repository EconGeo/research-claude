"""Contracts for the two ZotPilot bridge skills.

The marker tag is the idempotency key for the whole library, so writing it for an item that
got no Data note removes that item from every future run. And a local-first rule that only
appears as a citation is not a rule — ztp-research goes straight to external search, so the
local sweep has to happen in the bridge or nowhere.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAG = (ROOT / "skills" / "ztp-data-tag" / "SKILL.md").read_text()
LIT = (ROOT / "skills" / "lit-position" / "SKILL.md").read_text()
VENDORED = (ROOT / "zotpilot-skills" / "ztp-research" / "SKILL.md").read_text()


class TestDataTagAtomicity(unittest.TestCase):
    def test_the_marker_tag_is_conditional_on_the_data_note(self):
        i = TAG.index("## Step 5")
        j = TAG.index("## Step 6")
        step5 = TAG[i:j]
        self.assertIn("get_notes", step5, "must check for an existing Data note first")
        self.assertRegex(step5, r"data-tagged[^\n]*only|only[^\n]*data-tagged")
        # the note must come before the tags in the step's own ordering
        self.assertLess(step5.index("create_note"), step5.index("manage_tags"))

    def test_the_skip_case_is_reported_not_silent(self):
        self.assertIn("no Data note", TAG)


class TestDataTagVocabularyMerge(unittest.TestCase):
    def test_step_5b_merges_near_duplicate_tags_before_the_report(self):
        i = TAG.index("## Step 5b"); j = TAG.index("## Step 6")
        self.assertLess(TAG.index("## Step 5 "), i)
        step5b = TAG[i:j]
        self.assertIn("near-duplicate", step5b)
        self.assertNotIn('action="set"', step5b.replace('never `set`', ''))


class TestDataTagExtractionIsRouted(unittest.TestCase):
    """Plan Part B, Task B1: the per-paper MCP loop runs in a subagent that holds zotpilot
    and returns records; preview and every write stay in the main context."""

    def test_step_3_dispatches_the_extractor_and_step_4_previews_in_the_main_context(self):
        step3 = TAG[TAG.index("## Step 3"):TAG.index("## Step 4")]
        self.assertIn("data-tag-extractor", step3)
        self.assertIn(".claude/agents/data-tag-extractor.md", step3)
        step4 = TAG[TAG.index("## Step 4"):TAG.index("## Step 5 ")]
        self.assertNotIn("Agent", step4)

    def test_the_extractor_holds_zotpilot_and_writes_nothing(self):
        a = (ROOT / "agents" / "data-tag-extractor.md").read_text()
        front = a.split("---")[1]
        self.assertIn("mcpServers", front); self.assertIn("zotpilot", front)
        self.assertNotRegex(front, r"tools:.*\b(Write|Edit)\b")
        self.assertIn("Do NOT write any files", a)


class TestLitPositionLocalFirst(unittest.TestCase):
    def test_ztp_research_still_starts_externally(self):
        """If this ever fails, upstream changed and the bridge workaround can be revisited."""
        self.assertIn("**External search**", VENDORED)

    def test_the_bridge_runs_the_local_sweep_before_dispatching(self):
        i = LIT.index("## Step 1")
        j = LIT.index("## Step 2")
        step1 = LIT[i:j]
        for tool in ("search_topic", "advanced_search"):
            self.assertIn(tool, step1)
        self.assertLess(step1.index("search_topic"), step1.index("/ztp-research"))

    def test_the_local_sweep_and_citation_chains_run_in_lit_scout(self):
        """Plan Task B2: the sweep's tool names stay in Step 1 (as the scout's brief) and still
        precede /ztp-research; the scout holds zotpilot and writes nothing."""
        step1 = LIT[LIT.index("## Step 1"):LIT.index("## Step 2")]
        self.assertIn("lit-scout", step1)
        self.assertIn(".claude/agents/lit-scout.md", step1)
        a = (ROOT / "agents" / "lit-scout.md").read_text()
        front = a.split("---")[1]
        self.assertIn("zotpilot", front)
        self.assertNotRegex(front, r"tools:.*\b(Write|Edit)\b")
        self.assertIn("Do NOT write any files", a)
        self.assertIn("search_academic_databases", a)  # named only to forbid it

    def test_bash_is_pre_approved_because_step_7_runs_pipeline_py(self):
        front = LIT.split("---")[1]
        self.assertIn("pipeline.py", LIT)
        self.assertRegex(front, r"allowed-tools:.*\bBash\b")


if __name__ == "__main__":
    unittest.main()
