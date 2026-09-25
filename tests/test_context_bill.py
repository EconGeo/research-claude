import json, subprocess, sys, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "context_bill.py"

def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=cwd or ROOT)

class TestContextBillCli(unittest.TestCase):
    """Mirrors scripts/audit_graph.py's own CLI test shape (tests/test_audit_graph.py) —
    same footgun class: a script that dies on a missing positional arg before it ever
    audits anything."""

    def test_no_arguments_audits_this_checkout(self):
        r = run(cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("skills loaded into every session", r.stdout)

    def test_root_and_json_writes_the_full_report(self):
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "bill.json"
            r = run(str(ROOT), "--json", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            report = json.loads(out.read_text())
            self.assertIn("skills", report)
            self.assertIn("directories", report)
            self.assertIn("est_tokens", report["skills"][0])

    def test_json_only_written_when_asked(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(str(ROOT), cwd=t)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(list(pathlib.Path(t).iterdir()), [])

    def test_top_flag_limits_the_largest_files_list(self):
        r = run(str(ROOT), "--top", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        # Count numbered lines under the "Largest files" heading.
        after = r.stdout.split("Largest files")[1]
        numbered = [ln for ln in after.splitlines() if ln.strip()[:2].rstrip(".").isdigit()]
        self.assertLessEqual(len(numbered), 3)

    def test_skills_are_sorted_by_est_tokens_descending(self):
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t) / "bill.json"
            run(str(ROOT), "--json", str(out))
            report = json.loads(out.read_text())
            tokens = [s["est_tokens"] for s in report["skills"]]
            self.assertEqual(tokens, sorted(tokens, reverse=True))

    def test_help_is_usage_not_a_scan(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage", r.stdout.lower())
