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


CHECK = ROOT / "tests" / "evals" / "check_seed_papers.py"
T = use("u1", "mcp__zotpilot__search_topic", query="zoning preemption housing supply") + use("u2", "mcp__zotpilot__search_topic", query="upzoning statewide reform")
E = 'CALL search_topic {"query": "zoning preemption housing supply"}\nCALL search_topic {"query": "upzoning statewide reform"}\n'


class TestSeedPapersChecker(unittest.TestCase):
    def test_two_searches_then_stop_passes(self):
        self.assertEqual(run(CHECK, T, E)[0], 0)

    def test_one_search_fails(self):
        rc, out = run(CHECK, T, 'CALL search_topic {"query": "a"}\n'); self.assertEqual(rc, 1); self.assertIn("fewer than two", out)

    def test_details_before_reply_fails(self):
        rc, out = run(CHECK, T, E + 'CALL get_paper_details {"doc_id": "D1"}\n'); self.assertEqual(rc, 1); self.assertIn("get_paper_details", out)

    def test_bib_write_fails(self):
        rc, out = run(CHECK, T + use("u3", "Write", file_path="/p/bibliography_base.bib", content="x"), E); self.assertEqual(rc, 1); self.assertIn("bibliography_base.bib", out)


if __name__ == "__main__":
    unittest.main()
