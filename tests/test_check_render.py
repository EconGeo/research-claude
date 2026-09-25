"""check_render.py — the rendered page is the only place Quarto's failures show (L-002).

Every check here is a row of the authoring reference's gotchas ledger or post-render
checklist, run mechanically on pdftotext output. Fixtures are text so no PDF is needed.
"""
import pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_render.py"

CLEAN = """Effects of Policy on Outcomes
Keywords: housing; land use; supply
1 Introduction
As Table 1 shows, the estimate is 0.42 (see Section 3).
Table 1: Main estimates
Outcome  Estimate  SE  N
Figure 1: Event study
Notes: Standard errors clustered by state. The parallel-trends assumption IS NOT MET.
"""


def run(text, *args):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text); path = f.name
    return subprocess.run([sys.executable, str(SCRIPT), path, *args], capture_output=True, text=True)


class TestCheckRender(unittest.TestCase):
    def test_clean_text_exits_0(self):
        r = run(CLEAN)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_unresolved_crossref(self):
        r = run(CLEAN + "See ?@tbl-robust for details.\n")
        self.assertEqual(1, r.returncode)
        self.assertIn("UNRESOLVED: ?@tbl-robust", r.stdout)

    def test_literal_tex_markdown_and_html(self):
        r = run(CLEAN + "\\textbf{bold} and *stars* and <span>x</span>\n")
        self.assertIn("LITERAL_TEX: \\textbf{", r.stdout)
        self.assertIn("LITERAL_MD: *stars*", r.stdout)
        self.assertIn("LITERAL_HTML: <span>", r.stdout)

    def test_doubled_exhibit_number(self):
        r = run(CLEAN + "Table 2: Table 2: Robustness\n")
        self.assertIn("DOUBLED: Table 2", r.stdout)

    def test_doubled_does_not_fire_on_two_different_exhibits(self):
        # Review finding (Task 7 fix report, item 2): the DOUBLED regex must require the
        # same exhibit word (Table/Table or Figure/Figure) to repeat, not just any
        # Table-then-Figure adjacency in ordinary prose.
        r = run(CLEAN + "as shown in Table 1. Figure 1 plots the same.\n")
        self.assertNotIn("DOUBLED", r.stdout)

    def test_expect_phrase_missing_and_present_across_line_wrap(self):
        r = run(CLEAN, "--expect", "IS NOT MET", "--expect", "Keywords:")
        self.assertEqual(0, r.returncode, r.stdout)
        wrapped = CLEAN.replace("assumption IS NOT MET", "assumption IS\nNOT MET")
        r = run(wrapped, "--expect", "IS NOT MET")
        self.assertEqual(0, r.returncode, "a line wrap is not a missing phrase")
        clipped = CLEAN.replace(" IS NOT MET", "")
        r = run(clipped, "--expect", "IS NOT MET")
        self.assertIn("MISSING: IS NOT MET", r.stdout)

    def test_expect_ignores_ligatures(self):
        lig = CLEAN.replace("Outcomes", "Efﬁciency")  # pdftotext emits the fi ligature
        r = run(lig, "--expect", "Efficiency")
        self.assertEqual(0, r.returncode, r.stdout)

    def test_significance_stars_are_not_literal_markdown(self):
        r = run(CLEAN + "0.42*** (0.03)** and 0.10*\n")
        self.assertNotIn("LITERAL_MD", r.stdout)

    def test_columns_present_and_dropped(self):
        r = run(CLEAN, "--columns", "Table 1: Outcome,Estimate,SE,N")
        self.assertEqual(0, r.returncode, r.stdout)
        r = run(CLEAN.replace("Outcome  Estimate  SE  N", "Outcome  Estimate  SE"), "--columns", "Table 1: Outcome,Estimate,SE,N")
        self.assertIn("COLUMN: Table 1: N", r.stdout)

    def test_columns_caption_prefix_does_not_bind_to_a_longer_number(self):
        # Review finding (Task 7 fix report, item 1): "Table 1:" must not match a
        # "Table 10:" caption via a bare .startswith(head) check. Table 10 is missing its
        # "Beta" column; Table 1 has all of its columns. Column tokens are chosen so
        # neither is a substring of unrelated fixture prose (a plain-substring gotcha
        # distinct from the caption-binding bug under test).
        text = CLEAN + "Table 10: Robustness\nAlpha  Gamma\n"
        r = run(text, "--columns", "Table 1: Outcome,Estimate,SE,N")
        self.assertEqual(0, r.returncode, r.stdout)
        r = run(text, "--columns", "Table 10: Alpha,Beta")
        self.assertIn("COLUMN: Table 10: Beta", r.stdout)

    def test_missing_input_exits_2(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent.pdf"], capture_output=True, text=True)
        self.assertEqual(2, r.returncode)

    def test_shipped(self):
        self.assertIn("check_render.py", (ROOT / "scripts" / "SHIPPED").read_text().split())


if __name__ == "__main__":
    unittest.main()
