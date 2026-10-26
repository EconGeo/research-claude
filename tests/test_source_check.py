import csv, hashlib, pathlib, sys, tempfile, unittest
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

REG_COLS = ["id", "file", "label", "page", "sentence", "cleanup", "ocr"]
APP_COLS = ["tag_id", "ref", "claim_sha256", "file_sha256", "approved_at"]
SRC_TEXT = "Intro.\n\nThe Firm shall disclose the fee in writing.\n\nOther text here."
SENT = "The Firm shall disclose the fee in writing."

def write_csv(path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tag(claim, ref, tag_id):
    return "[" + claim + "]{.src ref=\"" + ref + "\" id=\"" + tag_id + "\"}"

class States(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("manuscript: paper.qmd\n")
        self.src = self.root / "sources" / "a.txt"
        self.src.parent.mkdir()
        self.src.write_text(SRC_TEXT)
    def tearDown(self):
        self.tmp.cleanup()
    def registry(self, rows):
        write_csv(self.root / "quality_reports" / "sources.csv", REG_COLS, rows)
    def reg_row(self, id_, file="sources/a.txt"):
        return {"id": id_, "file": file, "label": "Lbl", "page": "3", "sentence": "",
                "cleanup": "", "ocr": "FALSE"}
    def approve(self, rows):
        write_csv(self.root / "quality_reports" / "source_approvals.csv", APP_COLS, rows)
    def approval(self, tag_id, ref, claim, file_path):
        return {"tag_id": tag_id, "ref": ref, "claim_sha256": sc.claim_sha256(claim),
                "file_sha256": sha(file_path), "approved_at": "2026-10-26"}
    def test_each_state(self):
        qmd = "\n".join([tag(SENT, "ok", "t1"), tag(SENT, "ok", "t2"),
                         tag("Never said this.", "ok", "t3"),
                         tag(SENT, "missing", "t4"), tag(SENT, "nope", "t5"),
                         tag(SENT, "ok", "t6")])
        self.registry([self.reg_row("ok"), self.reg_row("missing", "sources/gone.txt")])
        self.approve([self.approval("t1", "ok", SENT, self.src),
                      dict(self.approval("t6", "ok", SENT, self.src), claim_sha256="0" * 64)])
        got = {r.tag.tag_id: r for r in sc.check(self.root, qmd)}
        self.assertEqual(got["t1"].state, "APPROVED")
        self.assertEqual(got["t2"].state, "UNREVIEWED")
        self.assertEqual(got["t3"].state, "FAILED")
        self.assertIsNone(got["t3"].paragraph)
        self.assertEqual(got["t4"].state, "NOT ON THIS MACHINE")
        self.assertIsNone(got["t4"].paragraph)
        self.assertEqual(got["t5"].state, "FAILED")
        self.assertIn("no registry entry", got["t5"].reason)
        self.assertEqual(got["t6"].state, "NEEDS REVIEW")
        self.assertEqual(got["t1"].label, "Lbl")
        self.assertEqual(got["t1"].page, "3")
        self.assertFalse(got["t1"].ocr)
    def test_claim_change_needs_review(self):
        self.registry([self.reg_row("ok")])
        self.approve([self.approval("c1", "ok", SENT, self.src),
                      self.approval("c2", "ok", "Intro.", self.src)])
        qmd = tag("The Firm shall disclose the fee in writing", "ok", "c1") + "\n" + tag("Intro.", "ok", "c2")
        got = {r.tag.tag_id: r for r in sc.check(self.root, qmd)}
        self.assertEqual(got["c1"].state, "NEEDS REVIEW")
        self.assertIn("claim", got["c1"].reason)
        self.assertEqual(got["c2"].state, "APPROVED")
    def test_file_change_needs_review(self):
        self.registry([self.reg_row("ok")])
        self.approve([self.approval("c1", "ok", SENT, self.src)])
        with open(self.src, "ab") as fh:
            fh.write(b" ")
        got = sc.check(self.root, tag(SENT, "ok", "c1"))
        self.assertEqual(got[0].state, "NEEDS REVIEW")
        self.assertIn("file", got[0].reason)
    def test_last_approval_row_wins_and_attr_order(self):
        self.registry([self.reg_row("ok")])
        old = dict(self.approval("c1", "ok", SENT, self.src), claim_sha256="0" * 64)
        self.approve([old, self.approval("c1", "ok", SENT, self.src)])
        qmd = "[" + SENT + "]{#x .src id=\"c1\" ref=\"ok\"}"
        self.assertEqual(sc.check(self.root, qmd)[0].state, "APPROVED")
    def test_tag_with_citation(self):
        qmd = tag("*NWMLS* rule [@nwmls2022]", "x", "c1")
        self.assertEqual(sc.scan_tags(qmd), [sc.Tag("c1", "x", "*NWMLS* rule [@nwmls2022]")])
    def test_claim_hash_whitespace_stable(self):
        self.assertEqual(sc.claim_sha256("one two\nthree"), sc.claim_sha256("one  two three"))
    def test_design_quote_tag(self):
        qmd = ('---\ntitle: T\ndesign:\n  treatment:\n    source: {cite: key2024, page: 12, '
               'quote: "the rule took effect"}\n---\n\nBody.\n')
        self.assertEqual(sc.scan_tags(qmd), [sc.Tag("design", "design:key2024", "the rule took effect")])
        self.assertEqual(sc.scan_tags("---\ntitle: T\n---\n\nBody.\n"), [])
    def test_warning_lines_summarise(self):
        def res(state, i):
            return sc.Result(sc.Tag("t%d" % i, "r", "c"), state, None, "why", "L", "1", False)
        results = [res("UNREVIEWED", i) for i in range(3)]
        results += [res("NOT ON THIS MACHINE", 3), res("NOT ON THIS MACHINE", 4), res("FAILED", 5)]
        lines = sc.warning_lines(results)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "source-check: FAILED t5 (r): why")
        self.assertIn("3 claims not yet reviewed", lines[1])
        self.assertIn("2 sources not on this machine", lines[2])
        self.assertEqual(sc.warning_lines([res("APPROVED", 0)]), [])

if __name__ == "__main__": unittest.main()
