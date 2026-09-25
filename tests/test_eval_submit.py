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


CHECK = ROOT / "tests" / "evals" / "check_submit.py"
T = (use("u1", "Agent", subagent_type="verifier", prompt="x")
     + use("u2", "Write", file_path="/p/quality_reports/verification_report.md", content="r")
     + use("u3", "Bash", command="python3 .claude/scripts/pipeline.py state record-score replication 100 --critic verifier --report quality_reports/verification_report.md")
     + use("u4", "Bash", command="test -f ai_use_log.md && echo present || echo missing"))


class TestSubmitChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "quality_reports").mkdir()

    def tearDown(self):
        self.d.cleanup()

    def test_stop_on_missing_log_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_no_verifier_fails(self):
        rc, out = go(CHECK, T.split("\n", 1)[1], self.p); self.assertEqual(rc, 1); self.assertIn("never dispatched", out)

    def test_no_log_check_fails(self):
        rc, out = go(CHECK, T.rsplit("\n", 2)[0] + "\n", self.p); self.assertEqual(rc, 1); self.assertIn("ai_use_log.md was never checked", out)

    def test_cover_letter_fails(self):
        rc, out = go(CHECK, T + use("u5", "Write", file_path="/p/quality_reports/cover_letter_2026.qmd", content="x"), self.p); self.assertEqual(rc, 1); self.assertIn("failing paper", out)

    def test_verify_claims_recorded_fails(self):
        rc, out = go(CHECK, T + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-verify-claims --report x --result pass"), self.p); self.assertEqual(rc, 1); self.assertIn("record-verify-claims", out)


if __name__ == "__main__":
    unittest.main()
