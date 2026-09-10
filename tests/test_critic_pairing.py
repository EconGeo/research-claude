import contextlib, importlib.util, io, json, os, shutil, sys, tempfile, unittest, pathlib
from unittest import mock
ROOT = pathlib.Path(__file__).resolve().parents[1]

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

if __name__ == "__main__": unittest.main()
