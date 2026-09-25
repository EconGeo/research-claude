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


CHECK = ROOT / "tests" / "evals" / "check_strategize.py"
T = (use("u1", "Agent", subagent_type="strategist", prompt="Use .claude/skills/strategize/templates/design-checklists/did.md only")
     + use("u2", "Agent", subagent_type="strategist-critic", prompt="x")
     + use("u3", "Bash", command="python3 .claude/scripts/pipeline.py state record-score strategy 84 --critic strategist-critic --deductions 16 --report quality_reports/reviews/strategist-critic_x.md"))


class TestStrategizeChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.d.name); (self.p / "quality_reports" / "decisions").mkdir(parents=True)
        (self.p / "quality_reports" / "decisions" / "strategy_psl.md").write_text("# Decision\n\n## Alternatives considered\n\n- IV: rejected\n- RDD: rejected\n")

    def tearDown(self):
        self.d.cleanup()

    def test_correct_mechanism_passes(self):
        rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 0, out)

    def test_all_checklists_named_fails(self):
        rc, out = go(CHECK, T.replace("did.md only", "did.md, design-checklists/iv.md, design-checklists/rdd.md"), self.p); self.assertEqual(rc, 1); self.assertIn("other designs", out)

    def test_two_scores_fail(self):
        rc, out = go(CHECK, T + T.splitlines(keepends=True)[2], self.p); self.assertEqual(rc, 1); self.assertIn("ran 2 times", out)

    def test_low_score_without_revision_fails(self):
        rc, out = go(CHECK, T.replace("strategy 84", "strategy 61"), self.p); self.assertEqual(rc, 1); self.assertIn("no revision round", out)

    def test_low_score_with_revision_passes(self):
        second = (use("u4", "Agent", subagent_type="strategist", prompt="Revise per the critic; .claude/skills/strategize/templates/design-checklists/did.md")
                  + use("u5", "Agent", subagent_type="strategist-critic", prompt="re-score")
                  + use("u6", "Bash", command="python3 .claude/scripts/pipeline.py state record-score strategy 86 --critic strategist-critic --deductions 14 --report quality_reports/reviews/strategist-critic_y.md"))
        rc, out = go(CHECK, T.replace("strategy 84", "strategy 61") + second, self.p); self.assertEqual(rc, 0, out)

    def test_critic_first_fails(self):
        lines = T.splitlines(keepends=True); rc, out = go(CHECK, lines[1] + lines[0] + lines[2], self.p); self.assertEqual(rc, 1); self.assertIn("before strategist", out)

    def test_no_alternatives_fails(self):
        (self.p / "quality_reports" / "decisions" / "strategy_psl.md").write_text("# Decision\n\nDiD.\n"); rc, out = go(CHECK, T, self.p); self.assertEqual(rc, 1); self.assertIn("Alternatives", out)


if __name__ == "__main__":
    unittest.main()
