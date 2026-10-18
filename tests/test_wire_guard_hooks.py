"""Tests for scripts/wire_guard_hooks.py — the UserPromptSubmit group has no matcher key."""
import pathlib, subprocess, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wire_guard_hooks as wgh


class TestWire(unittest.TestCase):
    def test_adds_matcherless_user_prompt_group(self):
        s = {"hooks": {}}
        wgh.wire(s)
        groups = s["hooks"]["UserPromptSubmit"]
        self.assertEqual(len(groups), 1)
        self.assertNotIn("matcher", groups[0])
        self.assertIn("design-token.py", groups[0]["hooks"][0]["command"])

    def test_second_wire_adds_nothing(self):
        s = {"hooks": {}}
        wgh.wire(s)
        self.assertEqual(wgh.wire(s), 0)

    def test_widen_protect_files_matcher_to_bash(self):
        s = {"hooks": {"PreToolUse": [{"matcher": "Edit|Write", "hooks": [
            {"type": "command", "command": "x/run-hook.sh protect-files.sh"}]}]}}
        self.assertEqual(wgh.widen(s), 1)
        self.assertEqual(s["hooks"]["PreToolUse"][0]["matcher"], "Edit|Write|Bash")
        self.assertEqual(wgh.widen(s), 0)

    def test_wire_adds_design_guard_once(self):
        s = {"hooks": {}}
        wgh.wire(s)
        cmds = [h["command"] for g in s["hooks"]["PreToolUse"] for h in g["hooks"]]
        self.assertEqual(sum("design-guard.py" in c for c in cmds), 1)

    def test_git_hook_is_refused(self):
        code = ("import sys; sys.path.insert(0, %r); import wire_guard_hooks as w\n"
                "w.WANTED.append(('PreToolUse', 'Bash', 'git/pre-commit'))\n"
                "w.check_wanted()\n" % str(ROOT / "scripts"))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ValueError", r.stderr)


if __name__ == "__main__":
    unittest.main()
