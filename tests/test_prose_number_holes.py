"""prose_number_check.py — the holes a 2026-09-23 project audit found.

Each class is one hole. At least one test in each class failed on main at
efe9e70; the rest guard behaviour that must not regress.
"""
import pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "prose_number_check.py"


class Case(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.t)

    def check(self, body, allow="literal,reason\n", claude=None):
        qmd = self.t / "manuscript_fixture.qmd"
        qmd.write_text('---\ntitle: "x"\n---\n\n' + body)
        a = self.t / "quality_reports" / "prose_number_allowlist.csv"
        a.parent.mkdir(exist_ok=True)
        a.write_text(allow)
        if claude is not None:
            (self.t / "CLAUDE.md").write_text(claude)
        p = subprocess.run([sys.executable, str(CHECK), str(qmd)],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


class TestFences(Case):
    def test_unclosed_fence_is_a_structural_error(self):
        rc, out = self.check("Intro.\n\n```\nstray\n\nThe elasticity is 0.634.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("never closed", out)
        self.assertIn("line 7", out)          # 4 header lines + blank + "Intro." + blank

    def test_longer_fence_contains_a_shorter_one(self):
        body = "````markdown\n```{r}\nx <- 1\n```\n````\n\nThe elasticity is 0.634.\n"
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.634'", out)          # prose after the outer fence is scanned

    def test_fence_with_info_string_does_not_close(self):
        body = "```{r}\nx <- 1\n```{r}\n```\n\nShare is 0.25.\n"
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'0.25'", out)

    def test_balanced_chunks_still_pass(self):
        rc, out = self.check("```{r}\nx <- 1.5\n```\n\nNo numbers.\n")
        self.assertEqual(rc, 0, out)


class TestTokenisation(Case):
    def test_quarto_inline_syntax_is_recognised(self):
        rc, out = self.check("The coefficient is `{r} round(b, 3)` here.\n")
        self.assertEqual(rc, 0, out)

    def test_trailing_comma_is_not_part_of_the_key(self):
        rc, out = self.check("In 2024, prices fell.\n", allow="literal,reason\n2024,Calendar year.\n")
        self.assertEqual(rc, 0, out)

    def test_thousands_separator_is_kept(self):
        rc, out = self.check("We observe 1,234 sales.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("'1,234'", out)


class TestSignGlue(Case):
    def test_plus_before_inline_fails(self):
        rc, out = self.check("The coefficient = +`r b` points.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("SIGN TYPED BESIDE A LIVE VALUE", out)

    def test_minus_and_unicode_minus_and_quarto_form_fail(self):
        for body in ("It is -`r b`.\n", "It is −`r b`.\n", "It is (-`{r} b`).\n"):
            with self.subTest(body=body):
                rc, out = self.check(body)
                self.assertEqual(rc, 1, out)

    def test_allowlist_cannot_silence_it(self):
        rc, out = self.check("It is +`r b`.\n", allow="literal,reason\n+,Sign.\n")
        self.assertEqual(rc, 1, out)

    def test_range_idioms_and_compounds_pass(self):
        for body in ("From `r a`--`r b`.\n", "From `r a`-`r b`.\n", "The pre-`r y` era.\n"):
            with self.subTest(body=body):
                rc, out = self.check(body)
                self.assertEqual(rc, 0, out)


class TestCaptions(Case):
    def test_hash_pipe_caption_is_scanned(self):
        body = '```{r}\n#| label: fig-rents\n#| fig-cap: "Rents across 117 markets"\nplot(1)\n```\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'117'", out)
        self.assertIn("caption:", out)

    def test_fence_line_caption_is_scanned(self):
        rc, out = self.check('```{r fig-top, fig.cap="Top 60 shown"}\nplot(1)\n```\n')
        self.assertEqual(rc, 1, out)
        self.assertIn("'60'", out)

    def test_r_caption_and_title_strings_are_scanned(self):
        body = ('```{r}\nmake_ft(d, caption = "Table 4: Returns")\n'
                "modelsummary(m, title = 'Table 5: Panel')\n```\n")
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'4'", out)
        self.assertIn("'5'", out)

    def test_code_comments_and_expr_captions_are_not(self):
        body = ('```{r}\n#| fig-cap: !expr paste("N =", n)\n'
                '# caption = "Table 9"\nx <- 1.20\n```\n')
        rc, out = self.check(body)
        self.assertEqual(rc, 0, out)

    def test_allowlisted_caption_literal_passes(self):
        body = '```{r}\n#| fig-cap: "Rents, 1983 onward"\nplot(1)\n```\n'
        rc, out = self.check(body, allow="literal,reason\n1983,Panel start year.\n")
        self.assertEqual(rc, 0, out)

    def test_fence_line_caption_with_escaped_quote_is_scanned(self):
        body = '```{r fig-q, fig.cap="A \\"quoted\\" term at 60 sites"}\nplot(1)\n```\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'60'", out)

    def test_r_caption_syntax_is_not_read_in_a_python_chunk(self):
        body = '```{python}\nplt.title = "Top 60"\nax.set(title="Top 60")\n```\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 0, out)

    def test_option_caption_is_read_in_a_python_chunk(self):
        body = '```{python}\n#| fig-cap: "Rents across 117 markets"\nplt.plot(1)\n```\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 1, out)
        self.assertIn("'117'", out)

    def test_r_caption_syntax_is_not_read_in_a_display_fence(self):
        rc, out = self.check('```r\nmake_ft(d, caption = "Table 4: Returns")\n```\n')
        self.assertEqual(rc, 0, out)

    def test_executable_chunk_nested_in_a_display_fence_is_not_read(self):
        body = '````markdown\n```{r}\n#| fig-cap: "Top 60"\n```\n````\n'
        rc, out = self.check(body)
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
