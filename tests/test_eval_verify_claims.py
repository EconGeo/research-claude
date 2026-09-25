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


CHECK = ROOT / "tests" / "evals" / "check_verify_claims.py"
S = "ORCHID-LANTERN-42"


class TestVerifyClaimsChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name)
        subprocess.run(["git", "init", "-q", str(self.p)], check=True)
        (self.p / "draft.md").write_text(f"claims. {S}\n"); (self.p / "quality_reports").mkdir()
        subprocess.run(["git", "-C", str(self.p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.p), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "b"], check=True)
        (self.p / "quality_reports" / "verify_claims_2026-09-25.md").write_text("# r\n")
        self.T = (use("u1", "Read", file_path=str(self.p / ".claude/agents/claim-verifier.md"))
                  + use("u2", "Agent", subagent_type="claim-verifier", prompt="C1: Smith 2019 shows X. Q1: does it? Source: source.md")
                  + use("u3", "Write", file_path=str(self.p / "quality_reports/verify_claims_2026-09-25.md"), content="# r"))

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, self.T, self.p, S); self.assertEqual(rc, 0, out)

    def test_no_preflight_fails(self):
        rc, out = go(CHECK, self.T.split("\n", 1)[1], self.p, S); self.assertEqual(rc, 1); self.assertIn("Phase 0", out)

    def test_sentinel_in_prompt_fails(self):
        rc, out = go(CHECK, self.T.replace("Q1: does it?", f"Q1: {S}"), self.p, S); self.assertEqual(rc, 1); self.assertIn("sentinel", out)

    def test_draft_edit_fails(self):
        rc, out = go(CHECK, self.T + use("u4", "Edit", file_path=str(self.p / "draft.md"), old_string="a", new_string="b"), self.p, S); self.assertEqual(rc, 1); self.assertIn("modified draft.md", out)

    def test_missing_report_fails(self):
        (self.p / "quality_reports" / "verify_claims_2026-09-25.md").unlink(); rc, out = go(CHECK, self.T, self.p, S); self.assertEqual(rc, 1); self.assertIn("no quality_reports/verify_claims", out)


if __name__ == "__main__":
    unittest.main()
