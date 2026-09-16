"""Contracts for hooks/session-guard.py.

Each case below is a command the careful guard claimed to block and did not, or blocked
and should not have. The guard is a safety net the user turns on deliberately; a pattern
that misses the form people actually type is worse than no pattern, because it reports
itself as active.
"""
import json, pathlib, subprocess, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "session-guard.py"


def run(tool_name, tool_input, guards, tmp):
    """Invoke the hook with a project dir whose session-guards.json is `guards`."""
    state = tmp / ".claude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "session-guards.json").write_text(json.dumps(guards))
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    p = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                       text=True, env={"CLAUDE_PROJECT_DIR": str(tmp), "PATH": "/usr/bin:/bin"})
    if not p.stdout.strip():
        return None
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]


CAREFUL_ON = {"careful": {"active": True}}


class TestCarefulBlocks(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def assertBlocked(self, cmd):
        self.assertEqual(run("Bash", {"command": cmd}, CAREFUL_ON, self.tmp), "deny", cmd)

    def assertAllowed(self, cmd):
        self.assertIsNone(run("Bash", {"command": cmd}, CAREFUL_ON, self.tmp), cmd)

    def test_force_push_with_a_refspec_is_blocked(self):
        """The plain `git push --force` form was the only one matched; nobody types it."""
        self.assertBlocked("git push origin main --force")
        self.assertBlocked("git push --force")
        self.assertBlocked("git push origin main -f")
        self.assertBlocked("git push origin main --force-with-lease")

    def test_find_delete_is_blocked(self):
        self.assertBlocked("find . -name '*.rds' -delete")
        self.assertBlocked("find . -type f -exec rm {} +")

    def test_rm_with_flags_before_the_recursive_flag_is_blocked(self):
        self.assertBlocked("rm -rf _cache")
        self.assertBlocked("rm -v -rf _cache")
        self.assertBlocked("rm --recursive _cache")

    def test_lowercase_branch_delete_is_allowed(self):
        """`git branch -d` refuses to delete an unmerged branch. IGNORECASE made it a denial."""
        self.assertAllowed("git branch -d feature/done")

    def test_ordinary_commands_are_allowed(self):
        self.assertAllowed("rm stale.log")
        self.assertAllowed("git push origin feature/x")
        self.assertAllowed("find . -name '*.qmd'")

    def test_sql_drops_stay_case_insensitive(self):
        self.assertBlocked("psql -c 'drop table users'")

    def test_deny_text_does_not_invite_a_workaround(self):
        text = HOOK.read_text()
        self.assertNotIn("rephrase the command", text)

    def test_hook_messages_address_the_user_not_the_model(self):
        """A hook that tells the model to run /freeze off is telling it to evade the guard."""
        text = HOOK.read_text()
        self.assertNotIn("Run /freeze off", text)
        self.assertNotIn("Run /careful off", text)


class TestFreezeDocumentedPathWorks(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_guard_file_is_not_editable_while_frozen(self):
        """Deliberate (hook line 55). Pinned so nobody 'fixes' it into a self-unfreeze hole."""
        guards = {"freeze": {"active": True, "allowed_paths": ["explorations/"]}}
        target = str(self.tmp / ".claude" / "state" / "session-guards.json")
        self.assertEqual(run("Edit", {"file_path": target}, guards, self.tmp), "deny")

    def test_freeze_skill_does_not_document_an_edit_to_deactivate(self):
        """Because the Edit above is denied, /freeze off must be documented as a Bash write."""
        skill = (ROOT / "skills" / "freeze" / "SKILL.md").read_text()
        self.assertIn("session-guards.json", skill)
        self.assertIn("python3", skill, "/freeze off must be documented as a Bash write")

    def test_both_guard_skills_preserve_the_other_key(self):
        for name in ("freeze", "careful"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text()
            self.assertIn("json.loads", text,
                          f"/{name} must read-modify-write session-guards.json, not overwrite it")

    def test_neither_skill_claims_the_guard_resets_itself(self):
        for name in ("freeze", "careful"):
            for f in (ROOT / "skills" / name / "SKILL.md",
                      ROOT / "skills" / name / "gotchas.md"):
                if f.exists():
                    self.assertNotIn("resets when the conversation ends", f.read_text(), str(f))


if __name__ == "__main__":
    unittest.main()
