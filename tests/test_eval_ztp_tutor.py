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


CHECK = ROOT / "tests" / "evals" / "check_ztp_tutor.py"
E = 'CALL get_paper_for_tutor {"title_or_doc_id": "Mortgage denial and neighborhood change"}\n'


class TestZtpTutorChecker(unittest.TestCase):
    def test_resolve_then_ask_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_other_call_first_fails(self):
        rc, out = run(CHECK, "", 'CALL search_topic {"query": "mortgage"}\n' + E); self.assertEqual(rc, 1); self.assertIn("first mock call", out)

    def test_annotate_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE annotate_pdf {"doc_id": "D1", "specs_path": "/t/x.json"} -> {"verified": true}\n'); self.assertEqual(rc, 1); self.assertIn("annotate_pdf", out)

    def test_persona_saved_without_answer_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE save_reading_persona {"persona_text": "x"} -> {"saved": true}\n'); self.assertEqual(rc, 1); self.assertIn("save_reading_persona", out)


if __name__ == "__main__":
    unittest.main()
