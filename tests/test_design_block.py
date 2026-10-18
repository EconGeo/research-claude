# tests/test_design_block.py
import csv, pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import design_block as db

BASE = """---
title: "T"
design:
  inference: {rule: cluster-robust, cluster: region, id: INF-1}   # field standard
  treatment:
    definition: "first permit issued under the new rule"
    date: 2020-01-01
    source: {cite: key2024, page: 12, quote: "the rule took effect"}
  sample: ["units observed before and after the rule"]
  hypotheses:
    H1: {estimand: "ATT", outcome: y, spec: m_h1, direction: negative}
  checks:
    power: {mde: 0.02, target_effect: 0.03, file: explorations/power.qmd}
    size: {rejection_at_0.10: 0.104, reps: 500, file: explorations/size.qmd}
format: pdf
---

Body text.
"""

class TestBlock(unittest.TestCase):
    def test_extracts_block_only(self):
        b = db.design_block(BASE)
        self.assertTrue(b.startswith("design:"))
        self.assertNotIn("format:", b); self.assertNotIn("title:", b)
    def test_span(self):
        self.assertEqual(db.design_span(BASE), (3, 14))
    def test_no_front_matter_or_block(self):
        self.assertIsNone(db.design_block("Body only\n"))
        self.assertIsNone(db.design_hash("---\ntitle: x\n---\n"))
    def test_hash_ignores_comments_ws_crlf(self):
        h = db.design_hash(BASE)
        noisy = BASE.replace("   # field standard", "").replace("\n", "\r\n")
        noisy = noisy.replace("  hypotheses:", "\n  # note\n  hypotheses:").replace("date: 2020-01-01", "date: 2020-01-01   ")
        self.assertEqual(db.design_hash(noisy), h)
    def test_hash_changes_on_value(self):
        self.assertNotEqual(db.design_hash(BASE.replace("cluster: region", "cluster: state")), db.design_hash(BASE))
    def test_edit_outside_block_keeps_hash(self):
        self.assertEqual(db.design_hash(BASE.replace('title: "T"', 'title: "U"')), db.design_hash(BASE))
    def test_no_alpha_or_verdicts_needed(self):
        self.assertNotIn("alpha", BASE); self.assertNotIn("verdicts", BASE)
        self.assertIsNotNone(db.design_hash(BASE))
    def test_checks(self):
        self.assertTrue(db.has_check(BASE, "power")); self.assertTrue(db.has_check(BASE, "size"))
        self.assertFalse(db.has_check(BASE.replace("    size:", "    sizz:"), "size"))
        self.assertEqual(db.check_field(BASE, "power", "file"), "explorations/power.qmd")
        self.assertEqual(db.check_number(BASE, "size", "rejection_at_0.10"), 0.104)
        self.assertEqual(db.check_number(BASE, "power", "target_effect"), 0.03)
        self.assertIsNone(db.check_number(BASE, "power", "nothing"))
    def test_amendment_rows_name_the_field(self):
        new = db.design_block(BASE.replace("cluster: region", "cluster: state"))
        rows = db.amendment_rows(db.design_block(BASE), new, "2026-10-20", "cluster at state level")
        self.assertEqual(len(rows), 1); r = rows[0]
        self.assertEqual(r["field"], "inference")
        self.assertIn("cluster: region", r["old"]); self.assertIn("cluster: state", r["new"])
        self.assertEqual((r["date"], r["reason"]), ("2026-10-20", "cluster at state level"))
    def test_needs_rerun(self):
        old = db.design_block(BASE)
        for a, b in (("cluster: region", "cluster: state"), ('"units observed', '"units always observed'),
                     ("date: 2020-01-01", "date: 2020-07-01"), ("outcome: y,", "outcome: y2,")):
            new = db.design_block(BASE.replace(a, b))
            self.assertTrue(db.needs_rerun(db.amendment_rows(old, new, "d", "r"), old, new), a)
        new = db.design_block(BASE.replace('estimand: "ATT"', 'estimand: "ATT, all cohorts"'))
        self.assertFalse(db.needs_rerun(db.amendment_rows(old, new, "d", "r"), old, new))
    def test_append_amendments_csv_and_md(self):
        r = pathlib.Path(tempfile.mkdtemp())
        rows = [{"date": "2026-10-20", "field": "inference", "old": "a, b", "new": "c | d", "reason": "why"}]
        db.append_amendments(r, rows, heading="Amendment — 2026-10-20", diff="-a\n+c")
        got = list(csv.DictReader((r / db.AMEND_CSV_REL).open()))
        self.assertEqual(list(got[0].keys()), db.AMEND_FIELDS); self.assertEqual(got[0]["new"], "c | d")
        self.assertEqual(db.amendment_count(r), 1)
        md = (r / db.AMEND_MD_REL).read_text(); self.assertIn("Amendment — 2026-10-20", md); self.assertIn("```diff", md)
    def test_manuscript_path_and_lock_roundtrip(self):
        r = pathlib.Path(tempfile.mkdtemp())
        self.assertIsNone(db.manuscript_path(r))
        (r / "CLAUDE.md").write_text("manuscript: m.qmd\n"); self.assertEqual(db.manuscript_path(r), (r / "m.qmd").resolve())
        self.assertIsNone(db.read_lock(r))
        db.write_lock(r, {"status": "signed", "hash": "abc"}); self.assertEqual(db.read_lock(r)["hash"], "abc")

if __name__ == "__main__": unittest.main()
