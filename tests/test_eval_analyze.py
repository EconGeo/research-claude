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


CHECK = ROOT / "tests" / "evals" / "check_analyze.py"
def ag(uid, t): return use(uid, "Agent", subagent_type=t, prompt="x")
T = (use("s1", "Bash", command="python3 .claude/scripts/pipeline.py manuscript") + use("s2", "Bash", command="python3 .claude/scripts/pipeline.py pre coder")
     + ag("a1", "data-engineer") + ag("a2", "coder-critic")
     + use("w1", "Write", file_path="/p/quality_reports/reviews/coder-critic_a.md", content="r")
     + use("r1", "Bash", command="python3 .claude/scripts/pipeline.py state record-score code 85 --critic coder-critic --report quality_reports/reviews/coder-critic_a.md")
     + ag("a3", "coder") + ag("a4", "coder-critic")
     + use("w2", "Write", file_path="/p/quality_reports/reviews/coder-critic_b.md", content="r")
     + use("r2", "Bash", command="python3 .claude/scripts/pipeline.py state record-score code 88 --critic coder-critic --report quality_reports/reviews/coder-critic_b.md"))


class TestAnalyzeChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p", 0, 0); self.assertEqual(rc, 0, out)

    def test_step0_after_dispatch_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[2] + lines[0] + lines[1] + "".join(lines[3:]), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("after an agent", out)

    def test_wrong_order_fails(self):
        rc, out = go(CHECK, T.replace(ag("a1", "data-engineer"), ag("a1", "coder")), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("dispatch order", out)

    def test_score_before_report_fails(self):
        rc, out = go(CHECK, T.replace(use("w2", "Write", file_path="/p/quality_reports/reviews/coder-critic_b.md", content="r"), ""), "/p", 0, 0); self.assertEqual(rc, 1); self.assertIn("before its report", out)

    def test_render_red_fails(self):
        rc, out = go(CHECK, T, "/p", 1, 0); self.assertEqual(rc, 1); self.assertIn("quarto render exited 1", out)


if __name__ == "__main__":
    unittest.main()
