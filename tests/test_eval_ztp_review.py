import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(check, transcript, mock_log):
    with tempfile.TemporaryDirectory() as d:
        pt, pe = pathlib.Path(d, "t.jsonl"), pathlib.Path(d, "e.log")
        pt.write_text(transcript); pe.write_text(mock_log)
        r = subprocess.run([sys.executable, str(check), str(pt), str(pe)], capture_output=True, text=True)
        return r.returncode, r.stdout


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


CHECK = ROOT / "tests" / "evals" / "check_ztp_review.py"
E = 'CALL search_topic {"query": "zoning"}\nCALL search_papers {"query": "supply elasticity"}\nCALL get_notes {"item_key": "K2"}\n'


class TestZtpReviewChecker(unittest.TestCase):
    def test_local_first_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_passages_before_topic_fails(self):
        lines = E.splitlines(keepends=True); rc, out = run(CHECK, "", lines[1] + lines[0] + lines[2]); self.assertEqual(rc, 1); self.assertIn("before search_topic", out)

    def test_no_notes_fails(self):
        rc, out = run(CHECK, "", E.replace("CALL get_notes", "CALL get_paper_details")); self.assertEqual(rc, 1); self.assertIn("get_notes", out)

    def test_external_search_fails(self):
        rc, out = run(CHECK, "", E + 'CALL search_academic_databases {"query": "x"}\n'); self.assertEqual(rc, 1); self.assertIn("stay local", out)


if __name__ == "__main__":
    unittest.main()
