import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eval_fixture

SKILL = "ztp-profile"


def run(check, transcript, mock_log, load="project"):
    return eval_fixture.run(check, transcript, mock_log, SKILL, load)


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


CHECK = ROOT / "tests" / "evals" / "check_ztp_profile.py"
E = ('CALL browse_library {"view": "overview"}\nCALL browse_library {"view": "collections"}\nCALL browse_library {"view": "tags"}\n'
     'CALL advanced_search {"tag": null}\nCALL profile_library {}\n')


class TestZtpProfileChecker(unittest.TestCase):
    def test_map_then_halt_passes(self):
        self.assertEqual(run(CHECK, "", E)[0], 0)

    def test_missing_view_fails(self):
        rc, out = run(CHECK, "", E.replace('CALL browse_library {"view": "tags"}\n', "")); self.assertEqual(rc, 1); self.assertIn("view='tags'", out)

    def test_write_before_approval_fails(self):
        rc, out = run(CHECK, "", E + 'WRITE manage_tags {"action": "remove", "item_key": "K4", "tags": ["AI"]} -> {"removed": ["AI"]}\n'); self.assertEqual(rc, 1); self.assertIn("approval", out)

    def test_set_fails(self):
        rc, out = run(CHECK, "", E + 'CALL manage_tags {"action": "set", "item_key": "K4", "tags": ["LLM"]}\n'); self.assertEqual(rc, 1); self.assertIn("'set'", out)

    def test_no_skill_load_fails(self):
        rc, out = run(CHECK, "", E, load=None); self.assertEqual(rc, 1); self.assertIn("no ZotPilot skill load recorded", out)

    def test_personal_skill_load_fails(self):
        rc, out = run(CHECK, "", E, load="personal"); self.assertEqual(rc, 1); self.assertIn("outside the project", out)


if __name__ == "__main__":
    unittest.main()
