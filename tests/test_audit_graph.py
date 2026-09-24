import json, subprocess, sys, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_graph.py"

def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=cwd or ROOT)

class TestAuditGraphCli(unittest.TestCase):
    """audit_graph.py took both its arguments positionally with no defaults, so the obvious
    invocation — `python3 scripts/audit_graph.py` — died on sys.argv[1] with an IndexError
    traceback, and `audit_graph.py .` got through the whole scan and THEN died on sys.argv[2].
    Every documented run passed an output path nobody reads. ROOT now defaults to the checkout
    the script lives in, and the JSON report is written only when a path is given."""

    def test_no_arguments_audits_this_checkout(self):
        r = run(cwd=tempfile.gettempdir())   # cwd deliberately elsewhere: the default is the checkout
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn(f"{ROOT.name}: ", r.stdout)
        self.assertIn("dangling path refs", r.stdout)

    def test_root_only_prints_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(str(ROOT), cwd=t)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("dangling path refs", r.stdout)
            self.assertEqual(list(pathlib.Path(t).iterdir()), [])

    def test_root_and_out_writes_the_json_report(self):
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "g.json"
            r = run(str(ROOT), str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            report = json.loads(out.read_text())
            self.assertIn("dangling_paths", report)
            self.assertEqual(report["root"], str(ROOT))

    def test_help_is_usage_not_a_scan(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage:", r.stdout.lower())
        # The summary row, not the phrase: the help text itself describes "dangling path refs".
        self.assertNotIn("dangling path refs        :", r.stdout)

    def test_missing_root_is_a_usage_error(self):
        r = run("/nonexistent/audit-graph-root")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

class TestAuditGraphLogic(unittest.TestCase):
    """Logic-level regression, not CLI plumbing (TestAuditGraphCli above only exercises argv
    handling). Found 2026-09-24: rules/agents.md names agents/civilize-auditor.md, a real file
    that lives at ai-audit/agents/civilize-auditor.md — audit_graph.py reported it dangling
    because it never tried the vendored-tree alias registry_lib.AGENT_DIRS already knows."""

    def test_vendored_agent_reference_resolves(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text("See agents/probe-agent.md for the contract.\n")
            (root / "ai-audit" / "agents").mkdir(parents=True)
            (root / "ai-audit" / "agents" / "probe-agent.md").write_text("---\ntools: Read\n---\n")
            r = run(str(root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("dangling path refs        : 0", r.stdout)

    def test_genuinely_dangling_path_still_caught(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text("See agents/does-not-exist.md.\n")
            r = run(str(root))
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("dangling path refs        : 1", r.stdout)

    def test_real_tree_has_zero_dangling_paths(self):
        r = run(str(ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("dangling path refs        : 0", r.stdout)


if __name__ == "__main__": unittest.main()
