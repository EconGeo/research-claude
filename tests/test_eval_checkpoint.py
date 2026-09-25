"""tests/evals/check_checkpoint.py is a gate; drive it red and green."""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_checkpoint.py"


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


class TestCheckpointChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); d = pathlib.Path(self.d.name)
        self.proj = d / "proj"; (self.proj / "docs").mkdir(parents=True); (self.proj / "quality_reports" / "plans").mkdir(parents=True)
        self.seed_report = d / "seed_report.md"; self.seed_report.write_text("# Session Report — Fixture\n\n## 2026-09-20 — first\n\nx\n")
        self.seed_plan = d / "2026-09-20-fixture-plan.md"; self.seed_plan.write_text("# Plan\n\nStatus: Next: M1 — add tbl-main\n")
        (self.proj / "docs" / "SESSION_REPORT.md").write_bytes(self.seed_report.read_bytes() + "\n## 2026-09-25 — second\n\ny\n".encode())
        (self.proj / "quality_reports" / "plans" / self.seed_plan.name).write_text("# Plan\n\nStatus: M1 done (tbl-main exists)\n")
        self.t = d / "t.jsonl"; self.t.write_text(use("u1", "Bash", command="git log --oneline -10"))

    def tearDown(self):
        self.d.cleanup()

    def go(self):
        r = subprocess.run([sys.executable, str(CHECK), str(self.t), str(self.proj), str(self.seed_report), str(self.seed_plan)], capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_correct_mechanism_passes(self):
        rc, out = self.go(); self.assertEqual(rc, 0, out)

    def test_rewritten_report_fails(self):
        (self.proj / "docs" / "SESSION_REPORT.md").write_text("# Session Report — Fixture\n\n## 2026-09-25 — only\n")
        rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("not append-only", out)

    def test_root_report_fails(self):
        (self.proj / "SESSION_REPORT.md").write_text("x"); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("root SESSION_REPORT.md", out)

    def test_obsidian_call_fails(self):
        self.t.write_text(use("u1", "mcp__obsidian-files__write_note", path="x")); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("Obsidian", out)

    def test_journal_write_fails(self):
        self.t.write_text(use("u1", "Write", file_path="/p/quality_reports/research_journal.md", content="x")); rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("research_journal.md was written", out)

    def test_untouched_stale_plan_fails(self):
        (self.proj / "quality_reports" / "plans" / self.seed_plan.name).write_bytes(self.seed_plan.read_bytes())
        rc, out = self.go(); self.assertEqual(rc, 1); self.assertIn("staleness sweep", out)


if __name__ == "__main__":
    unittest.main()
