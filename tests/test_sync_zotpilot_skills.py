"""sync-zotpilot-skills.sh against a local stand-in fork: --check reports drift without
writing; a real sync overwrites and records the source commit in VENDORED.md itself."""
import os, pathlib, shutil, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(*a, cwd=None, env=None):
    return subprocess.run(list(a), cwd=cwd, env=env, capture_output=True, text=True)

class TestSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.fork = t / "fork"; (self.fork / "claude-skills" / "ztp-x").mkdir(parents=True)
        (self.fork / "claude-skills" / "ztp-x" / "SKILL.md").write_text("new\n")
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(self.fork)]
        run("git", "init", "-q", "-b", "main", str(self.fork)); run(*g, "add", "-A"); run(*g, "commit", "-qm", "c")
        self.sha = run(*g, "rev-parse", "--short", "HEAD").stdout.strip()
        self.rc = t / "rc"; (self.rc / "scripts").mkdir(parents=True)
        shutil.copy(ROOT / "scripts" / "sync-zotpilot-skills.sh", self.rc / "scripts")
        dest = self.rc / "zotpilot-skills" / "ztp-x"; dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("old\n")
        (self.rc / "zotpilot-skills" / "VENDORED.md").write_text("- Vendored from commit: `aaaaaaa` (old)\n")
        self.env = dict(os.environ, ZOTPILOT_FORK_URL=f"file://{self.fork}")
    def tearDown(self): self.tmp.cleanup()
    def sync(self, *a): return run("bash", str(self.rc / "scripts" / "sync-zotpilot-skills.sh"), *a, env=self.env)

    def test_check_reports_drift_and_writes_nothing(self):
        r = self.sync("--check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual((self.rc / "zotpilot-skills" / "ztp-x" / "SKILL.md").read_text(), "old\n")

    def test_sync_overwrites_and_records_commit(self):
        self.assertEqual(self.sync().returncode, 0)
        self.assertEqual((self.rc / "zotpilot-skills" / "ztp-x" / "SKILL.md").read_text(), "new\n")
        self.assertIn(f"`{self.sha}`", (self.rc / "zotpilot-skills" / "VENDORED.md").read_text())
        self.assertEqual(self.sync("--check").returncode, 0)

    def test_unreachable_fork_is_not_exit_1(self):
        self.env["ZOTPILOT_FORK_URL"] = f"file://{self.rc}/no-such-repo"
        self.assertEqual(self.sync("--check").returncode, 3)

if __name__ == "__main__": unittest.main()
