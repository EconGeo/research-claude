import os, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_plan_liveness.py"

def git(args, cwd, when=None):
    env = os.environ.copy()
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)

def init_repo(root):
    git(["init", "-q"], root)
    git(["config", "user.email", "t@example.com"], root)
    git(["config", "user.name", "T"], root)
    git(["config", "commit.gpgsign", "false"], root)
    hooks = root / ".nohooks"
    hooks.mkdir()
    git(["config", "core.hooksPath", str(hooks)], root)

def run_check(root, days=7):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--days", str(days)],
                           capture_output=True, text=True)

class TestCheckPlanLiveness(unittest.TestCase):
    """closeout handoff §4.2 item 5: 'nothing asks is there an open plan that hasn't moved in
    a week' — the 2026-09-16 closeout plan's own stall, invisible to every prior gate."""

    def test_old_open_plan_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "old-plan.md").write_text("- [ ] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "old"], root, when="2020-01-01T00:00:00")
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("WARN [plan-liveness]", r.stdout)
            self.assertIn("old-plan.md", r.stdout)

    def test_recently_touched_open_plan_quiet(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "fresh-plan.md").write_text("- [ ] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "fresh"], root)
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PASS [plan-liveness]", r.stdout)

    def test_fully_checked_plan_ignored_even_if_old(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            init_repo(root)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "done-plan.md").write_text("- [x] Step 1\n")
            git(["add", "."], root)
            git(["commit", "-q", "-m", "done"], root, when="2020-01-01T00:00:00")
            r = run_check(root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PASS [plan-liveness]", r.stdout)

if __name__ == "__main__": unittest.main()
