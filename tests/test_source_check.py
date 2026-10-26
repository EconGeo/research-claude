import pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import source_check as sc
FX = ROOT / "tests" / "fixtures" / "sources"
U_SENT = "Seller and Buyer shall pay compensation in accordance with any listing or compensation agreement to which they are a party."

class ExtractMatch(unittest.TestCase):
    def test_trailing_line_numbers(self):
        out = sc.clean((FX / "form_lines.txt").read_text(), ["trailing-line-numbers"])
        self.assertIn("listing or compensation agreement", sc.normalise(out)); self.assertNotIn(" 206", out)
        st, para, _ = sc.find_paragraph(out, U_SENT)
        self.assertEqual(st, "ok"); self.assertFalse(para[-1].isdigit())
    def test_not_found_never_returns_text(self):
        text = (FX / "form_lines.txt").read_text(); s = "NWMLS stopped posting compensation offers."
        st, para, why = sc.find_paragraph(text, s)
        self.assertEqual((st, para), ("not-found", None)); self.assertIn(s, why)
    def test_ambiguous_sentence_fails(self):
        r = sc.find_paragraph((FX / "boiler.txt").read_text(), "The Firm shall disclose the fee in writing.")
        self.assertEqual(r, ("ambiguous", None, "ambiguous: 2 paragraphs"))
    def test_dehyphenated_match(self):
        self.assertEqual(sc.find_paragraph((FX / "hyphen.txt").read_text(), "Seller and Buyer shall pay compensation to the Firm at closing.")[0], "ok")
    def test_nfkc_and_quotes(self):
        self.assertEqual(sc.find_paragraph("Intro.\n\nSee the ﬁnal Firm’s fee today.", "the final Firm's fee")[0], "ok")
    def test_html_paragraphs(self):
        text = sc.extract_text(FX / "page.html")
        st, para, _ = sc.find_paragraph(text, "The agent must disclose all fees to the buyer.")
        self.assertEqual(st, "ok"); self.assertNotIn("First paragraph", para)
    def test_underline_markup(self):
        s = "shall disclose the fee"
        para = sc.find_paragraph("Intro.\n\nThe Firm shall disclose the fee in writing.", s)[1]
        self.assertEqual(para.count("[" + sc.normalise(s) + "]{.underline}"), 1)
    def test_word_boundaries(self):
        self.assertEqual(sc.find_paragraph("Intro.\n\nYou must pay the fees now.", "pay the fee")[:2], ("not-found", None))
        self.assertEqual(sc.find_paragraph("Intro.\n\nThe casino fee is high.", "no fee")[:2], ("not-found", None))
        self.assertEqual(sc.find_paragraph("Intro.\n\nYou must pay the fee. Now.", "pay the fee")[0], "ok")
    def test_unknown_cleanup_rule(self):
        with self.assertRaises(ValueError): sc.clean("x", ["nope"])

if __name__ == "__main__": unittest.main()
