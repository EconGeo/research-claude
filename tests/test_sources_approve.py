"""`pipeline.py sources approve <id>…`: approvals only with the author's fresh `approve sources:` token."""
import csv, datetime as dt, hashlib, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"
sys.path.insert(0, str(ROOT / "scripts"))
import author_token as tok, source_check as sc

REG_COLS = ["id", "file", "label", "page", "sentence", "cleanup", "ocr"]
SRC_TEXT = "Intro.\n\nThe Firm shall disclose the fee in writing.\n\nOther text here."
SENT = "The Firm shall disclose the fee in writing."
CLAIM = "Paper wording of the disclosure rule."

def tag(claim, ref, tag_id):
    return "[" + claim + "]{.src ref=\"" + ref + "\" id=\"" + tag_id + "\"}"

def run(*a, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *a], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class SourcesApprove(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / "CLAUDE.md").write_text("manuscript: m.qmd\n")
        self.src = self.t / "sources" / "a.txt"; self.src.parent.mkdir(); self.src.write_text(SRC_TEXT)
        rows = [{"id": "ok", "file": "sources/a.txt", "label": "L", "page": "3", "sentence": SENT, "cleanup": "", "ocr": ""},
                {"id": "gone", "file": "sources/missing.txt", "label": "L", "page": "", "sentence": SENT, "cleanup": "", "ocr": ""},
                {"id": "bad", "file": "sources/a.txt", "label": "L", "page": "", "sentence": "Not in the file.", "cleanup": "", "ocr": ""}]
        reg = self.t / "quality_reports" / "sources.csv"; reg.parent.mkdir()
        with open(reg, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=REG_COLS); w.writeheader(); w.writerows(rows)
        (self.t / "m.qmd").write_text("\n\n".join([tag(CLAIM, "ok", "t1"), tag("Second claim.", "ok", "t2"),
                                                    tag(CLAIM, "gone", "t3"), tag(CLAIM, "bad", "t4")]) + "\n")
        self.app = self.t / sc.APPROVALS_REL
    def tearDown(self): shutil.rmtree(self.t)
    def author(self, ids):                     # stands in for hooks/design-token.py
        tok.issue(self.t, "sources", ids, None)
    def rows(self):
        if not self.app.exists(): return []
        with open(self.app, newline="") as fh: return list(csv.DictReader(fh))
    def states(self):
        return {r.tag.tag_id: r.state for r in sc.check(self.t, (self.t / "m.qmd").read_text())}

    def test_approve_writes_rows(self):
        self.author("t2,t1")
        rc, out = run("sources", "approve", "t1", "t2", root=self.t)
        self.assertEqual(rc, 0, out)
        rows = self.rows()
        self.assertEqual(list(rows[0].keys()), sc.APPROVAL_COLS)
        self.assertEqual([r["tag_id"] for r in rows], ["t1", "t2"])
        self.assertEqual(rows[0]["ref"], "ok")
        self.assertEqual(rows[0]["claim_sha256"], sc.claim_sha256(CLAIM))
        self.assertEqual(rows[1]["claim_sha256"], sc.claim_sha256("Second claim."))
        self.assertEqual(rows[0]["file_sha256"], hashlib.sha256(self.src.read_bytes()).hexdigest())
        self.assertEqual(dt.datetime.fromisoformat(rows[0]["approved_at"]).utcoffset(), dt.timedelta(0))
        self.assertEqual((self.states()["t1"], self.states()["t2"]), (sc.APPROVED, sc.APPROVED))

    def test_reapproval_appends_after_change(self):
        self.author("t1"); self.assertEqual(run("sources", "approve", "t1", root=self.t)[0], 0)
        self.src.write_text(SRC_TEXT + "\n\nAdded.")
        self.assertEqual(self.states()["t1"], sc.NEEDS_REVIEW)
        self.author("t1"); self.assertEqual(run("sources", "approve", "t1", root=self.t)[0], 0)
        self.assertEqual(len(self.rows()), 2); self.assertEqual(self.states()["t1"], sc.APPROVED)

    def test_approve_without_token_refused(self):
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("no author token", out); self.assertEqual(self.rows(), [])

    def test_design_token_does_not_approve_sources(self):
        tok.issue(self.t, "sign", None, None)
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1); self.assertEqual(self.rows(), [])

    def test_approve_mismatched_ids_refused(self):
        for approved, args in (("t1", ["t1", "t2"]), ("t1,t2", ["t1"]), ("t1", ["t2"])):
            self.author(approved)
            rc, out = run("sources", "approve", *args, root=self.t)
            self.assertEqual(rc, 1, (approved, args)); self.assertEqual(self.rows(), [])
        self.assertIsNone(tok._read(self.t)["used_at"])      # a refusal does not spend the token

    def test_approve_failed_claim_refused(self):
        for bad in ("t3", "t4"):                               # NOT ON THIS MACHINE, FAILED
            self.author("t1," + bad)
            rc, out = run("sources", "approve", "t1", bad, root=self.t)
            self.assertEqual(rc, 1, out); self.assertIn(bad, out); self.assertEqual(self.rows(), [])
            self.assertIsNone(tok._read(self.t)["used_at"])

    def test_unknown_id_refused(self):
        self.author("t1,nope")
        rc, out = run("sources", "approve", "t1", "nope", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("nope", out); self.assertEqual(self.rows(), [])

    def test_no_ids_is_usage_error(self):
        self.author("t1")
        rc, out = run("sources", "approve", root=self.t)
        self.assertNotEqual(rc, 0); self.assertEqual(self.rows(), [])

    def test_token_single_use(self):
        self.author("t1")
        self.assertEqual(run("sources", "approve", "t1", root=self.t)[0], 0)
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("already used", out); self.assertEqual(len(self.rows()), 1)

    def test_expired_token_refused(self):
        tok.issue(self.t, "sources", "t1", None, now=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=31))
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("expired", out); self.assertEqual(self.rows(), [])

    def test_design_tag_can_be_approved(self):
        qmd = ('---\ntitle: "T"\ndesign:\n  treatment:\n    source: {cite: rule1, quote: "' + SENT + '"}\n---\n\nBody.\n')
        (self.t / "m.qmd").write_text(qmd)
        with open(self.t / "quality_reports" / "sources.csv", "a", newline="") as fh:
            csv.DictWriter(fh, fieldnames=REG_COLS).writerow({"id": "design:rule1", "file": "sources/a.txt", "label": "L",
                                                              "page": "", "sentence": "", "cleanup": "", "ocr": ""})
        self.assertEqual(self.states(), {"design": sc.UNREVIEWED})
        self.author("design")
        rc, out = run("sources", "approve", "design", root=self.t)
        self.assertEqual(rc, 0, out); self.assertEqual(self.states(), {"design": sc.APPROVED})

    def test_docx_still_parses(self):
        # `sources docx` keeps working with the new positional (no ids).
        rc, out = run("sources", "docx", "extra", root=self.t)
        self.assertNotEqual(rc, 0)

if __name__ == "__main__": unittest.main()
