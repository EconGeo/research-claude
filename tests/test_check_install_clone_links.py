"""check_install.sh's `clone-links` criterion — a committed symlink whose target leaves the repo.

`dangling` resolves links on THIS machine, so a committed link into ~/Research/.claude/references
passes here and is dead in every coauthor's clone (ESG a30b42f, 2026-09-13). `tracked-links`
only looks under the pipeline-owned dirs. This reads the committed link target itself, so the
answer does not depend on what happens to exist on the machine running the check.
CHECK_INSTALL_UNDER_TEST lets a mutated copy be shown red.
"""
import os, pathlib, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = os.environ.get("CHECK_INSTALL_UNDER_TEST", str(ROOT / "scripts" / "check_install.sh"))

def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                          check=True, capture_output=True, text=True).stdout.strip()

class TestCloneLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "agents").mkdir(parents=True); (self.rc / "skills" / "s").mkdir(parents=True)
        (self.rc / "agents" / "a.md").write_text("a\n"); (self.rc / "skills" / "s" / "SKILL.md").write_text("s\n")
        git(t, "init", "-q", "-b", "main", str(self.rc)); git(self.rc, "add", "-A"); git(self.rc, "commit", "-qm", "one")
        # The link target exists on this machine, so `dangling` passes — exactly the blind spot.
        (t / "shared").mkdir(); (t / "shared" / "profile.md").write_text("shared\n")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True); (self.p / ".claude" / "references").mkdir()
        os.symlink(self.rc / "skills" / "s", self.p / ".claude" / "skills" / "s")
        (self.p / ".gitignore").write_text(".claude/skills/*\n")
        (self.p / "notes.md").write_text("n\n")
        git(t, "init", "-q", "-b", "main", str(self.p))
    def tearDown(self): self.tmp.cleanup()

    def commit_link(self, target):
        os.symlink(target, self.p / ".claude" / "references" / "profile.md")
        git(self.p, "add", "-A"); git(self.p, "commit", "-qm", "link")

    def line(self):
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True).stdout
        return next((l for l in out.splitlines() if "[clone-links]" in l), ""), out

    def test_relative_link_out_of_the_repo_fails(self):
        self.commit_link("../../../shared/profile.md")
        l, out = self.line()
        self.assertTrue(l.startswith("FAIL [clone-links]"), out)
        self.assertIn(".claude/references/profile.md", out)
        self.assertIn("PASS [dangling]", out)  # the blind spot this criterion exists for

    def test_absolute_link_fails(self):
        self.commit_link(str(self.p.parent / "shared" / "profile.md"))
        self.assertTrue(self.line()[0].startswith("FAIL [clone-links]"), self.line()[1])

    def test_link_inside_the_repo_passes(self):
        self.commit_link("../../notes.md")
        self.assertTrue(self.line()[0].startswith("PASS [clone-links]"), self.line()[1])

    def test_real_file_passes(self):
        (self.p / ".claude" / "references" / "profile.md").write_text("copy\n")
        git(self.p, "add", "-A"); git(self.p, "commit", "-qm", "copy")
        self.assertTrue(self.line()[0].startswith("PASS [clone-links]"), self.line()[1])

if __name__ == "__main__": unittest.main()
