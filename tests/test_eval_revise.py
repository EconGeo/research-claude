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


CHECK = ROOT / "tests" / "evals" / "check_revise.py"


class TestReviseChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\n"); (self.p / "quality_reports").mkdir()
        (self.p / "quality_reports" / "referee_report_fixture.md").write_text("r\n")
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        self.T = (use("u1", "Read", file_path=str(self.p / "quality_reports/referee_report_fixture.md"))
                  + use("u2", "Grep", pattern="^#\\| label:|^#+ ", path=str(self.p / "manuscript_fixture.qmd")))

    def tearDown(self):
        self.d.cleanup()

    def test_halt_passes(self):
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 0, out)

    def test_full_read_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Read", file_path=str(self.p / "manuscript_fixture.qmd")), self.p); self.assertEqual(rc, 1); self.assertIn("Read in full", out)

    def test_coder_dispatch_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Agent", subagent_type="coder", prompt="x"), self.p); self.assertEqual(rc, 1); self.assertIn("coder was dispatched", out)

    def test_manuscript_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Edit", file_path=str(self.p / "manuscript_fixture.qmd"), old_string="a", new_string="b"), self.p); self.assertEqual(rc, 1); self.assertIn("modified the manuscript", out)

    def test_incomplete_tracker_fails(self):
        (self.p / "quality_reports" / "referee_response_tracker.md").write_text("| FATAL | TASTE |\n")
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("tracker written without", out)


if __name__ == "__main__":
    unittest.main()
