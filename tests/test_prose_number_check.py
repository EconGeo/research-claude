"""prose_number_check.py — where the allowlist is, and what it means when it isn't there.

Both behaviours under test were found the hard way on 2026-09-10. The scanner
resolved its default allowlist beside the MANUSCRIPT, but `quality_reports/` is a
PROJECT directory — `pipeline_state.json`, `agent_dispatch.jsonl`, `reviews/` and
this allowlist all live at the project root, and `quarto-empirical.md` calls the
allowlist "per-project". A project that keeps its manuscript in `paper/` therefore
had its allowlist read from `paper/quality_reports/`, found nothing, and was told
all 41 of its literals were unexplained.

The second half is the more dangerous one. A missing allowlist and an allowlist
that does not cover a literal produced the SAME message. One project's 54
"unexplained literals" were all adjudicated, with written reasons, in a file the
scanner never opened. Reporting "no allowlist at X" and "this literal is not in
your allowlist" identically is the failure R-135 names: the gate stated a
property it had not tested.
"""
import pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "prose_number_check.py"

QMD = """---
title: "Fixture"
---

# Body

The settlement took effect on 17 August 2024, and Section 4 returns to it.
"""

# "2024," carries its comma: the scanner keys on the literal as it appears in the
# prose, which is why a real allowlist carries both `2024` and `2024,` rows.
ALLOW = 'literal,reason\n17,"Day of month in a verified date."\n"2024,",Calendar year followed by a comma.\n4,Section cross-reference.\n'


def run(*args):
    p = subprocess.run([sys.executable, str(CHECK), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class Case(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.t)

    def project(self, sub=""):
        """A pipeline project: a .claude/ at the root, the manuscript at `sub`."""
        (self.t / ".claude").mkdir(exist_ok=True)
        d = self.t / sub if sub else self.t
        d.mkdir(parents=True, exist_ok=True)
        qmd = d / "manuscript_fixture.qmd"
        qmd.write_text(QMD)
        return qmd

    def allowlist(self, at):
        p = self.t / at / "quality_reports" / "prose_number_allowlist.csv" if at \
            else self.t / "quality_reports" / "prose_number_allowlist.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(ALLOW)
        return p


class TestDefaultResolution(Case):
    def test_manuscript_at_project_root(self):
        """The common layout, unchanged: manuscript and quality_reports/ side by side."""
        qmd = self.project()
        self.allowlist("")
        rc, out = run(str(qmd))
        self.assertEqual(rc, 0, out)

    def test_manuscript_in_subdirectory_reads_the_project_allowlist(self):
        """A manuscript kept in a subdirectory: the allowlist is at the PROJECT root."""
        qmd = self.project("paper")
        self.allowlist("")
        rc, out = run(str(qmd))
        self.assertEqual(rc, 0, out)
        self.assertIn(str(self.t / "quality_reports"), out)

    def test_outside_a_project_falls_back_to_the_manuscript_directory(self):
        """No .claude/ above it, so there is no project root to resolve from."""
        d = self.t / "loose"
        d.mkdir()
        qmd = d / "manuscript_fixture.qmd"
        qmd.write_text(QMD)
        p = d / "quality_reports" / "prose_number_allowlist.csv"
        p.parent.mkdir(parents=True)
        p.write_text(ALLOW)
        rc, out = run(str(qmd))
        self.assertEqual(rc, 0, out)


class TestMissingAllowlist(Case):
    def test_absent_allowlist_is_reported_as_absent(self):
        """Not the same finding as 'this literal is not in your allowlist'."""
        qmd = self.project()
        rc, out = run(str(qmd))
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", out)

    def test_absent_allowlist_with_no_literals_still_passes(self):
        """A project with no prose numbers needs no allowlist."""
        qmd = self.project()
        qmd.write_text("---\ntitle: \"x\"\n---\n\n# Body\n\nNo numbers here at all.\n")
        rc, out = run(str(qmd))
        self.assertEqual(rc, 0, out)

    def test_present_allowlist_says_nothing_about_existence(self):
        """The note must not fire when the file is there and simply lacks a row."""
        qmd = self.project()
        p = self.t / "quality_reports" / "prose_number_allowlist.csv"
        p.parent.mkdir(parents=True)
        p.write_text("literal,reason\n17,Day of month.\n")
        rc, out = run(str(qmd))
        self.assertEqual(rc, 1)
        self.assertNotIn("does not exist", out)


class TestExplicitPath(Case):
    def test_explicit_path_wins_over_the_default(self):
        qmd = self.project("paper")
        elsewhere = self.t / "somewhere" / "allow.csv"
        elsewhere.parent.mkdir(parents=True)
        elsewhere.write_text(ALLOW)
        rc, out = run(str(qmd), str(elsewhere))
        self.assertEqual(rc, 0, out)

    def test_explicit_path_that_does_not_exist_is_a_usage_error(self):
        """A named file that is not there is a typo, not an empty allowlist."""
        qmd = self.project()
        rc, out = run(str(qmd), str(self.t / "no_such_allowlist.csv"))
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main()
