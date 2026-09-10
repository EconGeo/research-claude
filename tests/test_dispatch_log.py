import importlib.util, io, os, re, shutil, sys, tempfile, unittest, pathlib
from unittest import mock
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline

def _load_dispatch_log():
    spec = importlib.util.spec_from_file_location("dispatch_log", ROOT / "hooks" / "dispatch-log.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")

class TestTimestampAgreement(unittest.TestCase):
    """R-109: dispatch-log.py's timestamp must be pipeline.py's `now()` format exactly —
    UTC, explicit +00:00 offset, millisecond precision — not naive local time at second
    resolution. `critic-ran` string-compares an `at` from each file directly."""
    def test_dispatch_log_now_matches_pipeline_now_format(self):
        dispatch_log = _load_dispatch_log()
        a, b = pipeline.now(), dispatch_log.now()
        self.assertRegex(a, TS_RE)
        self.assertRegex(b, TS_RE)
    def test_dispatch_log_now_falls_back_when_import_fails(self):
        """The fallback path (pipeline.py import fails) must ALSO match the format —
        it is the identical inline expression, not a second implementation to drift."""
        dispatch_log = _load_dispatch_log()
        orig_path = sys.path[:]
        try:
            # Simulate the sibling scripts/pipeline.py being unimportable.
            import builtins
            real_import = builtins.__import__
            def blocked(name, *a, **kw):
                if name == "pipeline":
                    raise ImportError("simulated: pipeline.py not importable")
                return real_import(name, *a, **kw)
            builtins.__import__ = blocked
            try:
                b = dispatch_log.now()
            finally:
                builtins.__import__ = real_import
        finally:
            sys.path[:] = orig_path
        self.assertRegex(b, TS_RE)

class TestFailOpen(unittest.TestCase):
    """Fix round 1, Finding 1b: valid JSON that decodes to a non-object (`[1,2,3]`, `42`,
    `"text"`, `null`) must not crash `inp.get(...)`. A crashing Stop/SubagentStop hook
    shows the user a `<hook name> hook error` banner on every event, not silence."""
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
    def tearDown(self):
        shutil.rmtree(self.t)
    def test_non_object_stdin_does_not_crash_and_writes_nothing(self):
        dispatch_log = _load_dispatch_log()
        for bad in ("[1,2,3]", "42", '"text"', "null"):
            with mock.patch.object(sys, "stdin", io.StringIO(bad)), \
                 mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.t)}):
                rc = dispatch_log.main()
            self.assertEqual(rc, 0, f"payload {bad!r} should fail open with rc 0")
        self.assertFalse((self.t / "quality_reports" / "agent_dispatch.jsonl").exists())

if __name__ == "__main__": unittest.main()
