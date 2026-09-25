import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def use_sub(uid, name, parent, **inp):
    """Like use(), but tags the line with parent_tool_use_id — a tool call made inside a
    dispatched subagent's own turn, per evallib.main_session_tool_uses()."""
    return json.dumps({"type": "assistant", "parent_tool_use_id": parent, "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout


CHECK = ROOT / "tests" / "evals" / "check_review.py"
def rec(comp, critic, rep): return use("r" + comp, "Bash", command=f"python3 .claude/scripts/pipeline.py state record-score {comp} 90 --critic {critic} --report {rep}")
T = (use("u1", "Bash", command="git status --porcelain")
     + use("u2", "Agent", subagent_type="strategist-critic", prompt="x") + use("u3", "Agent", subagent_type="writer-critic", prompt="x") + use("u4", "Agent", subagent_type="verifier", prompt="x")
     + use("u5", "Bash", command="git status --porcelain")
     + use("w1", "Write", file_path="/p/quality_reports/reviews/strategist-critic_d.md", content="r") + rec("strategy", "strategist-critic", "quality_reports/reviews/strategist-critic_d.md")
     + use("w2", "Write", file_path="/p/quality_reports/reviews/writer-critic_d.md", content="r") + rec("manuscript", "writer-critic", "quality_reports/reviews/writer-critic_d.md")
     + use("w3", "Write", file_path="/p/quality_reports/verification_report.md", content="r") + rec("replication", "verifier", "quality_reports/verification_report.md"))


class TestReviewChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, "/p"); self.assertEqual(rc, 0, out)

    def test_no_porcelain_after_fails(self):
        rc, out = go(CHECK, T.replace(use("u5", "Bash", command="git status --porcelain"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("after the verifier", out)

    def test_missing_critic_fails(self):
        rc, out = go(CHECK, T.replace(use("u3", "Agent", subagent_type="writer-critic", prompt="x"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("writer-critic was never dispatched", out)

    def test_score_before_report_fails(self):
        rc, out = go(CHECK, T.replace(use("w2", "Write", file_path="/p/quality_reports/reviews/writer-critic_d.md", content="r"), ""), "/p"); self.assertEqual(rc, 1); self.assertIn("manuscript report was not Written", out)

    def test_pool_read_fails(self):
        rc, out = go(CHECK, T + use("u9", "Read", file_path="/p/.claude/skills/review/templates/disposition-pool.md"), "/p"); self.assertEqual(rc, 1); self.assertIn("disposition-pool.md", out)

    def test_pool_read_in_subagent_passes(self):
        # A critic's own Read of disposition-pool.md (parent_tool_use_id set, per the
        # writer-critic dispatch at u3) is not a main-context read — must not fail.
        rc, out = go(CHECK, T + use_sub("u9", "Read", "u3", file_path="/p/.claude/skills/review/templates/disposition-pool.md"), "/p"); self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
