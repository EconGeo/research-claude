import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eval_fixture

SKILL = "seed-papers"


def run(check, transcript, mock_log, load="project"):
    return eval_fixture.run(check, transcript, mock_log, SKILL, load)


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

    def test_no_skill_load_fails(self):
        rc, out = run(CHECK, T, E, load=None); self.assertEqual(rc, 1); self.assertIn("no ZotPilot skill load recorded", out)

    def test_personal_skill_load_fails(self):
        rc, out = run(CHECK, T, E, load="personal"); self.assertEqual(rc, 1); self.assertIn("outside the project", out)


if __name__ == "__main__":
    unittest.main()
