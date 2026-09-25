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


CHECK = ROOT / "tests" / "evals" / "check_civilize.py"


class TestCivilizeChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\n"); (self.p / "quality_reports").mkdir()
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        (self.p / "quality_reports" / "civilize_manuscript_fixture_report.md").write_text("# report\n")
        self.T = use("u1", "Agent", subagent_type="civilize-auditor", prompt="Audit manuscript_fixture.qmd for the 10 categories") + use("u2", "Write", file_path=str(self.p / "quality_reports" / "civilize_manuscript_fixture_report.md"), content="# report")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 0, out)

    def test_two_dispatches_fail(self):
        rc, out = go(CHECK, self.T + use("u3", "Agent", subagent_type="civilize-auditor", prompt="Audit talks/seminar_talk.qmd"), self.p); self.assertEqual(rc, 1); self.assertIn("dispatched 2", out)

    def test_source_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Edit", file_path=str(self.p / "manuscript_fixture.qmd"), old_string="a", new_string="b"), self.p); self.assertEqual(rc, 1); self.assertIn("source file", out)

    def test_missing_report_fails(self):
        (self.p / "quality_reports" / "civilize_manuscript_fixture_report.md").unlink()
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("no quality_reports/civilize", out)

    def test_modified_manuscript_fails(self):
        (self.p / "manuscript_fixture.qmd").write_text("# Intro\nchanged\n")
        rc, out = go(CHECK, self.T, self.p); self.assertEqual(rc, 1); self.assertIn("is modified", out)

    def test_session_report_write_is_allowed(self):
        # rules/logging.md has every skill run append SESSION_REPORT.md at the project root;
        # observed on the first live run (2026-09-25). Not a civilize source-file edit.
        rc, out = go(CHECK, self.T + use("u3", "Write", file_path=str(self.p / "SESSION_REPORT.md"), content="# Session Report\n"), self.p)
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
