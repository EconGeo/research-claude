import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "seeds" / "run-hook.sh"
sys.path.insert(0, str(ROOT / "scripts"))
import wrap_hooks

def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *a],
                   check=True, capture_output=True)

class TestRunHook(unittest.TestCase):
    """2026-09-29: the desktop app's git worktree of a paper repo has tracked settings.json but
    none of the untracked .claude/hooks/ links, so PreToolUse session-guard.py failed every tool
    call. The launcher is tracked, so it is the one piece that exists in a fresh worktree."""
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.main = self.t / "main"; self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        (self.main / ".claude").mkdir()
        shutil.copy(LAUNCHER, self.main / ".claude" / "run-hook.sh")
        (self.main / ".claude" / "run-hook.sh").chmod(0o755)
        git(self.main, "add", "-A"); git(self.main, "commit", "-qm", "init")
        hooks = self.main / ".claude" / "hooks"; hooks.mkdir()          # untracked, like the real links
        (hooks / "echo-env.py").write_text(
            "import os,sys; print(os.environ['CLAUDE_PROJECT_DIR'], sys.stdin.read().strip(), *sys.argv[1:])\n")
        (hooks / "sh-hook.sh").write_text("#!/usr/bin/env bash\necho sh:$1\n"); (hooks / "sh-hook.sh").chmod(0o755)
        self.wt = self.t / "wt"
        git(self.main, "worktree", "add", "-q", str(self.wt))
    def tearDown(self): shutil.rmtree(self.t)
    def run_launcher(self, project, *args, stdin=""):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
        return subprocess.run([str(project / ".claude" / "run-hook.sh"), *args], input=stdin,
                              capture_output=True, text=True, env=env)

    def test_worktree_has_no_hooks_dir_but_launcher(self):
        self.assertFalse((self.wt / ".claude" / "hooks").exists())
        self.assertTrue((self.wt / ".claude" / "run-hook.sh").exists())

    def test_linked_case_runs_hook_in_project(self):
        p = self.run_launcher(self.main, "echo-env.py", "x", stdin="in")
        self.assertEqual((p.returncode, p.stdout.strip()), (0, f"{self.main} in x"))

    def test_worktree_falls_back_to_main_and_keeps_worktree_as_project_dir(self):
        p = self.run_launcher(self.wt, "echo-env.py", stdin="in")
        self.assertEqual((p.returncode, p.stdout.strip()), (0, f"{self.wt} in"))

    def test_shell_hook_is_exec_not_python(self):
        p = self.run_launcher(self.wt, "sh-hook.sh", "a")
        self.assertEqual(p.stdout.strip(), "sh:a")

    def test_missing_everywhere_fails_open_with_repair_hint(self):
        p = self.run_launcher(self.wt, "nope.py")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")
        self.assertIn("apply.sh", p.stderr)

class TestWrapHooks(unittest.TestCase):
    def test_seed_settings_all_routed_and_valid_json(self):
        text = (ROOT / "seeds" / "settings.json").read_text()
        cmds = [h["command"] for v in json.loads(text)["hooks"].values() for g in v for h in g["hooks"]]
        self.assertEqual(len(cmds), 12)
        for c in cmds:
            self.assertRegex(c, r'^"\$CLAUDE_PROJECT_DIR"/\.claude/run-hook\.sh [\w.-]+$')

    def test_rewrite_is_idempotent_and_preserves_other_text(self):
        raw = ('{\n  "a": 1,\n  "command": "python3 \\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/x.py",\n'
               '  "c2": "\\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/y.sh"\n}')
        once, n = wrap_hooks.wrap(raw)
        self.assertEqual(n, 2)
        self.assertEqual(json.loads(once)["command"], '"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh x.py')
        self.assertEqual(wrap_hooks.wrap(once), (once, 0))

if __name__ == "__main__": unittest.main()
