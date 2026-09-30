import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eval_fixture

SKILL = "ztp-research"


def run(check, transcript, mock_log, load="project"):
    return eval_fixture.run(check, transcript, mock_log, SKILL, load)


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

    def test_no_skill_load_fails(self):
        rc, out = run(CHECK, "", E, load=None); self.assertEqual(rc, 1); self.assertIn("no ZotPilot skill load recorded", out)

    def test_personal_skill_load_fails(self):
        rc, out = run(CHECK, "", E, load="personal"); self.assertEqual(rc, 1); self.assertIn("outside the project", out)


if __name__ == "__main__":
    unittest.main()
