"""check_install.sh's `branch` criterion — its four outcomes against a throwaway checkout.

The `detached at the lock SHA` branch was untested (rulings §5). A shared checkout that is
detached is only safe when it sits exactly where the project's lock says; anywhere else it
re-points every paper at an unrecorded pipeline. CHECK_INSTALL_UNDER_TEST lets a mutated copy
of the script be run against these tests to show each one red.
"""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = os.environ.get("CHECK_INSTALL_UNDER_TEST", str(ROOT / "scripts" / "check_install.sh"))

def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                          check=True, capture_output=True, text=True).stdout.strip()

class TestBranchCriterion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "agents").mkdir(parents=True); (self.rc / "skills" / "s").mkdir(parents=True)
        (self.rc / "agents" / "a.md").write_text("a\n"); (self.rc / "skills" / "s" / "SKILL.md").write_text("s\n")
        git(t, "init", "-q", "-b", "main", str(self.rc)); git(self.rc, "add", "-A"); git(self.rc, "commit", "-qm", "one")
        self.c1 = git(self.rc, "rev-parse", "HEAD")
        (self.rc / "agents" / "b.md").write_text("b\n"); git(self.rc, "add", "-A"); git(self.rc, "commit", "-qm", "two")
        self.c2 = git(self.rc, "rev-parse", "HEAD")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True)
        os.symlink(self.rc / "skills" / "s", self.p / ".claude" / "skills" / "s")
    def tearDown(self): self.tmp.cleanup()

    def lock(self, sha): (self.p / ".claude" / "pipeline.lock").write_text(f"commit={sha}\n")
    def branch_line(self, env_extra=None):
        env = dict(os.environ, **(env_extra or {})); env.pop("RESEARCH_CLAUDE_ALLOW_BRANCH", None) if not env_extra else None
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True, env=env).stdout
        return next((l for l in out.splitlines() if "[branch]" in l), "")

    def test_on_main_passes(self):
        self.lock(self.c2)
        self.assertEqual(self.branch_line(), "PASS [branch] checkout on main")

    def test_detached_at_the_lock_sha_passes(self):
        git(self.rc, "checkout", "-q", "--detach", self.c1); self.lock(self.c1)
        self.assertEqual(self.branch_line(), "PASS [branch] detached at the lock SHA")

    def test_detached_elsewhere_fails(self):
        git(self.rc, "checkout", "-q", "--detach", self.c1); self.lock(self.c2)
        self.assertTrue(self.branch_line().startswith("FAIL [branch]"), self.branch_line())

    def test_detached_with_no_lock_fails(self):
        git(self.rc, "checkout", "-q", "--detach", self.c1)
        self.assertTrue(self.branch_line().startswith("FAIL [branch]"), self.branch_line())

    def test_other_branch_fails_unless_allowed(self):
        git(self.rc, "checkout", "-q", "-b", "canary"); self.lock(self.c2)
        self.assertTrue(self.branch_line().startswith("FAIL [branch]"), self.branch_line())
        self.assertTrue(self.branch_line({"RESEARCH_CLAUDE_ALLOW_BRANCH": "1"}).startswith("WARN [branch]"))

if __name__ == "__main__": unittest.main()
