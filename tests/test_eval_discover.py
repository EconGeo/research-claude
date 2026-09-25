import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout


def use_nested(uid, name, parent, **inp):
    # A subagent's own tool call, as it actually appears in a live transcript: flattened into
    # the same stream as the main session's, tagged with parent_tool_use_id pointing at the
    # Agent block that dispatched it. The live /discover data run showed the explorer's
    # WebSearch/WebFetch calls carry exactly this shape.
    return json.dumps({"type": "assistant", "parent_tool_use_id": parent, "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


CHECK = ROOT / "tests" / "evals" / "check_discover.py"
T = (use("u1", "Read", file_path="/p/.claude/references/domain-profile.md")
     + use("u2", "Agent", subagent_type="explorer", prompt="x")
     + use("u3", "Agent", subagent_type="explorer-critic", prompt="x")
     + use("u4", "Write", file_path="/p/quality_reports/reviews/explorer-critic_2026-09-25.md", content="r")
     + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score data 82 --critic explorer-critic --deductions 18 --report quality_reports/reviews/explorer-critic_2026-09-25.md"))


class TestDiscoverChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); a = self.p / "quality_reports" / "data-assessment" / "fx"; a.mkdir(parents=True)
        for f in ("data_sources.md", "data_dictionary.md", "access_instructions.md"): (a / f).write_text("x")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_dispatch_before_profile_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + "".join(lines[2:]), self.p); self.assertEqual(rc, 1); self.assertIn("not Read before", out)

    def test_web_tool_fails(self):
        rc, out = go(CHECK, T + use("u6", "WebSearch", query="teen employment data"), self.p); self.assertEqual(rc, 1); self.assertIn("web tool", out)

    def test_explorer_own_web_tool_passes(self):
        # Regression for the live run (2026-09-25): the explorer's own WebSearch/WebFetch calls
        # are flattened into the same transcript, tagged with parent_tool_use_id = the Agent
        # dispatch's id, not made by the main session — must not trip "the main session called
        # a web tool".
        rc, out = go(CHECK, T + use_nested("u6", "WebSearch", "u2", query="teen employment data"), self.p); self.assertEqual(rc, 0, out)

    def test_missing_artifact_fails(self):
        (self.p / "quality_reports" / "data-assessment" / "fx" / "access_instructions.md").unlink(); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("access_instructions.md", out)

    def test_score_before_report_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:3]) + lines[4] + lines[3], self.p); self.assertEqual(rc, 1); self.assertIn("not Written before", out)


if __name__ == "__main__":
    unittest.main()
