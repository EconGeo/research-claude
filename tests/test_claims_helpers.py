# tests/test_claims_helpers.py
import pathlib, shutil, subprocess, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which("Rscript"), "Rscript not installed")
class TestClaimsHelpers(unittest.TestCase):
    def test_r_suite(self):
        r = subprocess.run(["Rscript", str(ROOT / "tests" / "r" / "test_claims_helpers.R"), str(ROOT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("claims-helpers: OK", r.stdout)
