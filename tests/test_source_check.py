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
CLAIM = "Paper wording of the disclosure rule."

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
        return {"id": id_, "file": file, "label": "Lbl", "page": "3", "sentence": SENT,
                "cleanup": "", "ocr": "FALSE"}
    def approve(self, rows):
        write_csv(self.root / "quality_reports" / "source_approvals.csv", APP_COLS, rows)
    def approval(self, tag_id, ref, claim, file_path):
        return {"tag_id": tag_id, "ref": ref, "claim_sha256": sc.claim_sha256(claim),
                "file_sha256": sha(file_path), "approved_at": "2026-10-26"}
    def test_each_state(self):
        qmd = "\n".join([tag(CLAIM, "ok", "t1"), tag(CLAIM, "ok", "t2"),
                         tag(CLAIM, "bad", "t3"),
                         tag(CLAIM, "missing", "t4"), tag(CLAIM, "nope", "t5"),
                         tag(CLAIM, "ok", "t6")])
        bad = dict(self.reg_row("bad"), sentence="Never said this.")
        self.registry([self.reg_row("ok"), bad, self.reg_row("missing", "sources/gone.txt")])
        self.approve([self.approval("t1", "ok", CLAIM, self.src),
                      dict(self.approval("t6", "ok", CLAIM, self.src), claim_sha256="0" * 64)])
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
        self.approve([self.approval("c1", "ok", CLAIM, self.src),
                      self.approval("c2", "ok", "Intro.", self.src)])
        qmd = tag("Paper wording of the disclosure rule", "ok", "c1") + "\n" + tag("Intro.", "ok", "c2")
        got = {r.tag.tag_id: r for r in sc.check(self.root, qmd)}
        self.assertEqual(got["c1"].state, "NEEDS REVIEW")
        self.assertIn("claim", got["c1"].reason)
        self.assertEqual(got["c2"].state, "APPROVED")
    def test_file_change_needs_review(self):
        self.registry([self.reg_row("ok")])
        self.approve([self.approval("c1", "ok", CLAIM, self.src)])
        with open(self.src, "ab") as fh:
            fh.write(b" ")
        got = sc.check(self.root, tag(CLAIM, "ok", "c1"))
        self.assertEqual(got[0].state, "NEEDS REVIEW")
        self.assertIn("file", got[0].reason)
    def test_last_approval_row_wins_and_attr_order(self):
        self.registry([self.reg_row("ok")])
        old = dict(self.approval("c1", "ok", CLAIM, self.src), claim_sha256="0" * 64)
        self.approve([old, self.approval("c1", "ok", CLAIM, self.src)])
        qmd = "[" + CLAIM + "]{#x .src id=\"c1\" ref=\"ok\"}"
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

    def test_registry_sentence_is_matched_not_claim(self):
        self.registry([self.reg_row("ok")])
        self.assertEqual(sc.check(self.root, tag(CLAIM, "ok", "a"))[0].state, "UNREVIEWED")
        self.assertEqual(sc.check(self.root, tag(SENT, "ok", "b"))[0].state, "UNREVIEWED")
        bad = dict(self.reg_row("bad"), sentence="Not in the source at all.")
        self.registry([bad])
        r = sc.check(self.root, tag(SENT, "bad", "c"))[0]
        self.assertEqual(r.state, "FAILED")
        self.assertIsNone(r.paragraph)
    def test_empty_sentence_fails(self):
        self.registry([dict(self.reg_row("ok"), sentence="")])
        r = sc.check(self.root, tag(CLAIM, "ok", "a"))[0]
        self.assertEqual((r.state, r.reason), ("FAILED", "registry entry ok has no sentence"))
    def test_design_tag_through_check(self):
        qmd = ('---\ndesign:\n  treatment:\n    source: {cite: k24, page: 2, '
               'quote: "disclose the fee"}\n---\n\nBody.\n')
        self.registry([dict(self.reg_row("design:k24"), sentence="")])
        r = sc.check(self.root, qmd)[0]
        self.assertEqual((r.tag.tag_id, r.state), ("design", "UNREVIEWED"))
        self.assertIn("[disclose the fee]{.underline}", r.paragraph)
    def test_unbalanced_bracket_does_not_hide_tags(self):
        qmd = 'see [unclosed here\n\n' + tag("Claim.", "a", "b")
        self.assertEqual(sc.scan_tags(qmd), [sc.Tag("b", "a", "Claim.")])
    def test_tag_missing_id_or_ref_fails(self):
        qmd = '[Claim.]{.src ref="a"} [Other.]{.src id="z"}'
        self.registry([self.reg_row("a")])
        got = sc.check(self.root, qmd)
        self.assertEqual([r.state for r in got], ["FAILED", "FAILED"])
        self.assertEqual(got[0].reason, "tag missing id")
        self.assertEqual(got[1].reason, "tag missing ref")
        self.assertEqual(len(sc.warning_lines(got)), 2)
    def test_unreadable_source_fails_with_error(self):
        bad_rule = dict(self.reg_row("rule"), cleanup="nope")
        binary = self.root / "sources" / "b.txt"
        binary.write_bytes(b"\xff\xfe\x00bad")
        bad_text = dict(self.reg_row("bin", "sources/b.txt"))
        self.registry([bad_rule, bad_text])
        got = sc.check(self.root, tag(CLAIM, "rule", "a") + tag(CLAIM, "bin", "b"))
        self.assertEqual([r.state for r in got], ["FAILED", "FAILED"])
        self.assertIn("unknown cleanup rule: nope", got[0].reason)
        self.assertTrue(got[1].reason.startswith("cannot read source"))
        self.assertIsNone(got[0].paragraph)
    def test_ocr_true_and_multi_cleanup(self):
        (self.root / "sources" / "n.txt").write_text("Intro.\n\nThe Firm shall disclose the fee in writing. 206\n")
        row = dict(self.reg_row("n", "sources/n.txt"), ocr="True", cleanup="trailing-line-numbers; trailing-line-numbers")
        self.registry([row])
        r = sc.check(self.root, tag(CLAIM, "n", "a"))[0]
        self.assertTrue(r.ocr)
        self.assertEqual(r.state, "UNREVIEWED")
        self.assertNotIn("206", r.paragraph)
    def test_malformed_registry_fails_every_tag(self):
        path = self.root / "quality_reports" / "sources.csv"
        path.parent.mkdir()
        path.write_text("name,file\nok,sources/a.txt\n")
        got = sc.check(self.root, tag(CLAIM, "ok", "a") + tag(CLAIM, "ok", "b"))
        self.assertEqual([r.state for r in got], ["FAILED", "FAILED"])
        self.assertIn("registry", got[0].reason)
        path.write_bytes(b"id,file\n\xff\xfe,x\n")
        self.assertIn("registry", sc.check(self.root, tag(CLAIM, "ok", "a"))[0].reason)
    def test_short_registry_row_does_not_raise(self):
        path = self.root / "quality_reports" / "sources.csv"
        path.parent.mkdir()
        path.write_text("id,file,label,page,sentence,cleanup,ocr\nok,sources/a.txt\n")
        r = sc.check(self.root, tag(CLAIM, "ok", "a"))[0]
        self.assertEqual(r.state, "FAILED")
    def test_malformed_approvals_stay_unreviewed(self):
        self.registry([self.reg_row("ok")])
        path = self.root / "quality_reports" / "source_approvals.csv"
        path.write_text("who,when\nx,y\n")
        r = sc.check(self.root, tag(CLAIM, "ok", "a"))[0]
        self.assertEqual(r.state, "UNREVIEWED")
        self.assertIn("approvals", r.reason)

