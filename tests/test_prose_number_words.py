"""prose_number_check.py -- retrofitted papers (a `design:` block) get the strict word gate,
guards and pipeline jargon; every paper gets the threshold warning and the context allowlist.
"""
import pathlib, subprocess, sys, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_prose_number_surface import Case, CHECK  # noqa: E402
from test_design_block import BASE  # noqa: E402

PLAIN_HEAD = 'title: "x"'


class Words(Case):
    def run_check(self, text, claude=None, extra=None, allow=None):
        qmd = self.t / "manuscript_fixture.qmd"
        qmd.write_text(text)
        a = self.t / "quality_reports" / "prose_number_allowlist.csv"
        a.parent.mkdir(exist_ok=True)
        a.write_text("literal,reason\n" if allow is None else allow)
        if claude is not None:
            (self.t / "CLAUDE.md").write_text(claude)
        p = subprocess.run([sys.executable, str(CHECK), str(qmd)],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def retro(self, body, **kw):
        return self.run_check(BASE.replace("Body text.\n", body), **kw)

    def plain(self, body, **kw):
        return self.run_check(f"---\n{PLAIN_HEAD}\n---\n\n{body}", **kw)


class TestRetrofittedWords(Words):
    def test_typed_rose_fails(self):
        rc, out = self.retro("Prices rose by `r rc_num(b)`.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("rose", out)

    def test_rc_dir_passes(self):
        rc, out = self.retro('Prices `r rc_dir(b, "rose", "fell")` by `r rc_num(b)`.\n')
        self.assertEqual(rc, 0, out)

    def test_guard_binds_the_sentence(self):
        g = '`r local({stopifnot("main: rose" = b > 0); ""})`'
        rc, out = self.retro(f"Prices rose by `r rc_num(b)`{g}.\n")
        self.assertEqual(rc, 0, out)
        rc, out = self.retro("Prices rose by `r rc_num(b)`.\n")
        self.assertEqual(rc, 1, out)

    def test_strict_lexicon(self):
        for sent in ("The effect is larger at `r rc_num(b)`.",
                     "The effect doubled to `r rc_num(b)`.",
                     "Results hold in every specification, `r rc_num(b)`."):
            rc, out = self.retro(sent + "\n")
            self.assertEqual(rc, 1, sent + out)

    def test_not_retrofitted_unchanged(self):
        rc, out = self.plain("Prices rose by `r rc_num(b)`.\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("advisory", out)
        rc, out = self.plain("The effect is larger at `r rc_num(b)`.\n")
        self.assertEqual(rc, 0, out)

    def test_ceiling_override(self):
        rc, out = self.retro("Prices rose by `r rc_num(b)`.\n", claude="prose-verdict-ceiling: 5\n")
        self.assertEqual(rc, 0, out)

    def test_mode_named(self):
        rc, out = self.retro("Plain text.\n")
        self.assertEqual(rc, 0, out)
        self.assertIn("default, retrofitted", out)

    def test_word_context_row(self):
        allow = "literal,reason,context\npositive,sign of a definition,positive integer\n"
        rc, out = self.retro("A positive integer `r k` is given.\n", allow=allow)
        self.assertEqual(rc, 0, out)
        rc, out = self.retro("A positive effect of `r rc_num(b)` appears.\n", allow=allow)
        self.assertEqual(rc, 1, out)


class TestJargon(Words):
    def test_governing_p_fails(self):
        rc, out = self.retro("The governing p is small.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("PIPELINE JARGON", out)

    def test_declared_jargon(self):
        rc, out = self.retro("A foo-band appears.\n", claude="prose-jargon: foo-band\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("foo-band", out)

    def test_not_retrofitted_no_jargon(self):
        rc, out = self.plain("The governing p is small.\n")
        self.assertEqual(rc, 0, out)

    def test_ids_fire_but_prose_does_not(self):
        for ok in ("R-1 zoning districts", "an L-1 visa", "F-150", "R-squared",
                   "F-statistic", "R-2000"):
            rc, out = self.retro(f"We use {ok} here.\n")
            self.assertNotIn("PIPELINE JARGON", out, ok)
        for bad in ("see ruling R-12", "F-007", "L-012"):
            rc, out = self.retro(f"We {bad} here.\n")
            self.assertEqual(rc, 1, bad + out)
            self.assertIn("PIPELINE JARGON", out)

    def test_headings_and_div_lines_are_scanned(self):
        for line in ("## The governing p result", '::: {.callout title="governing p"}'):
            rc, out = self.retro(f"{line}\n\nText.\n")
            self.assertEqual(rc, 1, line + out)
            self.assertIn("PIPELINE JARGON", out)

    def test_hyphenated_prose_is_not_jargon(self):
        rc, out = self.retro("The first-rate result in a well-known study, 8-year-old data.\n")
        self.assertNotIn("PIPELINE JARGON", out)

    def test_invalid_declared_pattern_is_exit_2(self):
        rc, out = self.retro("Text.\n", claude="prose-jargon: foo(\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("prose-jargon", out)
        self.assertNotIn("Traceback", out)

    def test_jargon_across_a_line_break(self):
        rc, out = self.retro("The governing\np is small.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("PIPELINE JARGON", out)

    def test_guard_does_not_bind_neighbouring_list_item(self):
        g = '`r local({stopifnot("m" = b > 0); ""})`'
        rc, out = self.retro(f"- Prices rose `r rc_num(b)`\n- Wages fell `r rc_num(c)`{g}\n")
        self.assertEqual(rc, 1, out)
        rc, out = self.retro(f"- Prices rose `r rc_num(b)`{g}\n- Plain item.\n")
        self.assertEqual(rc, 0, out)


class TestThreshold(Words):
    def test_odd_threshold_warns(self):
        for mk in (self.plain, self.retro):
            rc, out = mk('Result `r if (p <= 0.07) "x" else "y"`.\n')
            self.assertEqual(rc, 0, out)
            self.assertIn("WARN literal threshold", out)

    def test_convention_threshold_is_quiet(self):
        for mk in (self.plain, self.retro):
            rc, out = mk('Result `r if (p <= 0.05) "x" else "y"`.\n')
            self.assertEqual(rc, 0, out)
            self.assertNotIn("WARN", out)


    def test_sign_check_threshold_is_quiet(self):
        rc, out = self.plain('Result `r if (b > 0) "rose" else "fell"`.\n')
        self.assertNotIn("WARN", out)


class TestContext(Words):
    def test_literal_context_row(self):
        allow = "literal,reason,context\n2024,settlement year,in 2024\n"
        rc, out = self.plain("Settled in 2024.\n", allow=allow)
        self.assertEqual(rc, 0, out)
        rc, out = self.plain("It gained 0.2024 points.\n", allow=allow)
        self.assertEqual(rc, 1, out)


class TestRideAlongs(Words):
    def test_all_math_star_legend(self):
        rc, out = self.plain("Stars: $p \\le 0.05$ and $p \\leq 0.01$.\n")
        self.assertEqual(rc, 0, out)
        rc, out = self.plain("Stars: $p < 0.05$.\n")
        self.assertEqual(rc, 1, out)

    def test_plain_multiline_abstract(self):
        rc, out = self.run_check("---\ntitle: x\nabstract: Prices fell\n  3.4 percent.\nauthor: y\n---\n\nNo numbers.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("'3.4'", out)


if __name__ == "__main__":
    unittest.main()
