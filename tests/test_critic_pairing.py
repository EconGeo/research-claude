import contextlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest, pathlib
from unittest import mock
ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "critic-pairing.py"

def _load_critic_pairing():
    spec = importlib.util.spec_from_file_location("critic_pairing", ROOT / "hooks" / "critic-pairing.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class FixtureCase(unittest.TestCase):
    """A linked-fixture project plus an isolated HOME (R-114) so the hook's sentinel file
    under Path.home()/.claude/sessions/ never touches the developer's real home directory.
    HOME is mocked via os.environ, not a shell assignment, so it stays entirely in-process."""
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "tests" / "fixture-project", self.t, dirs_exist_ok=True)
        (self.t / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.t / ".claude" / "rules").mkdir(parents=True, exist_ok=True)
        (self.t / "quality_reports").mkdir(parents=True, exist_ok=True)
        os.symlink(ROOT / "scripts" / "registry_lib.py", self.t / ".claude" / "scripts" / "registry_lib.py")
        os.symlink(ROOT / "rules" / "registry.yaml", self.t / ".claude" / "rules" / "registry.yaml")
        self.home = pathlib.Path(tempfile.mkdtemp())
    def tearDown(self):
        shutil.rmtree(self.t); shutil.rmtree(self.home)
    def run_hook(self, payload_text):
        mod = _load_critic_pairing()
        buf = io.StringIO()
        env = {"CLAUDE_PROJECT_DIR": str(self.t), "HOME": str(self.home)}
        with contextlib.redirect_stdout(buf), \
             mock.patch.object(sys, "stdin", io.StringIO(payload_text)), \
             mock.patch.dict(os.environ, env):
            rc = mod.main()
        return rc, buf.getvalue()

class TestFailOpen(FixtureCase):
    """Fix round 1, Finding 1: three uncaught crashes in the brief's reference code, all
    violating the fail-open contract this hook's own docstring states. A crashing Stop
    hook shows a `<hook name> hook error` banner on every Stop event, not silence."""

    def test_non_object_stdin_does_not_crash(self):
        """1a-sibling: valid JSON that isn't an object must not reach `inp.get(...)`."""
        for bad in ("[1,2,3]", "42", '"text"', "null"):
            rc, out = self.run_hook(bad)
            self.assertEqual(rc, 0, f"payload {bad!r} should fail open with rc 0")
            self.assertEqual(out, "")

    def test_non_object_log_line_is_skipped_rest_of_file_still_evaluated(self):
        """1a: a log line that is valid JSON but not an object (`42`) must not crash
        `e.get(...)` — and the lines around it must still be read correctly."""
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        log.write_text("42\n" + json.dumps({"at": "2026-09-10T00:00:00.000+00:00", "agent": "coder"}) + "\n")
        rc, out = self.run_hook(json.dumps({"session_id": "s1", "cwd": str(self.t)}))
        self.assertEqual(rc, 0)
        self.assertIn('"decision": "block"', out)
        self.assertIn("coder", out)

    def test_registry_missing_agents_key_fails_open(self):
        """1c: registry_lib.creators(reg) sits outside the try that wraps the registry
        read. A registry.yaml that parses cleanly but has no agents: block (mid-edit,
        mid-merge-conflict) must not raise KeyError out of the hook."""
        reg_path = self.t / ".claude" / "rules" / "registry.yaml"
        reg_path.unlink()
        reg_path.write_text("schema_version: 1\ncomponents:\n  code:\n    weight: 1.0\n")
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        log.write_text(json.dumps({"at": "2026-09-10T00:00:00.000+00:00", "agent": "coder", "session": "s1"}) + "\n")
        rc, out = self.run_hook(json.dumps({"session_id": "s1", "cwd": str(self.t)}))
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_log_line_missing_at_key_does_not_crash(self):
        """Fix round 2, Finding a: hooks/critic-pairing.py:72-73 — a log line that IS a
        dict (passes the isinstance guard) but has no "at" key crashes `e["at"]` inside
        the max(...) generator. `python3 -c` reproduction with the guard temporarily
        removed (documented in the round-2 report) showed the real KeyError; this asserts
        the shipped hook (both its own main()->_run() wrapper and the outer
        if __name__ == "__main__" backstop) never lets it out."""
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        log.write_text(json.dumps({"agent": "coder"}) + "\n")  # valid dict, no "at"
        rc, out = self.run_hook(json.dumps({"session_id": "s1", "cwd": str(self.t)}))
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

