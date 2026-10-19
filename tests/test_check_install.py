"""check_install.sh's `branch` criterion — its four outcomes against a throwaway checkout.

The `detached at the lock SHA` branch was untested (rulings §5). A shared checkout that is
detached is only safe when it sits exactly where the project's lock says; anywhere else it
re-points every paper at an unrecorded pipeline. CHECK_INSTALL_UNDER_TEST lets a mutated copy
of the script be run against these tests to show each one red.
"""
import json, os, pathlib, subprocess, tempfile, unittest
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

class TestGitHooksPath(unittest.TestCase):
    """Task 12: the pre-commit gate is installed only when core.hooksPath names the linked
    directory AND that directory's pre-commit exists (a fresh worktree has the config, not the links)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "agents").mkdir(parents=True); (self.rc / "agents" / "a.md").write_text("a\n")
        (self.rc / "hooks" / "git").mkdir(parents=True); (self.rc / "hooks" / "git" / "pre-commit").write_text("#!/bin/sh\n")
        os.chmod(self.rc / "hooks" / "git" / "pre-commit", 0o755)
        (self.rc / "skills" / "s").mkdir(parents=True); (self.rc / "skills" / "s" / "SKILL.md").write_text("s\n")
        self.p = t / "proj"; (self.p / ".claude" / "hooks").mkdir(parents=True); git(t, "init", "-q", str(self.p))
        (self.p / ".claude" / "skills").mkdir(); os.symlink(self.rc / "skills" / "s", self.p / ".claude" / "skills" / "s")
    def tearDown(self): self.tmp.cleanup()
    def out(self):
        return subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True).stdout
    def line(self, check=""):
        return next((l for l in self.out().splitlines() if "[git-hooks-path]" in l), "")
    def link(self): os.symlink(self.rc / "hooks" / "git", self.p / ".claude" / "hooks" / "git")

    def test_unset_fails(self):
        self.link(); self.assertTrue(self.line().startswith("FAIL"), self.line())
    def test_other_path_fails(self):
        self.link(); git(self.p, "config", "core.hooksPath", ".githooks"); self.assertTrue(self.line().startswith("FAIL"), self.line())
    def test_missing_link_fails(self):
        git(self.p, "config", "core.hooksPath", ".claude/hooks/git"); self.assertTrue(self.line().startswith("FAIL"), self.line())
    def test_set_and_present_passes(self):
        self.link(); git(self.p, "config", "core.hooksPath", ".claude/hooks/git"); self.assertTrue(self.line().startswith("PASS"), self.line())
    def test_hooks_wired_fails_on_a_git_hook_command(self):
        (self.p / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
            {"hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/git/pre-commit"}]}]}}))
        l = next((x for x in self.out().splitlines() if "[hooks-wired]" in x), "")
        self.assertTrue(l.startswith("FAIL") and "git hook" in l, l)

class TestClaudeMdCaps(unittest.TestCase):
    """Task 13 (as released): a project CLAUDE.md over 60 lines, or one carrying design facts (a
    dated treatment or event, a hypothesis line), FAILs once the paper is retrofitted — its
    manuscript has a `design:` block — and WARNs before, so a re-link of an unretrofitted paper
    stays green (author ruling 2026-09-28: papers fix findings on their own schedule)."""
    DESIGN = "---\ntitle: T\ndesign:\n  hypotheses:\n    H1: {spec: m1}\n---\n\nBody.\n"
    PLAIN = "---\ntitle: T\n---\n\nBody.\n"
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "skills" / "s").mkdir(parents=True); (self.rc / "skills" / "s" / "SKILL.md").write_text("s\n")
        (self.rc / "agents").mkdir(); (self.rc / "agents" / "a.md").write_text("a\n")
        os.symlink(ROOT / "scripts", self.rc / "scripts")
        git(t, "init", "-q", "-b", "main", str(self.rc)); git(self.rc, "add", "-A"); git(self.rc, "commit", "-qm", "one")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True)
        os.symlink(self.rc / "skills" / "s", self.p / ".claude" / "skills" / "s")
    def tearDown(self): self.tmp.cleanup()
    def line(self, check, body, manuscript=None):
        if manuscript is not None:
            (self.p / "paper.qmd").write_text(manuscript); body = "manuscript: paper.qmd\n" + body
        (self.p / "CLAUDE.md").write_text(body)
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True).stdout
        return next((l for l in out.splitlines() if f"[{check}]" in l), "")

    def test_61_lines_fails_when_retrofitted(self):
        self.assertTrue(self.line("claude-md-size", "x\n" * 60, self.DESIGN).startswith("FAIL"))
    def test_61_lines_warns_when_not_retrofitted(self):
        l = self.line("claude-md-size", "x\n" * 60, self.PLAIN)
        self.assertTrue(l.startswith("WARN") and "design: block" in l, l)
        self.assertTrue(self.line("claude-md-size", "x\n" * 61).startswith("WARN"))   # no manuscript declared
    def test_60_lines_passes(self):
        self.assertTrue(self.line("claude-md-size", "x\n" * 59, self.DESIGN).startswith("PASS"))
    def test_treatment_date_fails_when_retrofitted(self):
        l = self.line("claude-md-design-facts", "# P\nTreatment date: 2024-10-01\n", self.DESIGN)
        self.assertTrue(l.startswith("FAIL") and "design:" in l, l)
    def test_treatment_date_warns_when_not_retrofitted(self):
        self.assertTrue(self.line("claude-md-design-facts", "# P\nTreatment date: 2024-10-01\n", self.PLAIN).startswith("WARN"))
    def test_hypothesis_line_fails_when_retrofitted(self):
        self.assertTrue(self.line("claude-md-design-facts", "# P\n- H1: prices fall\n", self.DESIGN).startswith("FAIL"))
    def test_clean_file_passes(self):
        l = self.line("claude-md-design-facts", "# P\nSee the 2024-10-01 session notes.\n", self.DESIGN)
        self.assertTrue(l.startswith("PASS"), l)

class TestHelpersCurrent(unittest.TestCase):
    """The pasted claim helpers must equal templates/claims-helpers.R.txt byte for byte."""
    TPL = (ROOT / "templates" / "claims-helpers.R.txt").read_text()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); t = pathlib.Path(self.tmp.name)
        self.rc = t / "rc"; (self.rc / "skills" / "s").mkdir(parents=True); (self.rc / "skills" / "s" / "SKILL.md").write_text("s\n")
        (self.rc / "agents").mkdir(); (self.rc / "agents" / "a.md").write_text("a\n")
        os.symlink(ROOT / "scripts", self.rc / "scripts"); os.symlink(ROOT / "templates", self.rc / "templates")
        git(t, "init", "-q", "-b", "main", str(self.rc)); git(self.rc, "add", "-A"); git(self.rc, "commit", "-qm", "one")
        self.p = t / "proj"; (self.p / ".claude" / "skills").mkdir(parents=True)
        os.symlink(self.rc / "skills" / "s", self.p / ".claude" / "skills" / "s")
        (self.p / "CLAUDE.md").write_text("manuscript: paper.qmd\n")
    def tearDown(self): self.tmp.cleanup()
    def line(self, manuscript):
        (self.p / "paper.qmd").write_text(manuscript)
        out = subprocess.run(["bash", SCRIPT, "--project-dir", str(self.p)], capture_output=True, text=True).stdout
        return next((l for l in out.splitlines() if "[helpers-current]" in l), "")
    def qmd(self, block, design=True):
        fm = "---\ntitle: T\n" + ("design:\n  hypotheses:\n    H1: {spec: m1}\n" if design else "") + "---\n"
        return fm + "\n```{r}\n#| label: setup\nlibrary(fixest)\n" + block + "\n```\n"
    def test_current_passes(self):
        self.assertTrue(self.line(self.qmd(self.TPL)).startswith("PASS"))
    def test_stale_paste_fails_and_names_its_version(self):
        old = self.TPL.replace('rc_helpers_version <- "', 'rc_helpers_version <- "2000-01-01.0').replace("rc_sig <- function(p) {", "rc_sig <- function(p) {  # edited")
        l = self.line(self.qmd(old)); self.assertTrue(l.startswith("FAIL") and "2000-01-01.0" in l, l)
    def test_not_retrofitted_without_block_passes(self):
        self.assertTrue(self.line(self.qmd("x <- 1", design=False)).startswith("PASS"))
    def test_design_block_without_helpers_warns(self):
        self.assertTrue(self.line(self.qmd("x <- 1")).startswith("WARN"))

if __name__ == "__main__": unittest.main()
