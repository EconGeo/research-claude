"""apply.sh's lock — rewritten when the pipeline commit changes, left byte-identical when it has not.

Every bootstrap used to restamp `generated=`, so a coauthor's fresh clone showed a modified
.claude/pipeline.lock straight after ./bootstrap-pipeline.sh, and committing it churned against
the maintainer's own lock refreshes. APPLY_UNDER_TEST lets a mutated copy be shown red.
"""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
APPLY = os.environ.get("APPLY_UNDER_TEST", str(ROOT / "apply.sh"))
HEAD = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

class TestLockIdempotence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.p = pathlib.Path(self.tmp.name)
        self.lock = self.p / ".claude" / "pipeline.lock"
    def tearDown(self): self.tmp.cleanup()

    def apply(self):
        subprocess.run(["bash", APPLY, "--project-dir", str(self.p), "--link"], check=True, capture_output=True, text=True)

    def test_first_run_writes_the_lock(self):
        self.apply()
        self.assertIn(f"commit={HEAD}\n", self.lock.read_text())

    def test_same_commit_leaves_the_lock_untouched(self):
        self.apply()
        # Sentinel stamp and mode: a rewrite would replace both, even within the same second.
        stamped = self.lock.read_text().replace("generated=", "generated=SENTINEL-").replace("# installed via: pinned", "# installed via: tip (shared checkout)")
        self.lock.write_text(stamped)
        self.apply()
        self.assertEqual(self.lock.read_text(), stamped)

    def test_different_commit_rewrites_the_lock(self):
        self.apply()
        self.lock.write_text(self.lock.read_text().replace(f"commit={HEAD}", "commit=" + "0" * 40))
        self.apply()
        text = self.lock.read_text()
        self.assertIn(f"commit={HEAD}\n", text)
        self.assertNotIn("0" * 40, text)

class TestHooksPathInWorktree(unittest.TestCase):
    """core.hooksPath is shared config: a linked worktree must see the MAIN checkout's .git/hooks."""
    def test_main_checkouts_own_hook_blocks_install_from_a_worktree(self):
        with tempfile.TemporaryDirectory() as t:
            main = pathlib.Path(t) / "main"; wt = pathlib.Path(t) / "wt"
            g = lambda *a, cwd=main: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *a], check=True, capture_output=True, text=True)
            main.mkdir(); g("init", "-q", "-b", "main"); (main / "f").write_text("x"); g("add", "f"); g("commit", "-qm", "i")
            hook = main / ".git" / "hooks" / "pre-commit"; hook.write_text("#!/bin/sh\nexit 0\n"); hook.chmod(0o755)
            g("worktree", "add", "-q", str(wt))
            out = subprocess.run(["bash", APPLY, "--project-dir", str(wt), "--link"], check=True, capture_output=True, text=True).stdout
            self.assertIn("pre-commit gate NOT installed", out)
            cfg = subprocess.run(["git", "-C", str(main), "config", "--get", "core.hooksPath"], capture_output=True, text=True)
            self.assertEqual(cfg.stdout.strip(), "")

if __name__ == "__main__": unittest.main()
