import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout


CHECK = ROOT / "tests" / "evals" / "check_write.py"
LOGP = "quality_reports/critic_inputs/writer-critic_2026-09-29_120000.log"
T = (use("u1", "Bash", command="python3 .claude/scripts/pipeline.py manuscript")
     + use("u2", "Agent", subagent_type="writer", prompt="x")
     + use("c1", "Bash", command="python3 .claude/scripts/pipeline.py critic-inputs")
     + use("u3", "Agent", subagent_type="writer-critic", prompt=f"section mode; render inputs: {LOGP}")
     + use("u4", "Write", file_path="/p/quality_reports/reviews/writer-critic_2026-09-25.md", content="r")
     + use("u5", "Bash", command="python3 .claude/scripts/pipeline.py state record-score manuscript 88 --critic writer-critic --deductions 12 --report quality_reports/reviews/writer-critic_2026-09-25.md --scope section:Conclusion"))


class TestWriteChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p", 0); self.assertEqual(rc, 0, out)

    def test_dispatch_before_resolve_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + "".join(lines[2:]), "/p", 0); self.assertEqual(rc, 1); self.assertIn("before the manuscript was resolved", out)

    def test_unscoped_score_fails(self):
        rc, out = go(CHECK, T.replace(" --scope section:Conclusion", ""), "/p", 0); self.assertEqual(rc, 1); self.assertIn("not scoped", out)

    def test_score_before_report_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:4]) + lines[5] + lines[4], "/p", 0); self.assertEqual(rc, 1); self.assertIn("not Written before", out)

    def test_prose_check_red_fails(self):
        rc, out = go(CHECK, T, "/p", 1); self.assertEqual(rc, 1); self.assertIn("prose_number_check exited 1", out)

    def test_no_critic_inputs_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, "".join(lines[:2] + lines[3:]), "/p", 0); self.assertEqual(rc, 1); self.assertIn("critic-inputs` never ran", out)

    def test_dispatch_without_the_log_path_fails(self):
        rc, out = go(CHECK, T.replace(f"render inputs: {LOGP}", "no log"), "/p", 0); self.assertEqual(rc, 1); self.assertIn("does not name a critic_inputs/ log", out)


if __name__ == "__main__":
    unittest.main()
