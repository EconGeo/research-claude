"""Task 8: the results fingerprint on scores, staleness, and the stale-stages SessionStart hook."""
import json, os, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_pipeline import FixtureCase, run
import design_block as dsb

HOOK = ROOT / "hooks" / "stale-stages.py"


class StaleCase(FixtureCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(run("state", "init", root=self.t)[0], 0)

    def fp(self, h):
        p = self.t / "quality_reports" / "render_fingerprint.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({"estimates_hash": h, "data_hash": "d", "design_hash": "x", "models": {}}))

    def score(self, comp, critic, val="90", *extra):
        rc, out = run("state", "record-score", comp, val, "--critic", critic, "--report", "r.md", *extra, root=self.t)
        self.assertEqual(rc, 0, out)

    def state(self):
        return json.loads((self.t / "quality_reports" / "pipeline_state.json").read_text())


class TestStaleness(StaleCase):
    def test_1_not_retrofitted_unaffected(self):
        # FixtureCase signs the fixture's design; a paper not yet retrofitted has neither file.
        (self.t / dsb.LOCK_REL).unlink(); (self.t / "quality_reports" / "render_fingerprint.json").unlink()
        self.score("manuscript", "writer-critic")
        rc, out = run("score", "--gate", "commit", root=self.t)
        self.assertNotIn("STALE", out)
        rc, out = run("stale", root=self.t)
        self.assertEqual((rc, out.strip()), (0, "stale: none"))

    def test_2_changed_estimates_make_manuscript_stale(self):
        self.fp("A"); self.score("manuscript", "writer-critic")
        self.assertEqual(run("stale", root=self.t)[0], 0)
        self.fp("B")
        rc, out = run("score", "--gate", "commit", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("STALE", out)
        rc, out = run("next", root=self.t)
        self.assertRegex(out, r"OPEN\s+manuscript .*older fingerprint")
        rc, out = run("pre", "editor", root=self.t)
        self.assertEqual(rc, 1)
        rc, out = run("stale", root=self.t)
        self.assertEqual(rc, 1); self.assertRegex(out, r"STALE manuscript: ")

    def test_3_code_score_not_stale(self):
        self.fp("A"); self.score("code", "coder-critic"); self.fp("B")
        self.assertEqual(run("stale", root=self.t)[1].strip(), "stale: none")

    def test_4_section_score_does_not_clear(self):
        self.fp("A"); self.score("manuscript", "writer-critic"); self.fp("B")
        self.score("manuscript", "writer-critic", "90", "--scope", "section:Intro")
        self.assertEqual(run("stale", root=self.t)[0], 1)
        self.score("manuscript", "writer-critic")
        self.assertEqual(run("stale", root=self.t)[0], 0)

    def test_5_lock_without_fingerprint_fails_gate(self):
        (self.t / "quality_reports" / "render_fingerprint.json").unlink()   # FixtureCase's stub
        self.score("manuscript", "writer-critic")
        (self.t / "quality_reports").mkdir(exist_ok=True)
        (self.t / dsb.LOCK_REL).parent.mkdir(parents=True, exist_ok=True)
        (self.t / dsb.LOCK_REL).write_text("{not json")          # corrupt lock still counts as locked
        rc, out = run("score", "--gate", "commit", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("no render_fingerprint.json", out)

    def test_6_score_and_receipt_carry_fingerprint_and_head(self):
        self.fp("A"); self.score("manuscript", "writer-critic")
        e = self.state()["components"]["manuscript"]
        self.assertEqual(e["fingerprint"]["estimates"], "A")
        self.assertIn("design", e["fingerprint"]); self.assertIn("head", e)
        rec = json.loads((self.t / "quality_reports" / "receipts.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["fingerprint"], e["fingerprint"]); self.assertEqual(rec["head"], e["head"])

    def test_7_hook(self):
        os.symlink(ROOT / "scripts" / "pipeline.py", self.t / ".claude" / "scripts" / "pipeline.py")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.t))
        def hook():
            return subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True, env=env)
        self.fp("A"); self.score("manuscript", "writer-critic")
        p = hook(); self.assertEqual((p.returncode, p.stdout), (0, ""))
        self.fp("B")
        p = hook(); self.assertEqual(p.returncode, 0)
        j = json.loads(p.stdout)
        self.assertIn("manuscript", j["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(j["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("manuscript", j["systemMessage"])


if __name__ == "__main__":
    unittest.main()