import json, subprocess
SCRIPT = ROOT / "scripts" / "source_check.py"

class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("manuscript: paper.qmd\n")
        src = self.root / "sources" / "a.txt"
        src.parent.mkdir()
        src.write_text(SRC_TEXT)
        row = {"id": "ok", "file": "sources/a.txt", "label": "Lbl", "page": "3",
               "sentence": SENT, "cleanup": "", "ocr": "TRUE"}
        write_csv(self.root / "quality_reports" / "sources.csv", REG_COLS, [row])
        (self.root / "paper.qmd").write_text(tag(CLAIM, "ok", "t1") + " " + tag(CLAIM, "nope", "t2") + "\n")
    def tearDown(self):
        self.tmp.cleanup()
    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                              capture_output=True, text=True, encoding="utf-8", env=env)
    def test_default_prints_warnings_exit0(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertIn("source-check: FAILED t2 (nope)", r.stdout)
        self.assertIn("1 claims not yet reviewed", r.stdout)
    def test_post_render_mode_exit0(self):
        import os
        r = self.run_cli(env=dict(os.environ, QUARTO_PROJECT_OUTPUT_FILES="paper.docx"))
        self.assertEqual(r.returncode, 0)
        self.assertIn("source-check: FAILED t2", r.stdout)
    def test_explicit_manuscript_and_root(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "paper.qmd", "--root", str(self.root)],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0)
        self.assertIn("FAILED t2", r.stdout)
    def test_json_shape(self):
        r = self.run_cli("--json")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(set(data), {"t1", "t2"})
        keys = {"state", "label", "page", "ocr", "paragraph", "reason", "before", "sentence", "after"}
        self.assertEqual(set(data["t1"]), keys)
        self.assertEqual(set(data["t2"]), keys)
        self.assertEqual((data["t1"]["before"], data["t1"]["sentence"], data["t1"]["after"]), ("", SENT, ""))
        self.assertEqual((data["t2"]["before"], data["t2"]["sentence"], data["t2"]["after"]), (None, None, None))
        self.assertEqual(data["t1"]["state"], "UNREVIEWED")
        self.assertIs(data["t1"]["ocr"], True)
        self.assertIn("[" + SENT + "]{.underline}", data["t1"]["paragraph"])
        self.assertIsNone(data["t2"]["paragraph"])
    def test_no_manuscript_silent(self):
        (self.root / "CLAUDE.md").write_text("nothing declared\n")
        for args in ([], ["--json"]):
            r = self.run_cli(*args)
            self.assertEqual((r.returncode, r.stdout), (0, ""))
        (self.root / "CLAUDE.md").write_text("manuscript: a.qmd\nmanuscript: b.qmd\n")
        self.assertEqual(self.run_cli().stdout, "")
        (self.root / "CLAUDE.md").write_text("manuscript: gone.qmd\n")
        self.assertEqual(self.run_cli().stdout, "")
        (self.root / "CLAUDE.md").unlink()
        self.assertEqual(self.run_cli().stdout, "")
    def test_internal_error_fails_open(self):
        (self.root / "paper.qmd").write_bytes(b"\xff\xfe not utf-8")
        r = self.run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("source-check: internal error: "))
    def test_unreadable_sources_csv_fails_open(self):
        (self.root / "quality_reports" / "sources.csv").write_bytes(b"\xff\xfe\x00bad")
        r = self.run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertIn("source-check:", r.stdout)

if __name__ == "__main__": unittest.main()
