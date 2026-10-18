"""prose_number_check.py -- the surfaces that render but were not scanned.

YAML title/subtitle/abstract, decimals in math, R table notes, a response
letter. The fixed star legend is not a literal. Applies to every paper.
"""
import pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "prose_number_check.py"
FIXTURE = ROOT / "tests" / "fixture-project" / "manuscript_fixture.qmd"


class Case(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.t)

    def run_check(self, text, claude=None, extra=None):
        qmd = self.t / "manuscript_fixture.qmd"
        qmd.write_text(text)
        a = self.t / "quality_reports" / "prose_number_allowlist.csv"
        a.parent.mkdir(exist_ok=True)
        a.write_text("literal,reason\n")
        if claude is not None:
            (self.t / "CLAUDE.md").write_text(claude)
        for name, body in (extra or {}).items():
            (self.t / name).write_text(body)
        p = subprocess.run([sys.executable, str(CHECK), str(qmd)],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def body(self, body, head='title: "x"'):
        return self.run_check(f"---\n{head}\n---\n\n{body}")


class TestYaml(Case):
    def test_abstract_block_is_scanned(self):
        rc, out = self.body("No numbers.\n", "title: x\nabstract: |\n  Prices fell 3.4 percent.\nauthor: y")
        self.assertEqual(rc, 1, out)
        self.assertIn("'3.4'", out)

    def test_title_is_scanned(self):
        rc, out = self.body("No numbers.\n", 'title: "A 12 percent drop"')
        self.assertEqual(rc, 1, out)
        self.assertIn("'12'", out)

    def test_subtitle_is_scanned(self):
        rc, out = self.body("No numbers.\n", "title: x\nsubtitle: Wave 7 data")
        self.assertEqual(rc, 1, out)
        self.assertIn("'7'", out)

    def test_other_yaml_keys_are_not_scanned(self):
        rc, out = self.body("No numbers.\n", "title: x\ndate: 2026-10-12\ndesign:\n  n: 0.5")
        self.assertEqual(rc, 0, out)

    def test_inline_r_in_abstract_passes(self):
        rc, out = self.body("No numbers.\n", "title: x\nabstract: >-\n  Prices fell `r round(b, 1)` percent.\nauthor: y")
        self.assertEqual(rc, 0, out)


class TestMath(Case):
    def test_decimal_in_math_is_flagged(self):
        rc, out = self.body("We estimate $\\beta = 0.634$ here.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.634'", out)

    def test_symbols_and_subscripts_pass(self):
        rc, out = self.body("Let $\\beta_1$ and $x_{it}$ and $y^2$ be given.\n")
        self.assertEqual(rc, 0, out)


class TestNotes(Case):
    def test_notes_literal_is_scanned(self):
        rc, out = self.body('```{r}\nmodelsummary(m, notes = "Clustered by 51 states.")\n```\n')
        self.assertEqual(rc, 1, out)
        self.assertIn("'51'", out)

    def test_star_legend_le_passes(self):
        rc, out = self.body('```{r}\nmodelsummary(m, notes = "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01")\n```\n')
        self.assertEqual(rc, 0, out)

    def test_star_legend_ascii_and_latex_pass(self):
        rc, out = self.body('```{r}\nmodelsummary(m, notes = "* p <= 0.1, ** p <= 0.05")\n```\n\n'
                            "Stars: p $\\le$ 0.01 and p $\\leq$ 0.05.\n")
        self.assertEqual(rc, 0, out)

    def test_star_legend_with_strict_less_than_fails(self):
        rc, out = self.body('```{r}\nmodelsummary(m, notes = "* p < 0.10, ** p < 0.05")\n```\n')
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.10'", out)


class TestLetter(Case):
    def test_letter_is_scanned(self):
        rc, out = self.run_check("---\ntitle: x\n---\n\nNo numbers.\n",
                                 claude="response-letter: letter.md\n",
                                 extra={"letter.md": "We now find 0.21.\n"})
        self.assertEqual(rc, 1, out)
        self.assertIn("letter:", out)
        self.assertIn("'0.21'", out)

    def test_missing_letter_is_exit_2(self):
        rc, out = self.run_check("---\ntitle: x\n---\n\nNo numbers.\n",
                                 claude="response-letter: nope.md\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("nope.md", out)


class TestControl(Case):
    def test_fixture_manuscript_passes(self):
        proj = self.t / "fixture"
        shutil.copytree(FIXTURE.parent, proj)
        (proj / ".claude").mkdir(exist_ok=True)
        p = subprocess.run([sys.executable, str(CHECK), str(proj / FIXTURE.name)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
