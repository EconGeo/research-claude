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
        try:
            prints = sc.fingerprints(self.t, (self.t / "m.qmd").read_text(), ids.split(","))
        except ValueError:
            prints = None                      # the hook would issue no token; approve must refuse
        tok.issue(self.t, "sources", ids, None, fingerprints=prints)
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

    # Final review finding 1: the approval row binds the registry entry.
    def test_approval_row_has_entry_hash(self):
        self.author("t1")
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 0, out)
        reg = self.t / "quality_reports" / "sources.csv"
        with open(reg, newline="") as fh:
            entry = [r for r in csv.DictReader(fh) if r["id"] == "ok"][0]
        self.assertEqual(self.rows()[0]["entry_sha256"], sc.entry_sha256("ok", entry))
        reg.write_text(reg.read_text().replace(SENT, "Other text here."))
        self.assertEqual(self.states()["t1"], sc.NEEDS_REVIEW)

    # Final review finding 2: the token binds what the author saw, not only the ids.
    def test_claim_edited_after_author_approval_refused(self):
        self.author("t1")
        ms = self.t / "m.qmd"
        ms.write_text(ms.read_text().replace(CLAIM, "Wording the author never saw.", 1))
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("changed since the author approved", out)
        self.assertIn("claim", out)
        self.assertEqual(self.rows(), [])
        self.assertIsNone(tok._read(self.t)["used_at"])
    def test_entry_or_file_edited_after_author_approval_refused(self):
        reg = self.t / "quality_reports" / "sources.csv"
        original = reg.read_text()
        for change, word in ((lambda: reg.write_text(original.replace(",L,3,", ",Other,3,", 1)), "source entry"),
                             (lambda: self.src.write_text(SRC_TEXT + "\n\nAdded."), "file")):
            reg.write_text(original)
            self.src.write_text(SRC_TEXT)
            self.author("t1")
            change()
            rc, out = run("sources", "approve", "t1", root=self.t)
            self.assertEqual(rc, 1, out)
            self.assertIn(word, out)
            self.assertEqual(self.rows(), [])
    def test_token_without_fingerprints_refused(self):
        tok.issue(self.t, "sources", "t1", None)
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("fingerprint", out)
        self.assertEqual(self.rows(), [])

    # Final review finding 4: repeated ids and the reserved id cannot be approved.
    def test_duplicate_or_reserved_id_refused(self):
        ms = self.t / "m.qmd"
        ms.write_text(tag(CLAIM, "ok", "t1") + "\n\n" + tag("Again.", "ok", "t1") + "\n\n" + tag(CLAIM, "ok", "design") + "\n")
        for tag_id in ("t1", "design"):
            tok.issue(self.t, "sources", tag_id, None, fingerprints={tag_id: {}})
            rc, out = run("sources", "approve", tag_id, root=self.t)
            self.assertEqual(rc, 1, out)
            self.assertIn("FAILED", out)
            self.assertEqual(self.rows(), [])

    # Minor: a malformed approvals file is never appended to; an old-format one is migrated.
    def test_malformed_approvals_refused(self):
        self.app.write_text("who,when\nx,y\n")
        self.author("t1")
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("source_approvals.csv", out)
        self.assertEqual(self.app.read_text(), "who,when\nx,y\n")
    def test_old_format_approvals_migrated(self):
        self.app.write_text("tag_id,ref,claim_sha256,file_sha256,approved_at\nt2,ok,abc,def,2026-10-25\n")
        self.author("t1")
        rc, out = run("sources", "approve", "t1", root=self.t)
        self.assertEqual(rc, 0, out)
        rows = self.rows()
        self.assertEqual(list(rows[0].keys()), sc.APPROVAL_COLS)
        self.assertEqual([(r["tag_id"], r["entry_sha256"] != "") for r in rows], [("t2", False), ("t1", True)])
        self.assertEqual(self.states()["t1"], sc.APPROVED)

    def test_docx_still_parses(self):
        # `sources docx` keeps working with the new positional (no ids).
        rc, out = run("sources", "docx", "extra", root=self.t)
        self.assertNotEqual(rc, 0)

    def test_docx_without_manuscript_is_one_line(self):
        (self.t / "CLAUDE.md").write_text("no manuscript here\n")
        rc, out = run("sources", "docx", root=self.t)
        self.assertEqual(rc, 1)
        self.assertNotIn("Traceback", out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)

if __name__ == "__main__": unittest.main()
