# tests/test_check_install_personal_shadow.py
"""check_install.sh `personal-shadow`: a user-level skill with a project skill's name runs
instead of it (Claude Code: personal over project), so it FAILs — unless both are the same
target. `zotpilot-vendored` (--all only) WARNs, never FAILs, when the fork is unreachable."""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = str(ROOT / "scripts" / "check_install.sh")

class TestPersonalShadow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "agents").mkdir(parents=True); (self.rc / "skills" / "ztp-x").mkdir(parents=True)
        (self.rc / "agents" / "a.md").write_text("a\n"); (self.rc / "skills" / "ztp-x" / "SKILL.md").write_text("s\n")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True)
        os.symlink(self.rc / "skills" / "ztp-x", self.p / ".claude" / "skills" / "ztp-x")
        self.home = t / "home-skills"; self.home.mkdir()
    def tearDown(self): self.tmp.cleanup()
    def line(self, check):
        env = dict(os.environ, CLAUDE_PERSONAL_SKILLS_DIR=str(self.home))
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True, env=env).stdout
        return next((l for l in out.splitlines() if f"[{check}]" in l), "")

    def test_no_personal_copy_passes(self):
        self.assertTrue(self.line("personal-shadow").startswith("PASS"), self.line("personal-shadow"))

    def test_real_personal_copy_fails(self):
        (self.home / "ztp-x").mkdir(); (self.home / "ztp-x" / "SKILL.md").write_text("other\n")
        l = self.line("personal-shadow")
        self.assertTrue(l.startswith("FAIL") and "ztp-x" in l, l)

    def test_symlink_to_same_target_is_not_a_shadow(self):
        os.symlink(self.rc / "skills" / "ztp-x", self.home / "ztp-x")
        self.assertTrue(self.line("personal-shadow").startswith("PASS"), self.line("personal-shadow"))

    def test_regular_file_is_not_a_shadow(self):
        (self.home / "ztp-x").write_text("stray file\n")
        self.assertTrue(self.line("personal-shadow").startswith("PASS"), self.line("personal-shadow"))

    def test_broken_symlink_is_a_shadow(self):
        os.symlink(self.home / "nowhere", self.home / "ztp-x")
        self.assertTrue(self.line("personal-shadow").startswith("FAIL"), self.line("personal-shadow"))

class TestForkFreshness(unittest.TestCase):
    def test_fork_unreachable_warns(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, RESEARCH_DIR=d, ZOTPILOT_FORK_URL=f"file://{d}/no-such-repo")
            out = subprocess.run(["bash", SCRIPT, "--all"], capture_output=True, text=True, env=env).stdout
            l = next((x for x in out.splitlines() if "[zotpilot-vendored]" in x), "")
            self.assertTrue(l.startswith("WARN"), out)

if __name__ == "__main__": unittest.main()