class TestEmptySessionId(FixtureCase):
    """Fix round 1, Finding 2: the sentinel key is "<sid>:<creator>", keyed by project hash
    only. An empty sid collapses every session's incident onto the same ":<creator>" token,
    so a later session's genuinely new unpaired creator would find its block already spent.
    Fail toward noticing: with no session id, always block and never write a sentinel."""
    def _log_unpaired_coder(self):
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        with log.open("a") as f:
            f.write(json.dumps({"at": "2026-09-10T00:00:00.000+00:00", "agent": "coder", "session": ""}) + "\n")

    def test_empty_sid_blocks_every_time(self):
        self._log_unpaired_coder()
        payload = json.dumps({"session_id": "", "cwd": str(self.t)})
        rc1, out1 = self.run_hook(payload)
        rc2, out2 = self.run_hook(payload)
        self.assertEqual(rc1, 0); self.assertEqual(rc2, 0)
        self.assertIn('"decision": "block"', out1)
        self.assertIn('"decision": "block"', out2)

    def test_empty_sid_writes_no_sentinel(self):
        self._log_unpaired_coder()
        self.run_hook(json.dumps({"session_id": "", "cwd": str(self.t)}))
        sessions = self.home / ".claude" / "sessions"
        found = list(sessions.rglob("critic-pairing-blocked.json")) if sessions.exists() else []
        self.assertEqual(found, [])

class TestOuterBackstopEndToEnd(FixtureCase):
    """Fix round 2 (R-115): hooks/critic-pairing.py's own `if __name__ == "__main__":`
    block now carries the house fail-open idiom (see hooks/log-reminder.py and four other
    shipped hooks). Both findings below sit inside `_run()`, which `main()` already wraps
    in its own try/except — so through the real script entry point these already returned
    rc 0 even before this round's change (confirmed directly; see the round-2 report). The
    outer idiom is a second, independent layer for when that internal wrapper is ever
    bypassed or refactored away, so these tests exercise the actual entry point
    (subprocess) rather than an in-process `main()` call, which cannot reach the
    `if __name__` block at all."""
    def _run_subprocess(self, payload, home):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.t)
        env["HOME"] = str(home)
        return subprocess.run([sys.executable, str(HOOK)], input=payload,
                               capture_output=True, text=True, env=env)

    def test_missing_at_key_end_to_end(self):
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        log.write_text(json.dumps({"agent": "coder"}) + "\n")
        p = self._run_subprocess(json.dumps({"session_id": "s1", "cwd": str(self.t)}), self.home)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")

    def test_unwritable_home_end_to_end(self):
        """Finding b: session_dir()'s mkdir(parents=True, exist_ok=True) sits outside any
        try. A read-only HOME reproduces the real PermissionError (see round-2 report for
        the traceback); skipped when running as root, since root ignores POSIX
        permission bits and the reproduction wouldn't mean anything."""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission bits are meaningless as root")
        log = self.t / "quality_reports" / "agent_dispatch.jsonl"
        log.write_text(json.dumps({"at": "2026-09-10T00:00:00.000+00:00", "agent": "coder"}) + "\n")
        readonly_home = pathlib.Path(tempfile.mkdtemp())
        os.chmod(readonly_home, 0o555)
        try:
            p = self._run_subprocess(json.dumps({"session_id": "s1", "cwd": str(self.t)}), readonly_home)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stderr, "")
        finally:
            os.chmod(readonly_home, 0o755)
            shutil.rmtree(readonly_home)

if __name__ == "__main__": unittest.main()
