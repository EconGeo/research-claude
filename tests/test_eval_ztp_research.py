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


CHECK = ROOT / "tests" / "evals" / "check_ztp_research.py"
E = 'CALL search_academic_databases {"query": "\\"staggered difference-in-differences\\"", "year_min": 2020}\n'


class TestZtpResearchChecker(unittest.TestCase):
    def test_search_then_stop_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_ingest_same_turn_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE ingest_by_identifiers {"candidates": []} -> {"results": []}\n'); self.assertEqual(rc, 1); self.assertIn("same turn", out)

    def test_dedup_call_fails(self):
        rc, out = run(CHECK, "", E + 'CALL advanced_search {"year": 2021}\n'); self.assertEqual(rc, 1); self.assertIn("dedup", out)

    def test_phase3_tool_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE manage_tags {"action": "add"} -> {}\n'); self.assertEqual(rc, 1); self.assertIn("Phase 3", out)

    def test_web_tool_fails(self):
        rc, out = run(CHECK, use("u1", "WebFetch", url="https://en.wikipedia.org/wiki/x"), E); self.assertEqual(rc, 1); self.assertIn("web tool", out)


if __name__ == "__main__":
    unittest.main()
