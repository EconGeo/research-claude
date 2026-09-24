"""The eval checkers under tests/evals/ are gates; a gate that cannot go red is not one."""
import pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_ztp_data_tag.py"

GOOD_T = (
 '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Agent","input":{"subagent_type":"data-tag-extractor"}}]}}\n'
 '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"mcp__zotpilot__manage_tags","input":{"action":"add","allow_new":true,"item_key":"K1","tags":["dataset:hmda"]}}]}}\n')
GOOD_E = (
 'WRITE create_note {"idempotent": true, "item_key": "K1"} -> {"created": true}\n'
 'WRITE manage_tags {"action": "add", "allow_new": true, "item_key": "K1", "tags": ["dataset:hmda"]} -> {"added": ["dataset:hmda"]}\n'
 'WRITE create_note {"idempotent": true, "item_key": "K2"} -> {"created": false}\n')


def run(t, e):
    with tempfile.TemporaryDirectory() as d:
        pt, pe = pathlib.Path(d, "t.jsonl"), pathlib.Path(d, "e.log")
        pt.write_text(t); pe.write_text(e)
        r = subprocess.run([sys.executable, str(CHECK), str(pt), str(pe)], capture_output=True, text=True)
        return r.returncode, r.stdout


class TestZtpDataTagChecker(unittest.TestCase):
    def test_the_correct_mechanism_passes(self):
        self.assertEqual(run(GOOD_T, GOOD_E)[0], 0)

    def test_tags_for_a_skipped_note_fail(self):
        rc, out = run(GOOD_T, GOOD_E + 'WRITE manage_tags {"action": "add", "allow_new": true, "item_key": "K2", "tags": ["x"]} -> {"added": ["x"]}\n')
        self.assertEqual(rc, 1); self.assertIn("skipped", out)

    def test_set_fails(self):
        rc, out = run(GOOD_T, GOOD_E.replace('"action": "add"', '"action": "set"'))
        self.assertEqual(rc, 1); self.assertIn("must be 'add'", out)

    def test_no_extractor_dispatch_fails(self):
        rc, out = run(GOOD_T.replace("data-tag-extractor", "someone-else"), GOOD_E)
        self.assertEqual(rc, 1); self.assertIn("never dispatched", out)

    def test_tags_before_extractor_fail(self):
        lines = GOOD_T.splitlines(keepends=True)
        rc, out = run(lines[1] + lines[0], GOOD_E)
        self.assertEqual(rc, 1); self.assertIn("before data-tag-extractor", out)


if __name__ == "__main__":
    unittest.main()
