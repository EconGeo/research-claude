"""Tests for hooks/script-guard.py and hooks/read-gate.py — piped payloads, as the hooks README asks."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_GUARD = ROOT / "hooks" / "script-guard.py"
READ_GATE = ROOT / "hooks" / "read-gate.py"


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.proj = pathlib.Path(tempfile.mkdtemp()).resolve()
        (self.proj / "CLAUDE.md").write_text("# P\n\nmanuscript: manuscript_p.qmd\n")
        self.ms = self.proj / "manuscript_p.qmd"
        self.ms.write_text("".join(f"line {i}\n" for i in range(1, 4501)))
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.session = f"test-{os.getpid()}-{id(self)}"

    def tearDown(self):
        shutil.rmtree(self.proj); shutil.rmtree(self.tmp)

    def run_hook(self, hook, payload):
        payload.setdefault("session_id", self.session)
        payload.setdefault("cwd", str(self.proj))
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.proj), TMPDIR=str(self.tmp))
        r = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def denied(self, out):
        return bool(out) and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestScriptGuard(ProjectCase):
    def write(self, rel):
        return self.run_hook(SCRIPT_GUARD, {"hook_event_name": "PreToolUse", "tool_name": "Write",
                                            "tool_input": {"file_path": str(self.proj / rel), "content": "x"}})

    def bash(self, cmd):
        return self.run_hook(SCRIPT_GUARD, {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                            "tool_input": {"command": cmd}})

    def test_new_script_in_root_or_scripts_is_denied(self):
        for rel in ("model_test.R", "scripts/R/fit.R", "code/try.py", "analysis.Rmd"):
            self.assertTrue(self.denied(self.write(rel)), rel)

    def test_allowed_homes(self):
        for rel in ("explorations/hedonic.R", "explorations/sub/try.qmd", "explorations/x.py",
                    "scripts/acquire/01_get.py", ".claude/scripts/x.py", "notes.md",
                    "manuscript_p.qmd"):
            self.assertFalse(self.denied(self.write(rel)), rel)

    def test_outside_project_allowed(self):
        out = self.run_hook(SCRIPT_GUARD, {"hook_event_name": "PreToolUse", "tool_name": "Write",
                                           "tool_input": {"file_path": str(self.tmp / "scratch.R")}})
        self.assertFalse(self.denied(out))

    def test_existing_script_may_be_overwritten(self):
        (self.proj / "legacy.R").write_text("1\n")
        self.assertFalse(self.denied(self.write("legacy.R")))

    def test_bash_creation_forms(self):
        for cmd in ("cat > fit.R <<'EOF'\nx <- 1\nEOF", "echo 1 >> code/a.py", "touch b.R",
                    "printf x | tee c.jl", "cp explorations/a.R d.R", "Rscript -e '1' && touch e.R"):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)

    def test_bash_harmless(self):
        for cmd in ("Rscript explorations/a.R", "quarto render manuscript_p.qmd 2>&1 | tail -5",
                    "echo hi > explorations/out.R", "ls > /dev/null", "cat x.R"):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)

    def test_inactive_without_manuscript_declaration(self):
        (self.proj / "CLAUDE.md").write_text("# no declaration\n")
        self.assertFalse(self.denied(self.write("model_test.R")))

    def test_garbage_input_fails_open(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.proj))
        for bad in ("", "[1]", "not json"):
            r = subprocess.run([sys.executable, str(SCRIPT_GUARD)], input=bad, capture_output=True,
                               text=True, env=env)
            self.assertEqual((r.returncode, r.stdout), (0, ""))


class TestReadGate(ProjectCase):
    def read(self, offset=None, limit=None, agent=None, response=True):
        ti = {"file_path": str(self.ms)}
        if offset: ti["offset"] = offset
        if limit: ti["limit"] = limit
        p = {"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": ti}
        if response:
            start = max(offset or 1, 1); n = min(limit or 2000, 4500 - start + 1)
            p["tool_response"] = {"type": "text", "file": {"filePath": str(self.ms), "startLine": start,
                                                           "numLines": n, "totalLines": 4500}}
        if agent: p["agent_id"] = agent
        return self.run_hook(READ_GATE, p)

    def edit(self, agent=None, post=False):
        p = {"hook_event_name": "PostToolUse" if post else "PreToolUse", "tool_name": "Edit",
             "tool_input": {"file_path": str(self.ms), "old_string": "a", "new_string": "b"}}
        if agent: p["agent_id"] = agent
        return self.run_hook(READ_GATE, p)

    def full_read(self, agent=None, response=True):
        for off in (1, 2001, 4001):
            self.read(off, 2000, agent, response)

    def test_edit_without_read_denied(self):
        out = self.edit()
        self.assertTrue(self.denied(out))
        self.assertIn("1-4500", out)

    def test_default_read_is_partial(self):
        self.read()
        out = self.edit()
        self.assertTrue(self.denied(out))
        self.assertIn("2001-4500", out)

    def test_chunked_full_read_allows_edit(self):
        self.full_read()
        self.assertFalse(self.denied(self.edit()))

    def test_fallback_to_offset_limit_without_response(self):
        self.full_read(response=False)
        self.assertFalse(self.denied(self.edit()))

    def test_own_edit_keeps_full_read_valid(self):
        self.full_read()
        self.ms.write_text(self.ms.read_text() + "added\n")  # the Edit tool's effect
        self.edit(post=True)
        self.assertFalse(self.denied(self.edit()))

    def test_outside_change_requires_reread(self):
        self.full_read()
        self.ms.write_text(self.ms.read_text() + "user edit in VS Code\n")
        out = self.edit()
        self.assertTrue(self.denied(out))
        self.assertIn("changed since", out)

    def test_subagent_must_read_for_itself(self):
        self.full_read()
        self.assertTrue(self.denied(self.edit(agent="writer-1")))
        self.full_read(agent="writer-1")
        self.assertFalse(self.denied(self.edit(agent="writer-1")))

    def test_bash_inplace_write_gated_render_not(self):
        sed = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": "sed -i '' 's/a/b/' manuscript_p.qmd"}}
        render = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                  "tool_input": {"command": "quarto render manuscript_p.qmd --quiet"}}
        self.assertTrue(self.denied(self.run_hook(READ_GATE, sed)))
        self.assertFalse(self.denied(self.run_hook(READ_GATE, render)))

    def test_other_files_not_gated(self):
        p = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
             "tool_input": {"file_path": str(self.proj / "explorations" / "a.qmd")}}
        self.assertFalse(self.denied(self.run_hook(READ_GATE, p)))

    def test_new_manuscript_creation_allowed(self):
        self.ms.unlink()
        p = {"hook_event_name": "PreToolUse", "tool_name": "Write",
             "tool_input": {"file_path": str(self.ms), "content": "x"}}
        self.assertFalse(self.denied(self.run_hook(READ_GATE, p)))


if __name__ == "__main__":
    unittest.main()
