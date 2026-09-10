import importlib.util, re, sys, unittest, pathlib
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

if __name__ == "__main__": unittest.main()
