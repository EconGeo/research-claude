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


if __name__ == "__main__":
    unittest.main()
