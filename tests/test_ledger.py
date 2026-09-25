"""Cross-project improvement ledger (P6, plan 2026-09-25).

A correction recorded in one project's SESSION_REPORT dies there. The ledger is the one place
/checkpoint writes candidates to and /promote reads them from; `show` flags a target named by
REPEATED_AT distinct projects.
"""
import pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ledger.py"


def run(*args, ledger):
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--ledger", str(ledger)],
                          capture_output=True, text=True)


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = pathlib.Path(self.tmp.name) / "improvement-ledger.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_creates_the_file_with_header_and_returns_sequential_ids(self):
        r1 = run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "first",
                 "--date", "2026-09-25", ledger=self.ledger)
        r2 = run("add", "--project", "beta", "--target", "rules/x.md", "--note", "second",
                 "--date", "2026-09-26", ledger=self.ledger)
        self.assertEqual(0, r1.returncode, r1.stderr)
        self.assertEqual("L-001", r1.stdout.strip())
        self.assertEqual("L-002", r2.stdout.strip())
        text = self.ledger.read_text()
        self.assertIn("| id | date | project | target | note | status |", text)
        self.assertIn("| L-002 | 2026-09-26 | beta | rules/x.md | second | open |", text)

    def test_add_is_append_only(self):
        run("add", "--project", "a", "--target", "t", "--note", "n", ledger=self.ledger)
        before = self.ledger.read_text()
        run("add", "--project", "b", "--target", "t", "--note", "m", ledger=self.ledger)
        self.assertTrue(self.ledger.read_text().startswith(before))

    def test_pipe_in_note_is_escaped_so_the_table_survives(self):
        run("add", "--project", "a", "--target", "t", "--note", "x | y", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertIn("x \\| y", self.ledger.read_text())
        self.assertIn("t", r.stdout)

    def test_show_groups_by_target_and_flags_two_distinct_projects(self):
        run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "a", ledger=self.ledger)
        run("add", "--project", "alpha", "--target", "rules/x.md", "--note", "b", ledger=self.ledger)
        run("add", "--project", "gamma", "--target", "agents/y.md", "--note", "c", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertNotIn("REPEATED", r.stdout, "same project twice is not repeated")
        run("add", "--project", "beta", "--target", "rules/x.md", "--note", "d", ledger=self.ledger)
        r = run("show", ledger=self.ledger)
        self.assertRegex(r.stdout, r"rules/x\.md.*projects=2.*REPEATED")
        self.assertRegex(r.stdout, r"agents/y\.md.*projects=1")

    def test_mark_landed_and_declined_change_status_and_open_hides_them(self):
        run("add", "--project", "a", "--target", "t1", "--note", "n", ledger=self.ledger)
        run("add", "--project", "b", "--target", "t2", "--note", "n", ledger=self.ledger)
        r = run("mark", "L-001", "landed", "abc1234", ledger=self.ledger)
        self.assertEqual(0, r.returncode, r.stderr)
        r = run("mark", "L-002", "declined", "project-specific", ledger=self.ledger)
        self.assertEqual(0, r.returncode, r.stderr)
        text = self.ledger.read_text()
        self.assertIn("| landed abc1234 |", text)
        self.assertIn("| declined: project-specific |", text)
        r = run("show", "--open", ledger=self.ledger)
        self.assertNotIn("t1", r.stdout)
        self.assertNotIn("t2", r.stdout)

    def test_mark_unknown_id_exits_2(self):
        run("add", "--project", "a", "--target", "t", "--note", "n", ledger=self.ledger)
        r = run("mark", "L-009", "landed", "abc", ledger=self.ledger)
        self.assertEqual(2, r.returncode)

    def test_show_on_missing_ledger_is_empty_not_an_error(self):
        r = run("show", ledger=self.ledger)
        self.assertEqual(0, r.returncode)
        self.assertIn("no rows", r.stdout)

    def test_ledger_is_shipped(self):
        self.assertIn("ledger.py", (ROOT / "scripts" / "SHIPPED").read_text().split())


if __name__ == "__main__":
    unittest.main()
