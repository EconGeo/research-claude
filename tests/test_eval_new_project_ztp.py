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


CHECK = ROOT / "tests" / "evals" / "check_new_project_ztp.py"
T = use("u1", "mcp__zotpilot__get_index_stats")
E = 'CALL get_index_stats {}\n'


class TestNewProjectZtpChecker(unittest.TestCase):
    def test_stats_only_passes(self):
        self.assertEqual(run(CHECK, T, E)[0], 0)

    def test_no_stats_fails(self):
        rc, out = run(CHECK, "", ""); self.assertEqual(rc, 1); self.assertIn("never reached", out)

    def test_index_library_fails(self):
        rc, out = run(CHECK, T, E + 'WRITE index_library {} -> {"indexed": []}\n'); self.assertEqual(rc, 1); self.assertIn("index_library", out)

    def test_ztp_setup_fails(self):
        rc, out = run(CHECK, T + use("u2", "Skill", skill="ztp-setup"), E); self.assertEqual(rc, 1); self.assertIn("ztp-setup", out)


if __name__ == "__main__":
    unittest.main()
