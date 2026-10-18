import csv, json, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_design_block import BASE
import author_token as tok, design_block as dsb

def run(*a, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *a], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class DesignCase(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / "CLAUDE.md").write_text("manuscript: m.qmd\n")
        (self.t / "rules").mkdir(); shutil.copy(ROOT / "rules" / "registry.yaml", self.t / "rules" / "registry.yaml")
        (self.t / "explorations").mkdir()
        for f in ("power.qmd", "size.qmd"): (self.t / "explorations" / f).write_text("---\ntitle: check\n---\n")
        self.ms = self.t / "m.qmd"; self.ms.write_text(BASE)
    def tearDown(self): shutil.rmtree(self.t)
    def approve(self, op, reason=None):        # stands in for hooks/design-token.py
        tok.issue(self.t, op, reason, dsb.design_hash(self.ms.read_text()))
    def sign(self):
        self.approve("sign"); return run("design", "sign", "--signer", "author", root=self.t)
    def unlock(self, reason):
        self.approve("unlock", reason); return run("design", "unlock", "--reason", reason, root=self.t)
    def edit(self, old, new):
        self.ms.write_text(self.ms.read_text().replace(old, new))
    def status(self):
        return run("design", "status", root=self.t)

    def test_not_retrofitted_passes(self):
        self.ms.write_text("---\ntitle: x\n---\nbody\n")
        rc, out = self.status(); self.assertEqual(rc, 0); self.assertIn("NOT-RETROFITTED", out)
    def test_unsigned_fails(self):
        rc, out = self.status(); self.assertEqual(rc, 1); self.assertIn("UNSIGNED", out)
    def test_sign_refused_without_token(self):
        rc, out = run("design", "sign", "--signer", "author", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("no author token", out)
    def test_sign_then_signed_and_token_spent(self):
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
        self.assertIn("SIGNED", self.status()[1])
        self.assertIsNotNone(json.loads((self.t / tok.TOKEN_REL).read_text())["used_at"])
    def test_token_for_another_block_refused(self):
        self.approve("sign"); self.edit("cluster: region", "cluster: state")
        rc, out = run("design", "sign", "--signer", "author", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("different design block", out)
    def test_sign_requires_checks(self):
        for old, new, msg in (("    size:", "    sizz:", "checks.size missing"),
                              ("explorations/size.qmd", "explorations/nope.qmd", "does not exist"),
                              ("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.164", "outside"),
                              ("mde: 0.02", "mde: 0.05", "exceeds")):
            with self.subTest(msg=msg):
                self.ms.write_text(BASE.replace(old, new)); self.approve("sign")
                rc, out = run("design", "sign", "--signer", "a", root=self.t)
                self.assertEqual(rc, 1); self.assertIn(msg, out)
    def test_changed_after_sign_fails(self):
        self.sign(); self.edit("cluster: region", "cluster: state")
        rc, out = self.status(); self.assertEqual(rc, 1); self.assertIn("CHANGED", out)
    def test_unlock_needs_token_with_the_authors_reason(self):
        self.sign()
        rc, out = run("design", "unlock", "--reason", "cluster at state level", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("already used", out)       # the sign token is spent
        self.approve("unlock", "cluster at state level")
        rc, out = run("design", "unlock", "--reason", "something else", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("reason", out)
    def test_amendment_writes_csv_and_md(self):
        self.sign(); self.assertEqual(self.unlock("cluster at state level")[0], 0)
        self.assertIn("UNLOCKED", self.status()[1])
        self.edit("cluster: region", "cluster: state")
        self.edit("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.098")   # inference changed: checks re-run
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
        rows = list(csv.DictReader((self.t / dsb.AMEND_CSV_REL).open()))
        self.assertEqual(list(rows[0].keys()), ["date", "field", "old", "new", "reason"])
        self.assertEqual([r["field"] for r in rows], ["inference", "checks.size"])
        self.assertIn("cluster: region", rows[0]["old"]); self.assertIn("cluster: state", rows[0]["new"])
        self.assertEqual(rows[0]["reason"], "cluster at state level")
        md = (self.t / dsb.AMEND_MD_REL).read_text()
        self.assertIn("cluster at state level", md); self.assertIn("+  inference:", md)
    def test_amendment_touching_sample_needs_new_checks(self):
        self.sign(); self.unlock("drop units with gaps")
        self.edit('"units observed', '"units always observed')
        rc, out = self.sign(); self.assertEqual(rc, 1); self.assertIn("re-run the power and size", out)
        self.edit("rejection_at_0.10: 0.104", "rejection_at_0.10: 0.101")
        rc, out = self.sign(); self.assertEqual(rc, 0, out)
    def test_seed_amendment_only_before_first_signing(self):
        args = ("design", "seed-amendment", "--date", "2025-03-01", "--field", "treatment.date",
                "--old", "2019-06-01", "--new", "2020-01-01", "--reason", "statute effective date")
        self.assertEqual(run(*args, root=self.t)[0], 0)
        self.assertEqual(dsb.amendment_count(self.t), 1)
        self.sign(); rc, out = run(*args, root=self.t); self.assertEqual(rc, 1); self.assertIn("first signing", out)
    def test_pre_coder_blocks_unsigned(self):
        rc, out = run("pre", "coder", root=self.t); self.assertIn("design-lock", out); self.assertEqual(rc, 1)

if __name__ == "__main__": unittest.main()
