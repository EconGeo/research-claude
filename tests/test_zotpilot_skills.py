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
    """v2 guarantee: the idempotency marker (`data-tagged:v2`) is written only after the note, and
    only for a clean extraction. Behavioural coverage lives in tests/test_data_tag_cli.py
    (test_live_run_writes_note_then_tags, test_model_error_doc_is_never_written_live,
    test_note_logged_even_if_merge_tags_conflicts_and_undo_deletes_it,
    test_write_error_continues_and_report_exists)."""

    def test_the_marker_tag_is_conditional_on_the_data_note(self):
        step3 = TAG[TAG.index("## Step 3"):TAG.index("## Step 4")]
        self.assertRegex(step3, r"[Nn]otes are written before tags")
        self.assertRegex(step3, r"`data-tagged:v2` is the\s+idempotency marker")
        head = TAG[:TAG.index("## Preconditions")]
        self.assertRegex(head, r"`model_error` papers get no note, tags or marker")
        self.assertRegex(head, r"Only papers with status `ok` and at least one dataset\s+are written")

    def test_the_skip_case_is_reported_not_silent(self):
        head = TAG[:TAG.index("## Preconditions")]
        for status in ("write_conflict", "write_error", "model_error"):
            self.assertIn(status, head)
        for key in ("skipped_v2", "skipped_sidecar", "skipped_written", "unindexed"):
            self.assertIn(key, head)
        self.assertIn("Nothing is skipped silently", head)
        self.assertIn("Unindexed items are listed in the report", TAG)


class TestDataTagVocabularyMerge(unittest.TestCase):
    """v1 merged near-duplicate tags inline; v2 keeps the vocabulary closed and routes new
    sources through review queue -> proposed vocabulary diff -> user-approved promotion."""

    def test_step_5b_merges_near_duplicate_tags_before_the_report(self):
        step4 = TAG[TAG.index("## Step 4"):TAG.index("## Queries")]
        self.assertIn("**Review queue**", step4)
        self.assertIn("data_vocab.yaml", step4)
        self.assertRegex(step4, r"[Pp]romotions are a \*\*USER_REQUIRED\*\* gate")
        self.assertIn("wait for yes", step4)
        self.assertLess(step4.index("Review queue"), step4.index("USER_REQUIRED"))
        self.assertLess(step4.index("USER_REQUIRED"), step4.index("--pass N+1"))
        # the report that feeds the gate really carries the queue and the diff
        report = (ROOT / "skills/ztp-data-tag/scripts/data_tag/report.py").read_text()
        self.assertIn("## Review queue", report)
        self.assertIn("## Proposed vocabulary diff", report)
        self.assertNotIn('action="set"', TAG.replace('manage_tags(action="set")', ""))


class TestDataTagExtractionIsRouted(unittest.TestCase):
    """v2: extraction is local (Ollama via data_tag.py), never Claude or a subagent; the dry-run
    report is read in the main context before the live gate."""

    def test_step_3_dispatches_the_extractor_and_step_4_previews_in_the_main_context(self):
        self.assertIn("one `qwen2.5:7b-instruct` call", TAG)
        self.assertIn("No Claude-side extraction fallback", TAG)
        self.assertRegex(TAG, r"never Claude")
        self.assertNotIn("data-tag-extractor", TAG)
        self.assertNotRegex(TAG, r"\bAgent\(|subagent")
        self.assertNotRegex(TAG.split("---")[1], r"allowed-tools:.*\bAgent\b")
        step1 = TAG[TAG.index("## Step 1"):TAG.index("## Step 2")]
        self.assertIn("--dry-run", step1)
        self.assertRegex(step1, r"Read `quality_reports/data_tags/pass_NN.md` \*\*in full\*\*")
        step2 = TAG[TAG.index("## Step 2"):TAG.index("## Step 3")]
        self.assertIn("USER_REQUIRED", step2)
        self.assertLess(TAG.index("## Step 1"), TAG.index("## Step 2"))

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
