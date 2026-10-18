"""Task 10: dispatch-ok (no re-review of a passed, unchanged target) and critic-context."""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_pipeline import FixtureCase, run


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


class DispatchCase(FixtureCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(run("state", "init", root=self.t)[0], 0)
        self.ms = self.t / "manuscript_fixture.qmd"

    def score(self, val="85"):
        rc, out = run("state", "record-score", "manuscript", val, "--critic", "writer-critic",
                      "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)

    def init_git(self):
        git(self.t, "init", "-q"); git(self.t, "config", "user.email", "t@t"); git(self.t, "config", "user.name", "t")
        git(self.t, "add", "-A"); git(self.t, "commit", "-qm", "init", "--no-verify")


class TestDispatchOk(DispatchCase):
    def test_1_no_score_allows(self):
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 0)

    def test_2_passed_unchanged_blocks(self):
        self.score("85")
        rc, out = run("dispatch-ok", "writer-critic", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("PASSED-UNCHANGED", out)
        self.assertEqual(run("dispatch-ok", "writer-critic", "--author-request", root=self.t)[0], 0)

    def test_3_changed_manuscript_allows(self):
        self.score("85")
        with self.ms.open("a") as f: f.write("\nAn added line.\n")
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 0)

    def test_4_low_score_allows(self):
        self.score("70")
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 0)

    def test_5_stale_score_allows(self):
        fpp = self.t / "quality_reports" / "render_fingerprint.json"
        fpp.parent.mkdir(exist_ok=True)
        fpp.write_text(json.dumps({"estimates_hash": "A", "data_hash": "d", "design_hash": "x", "models": {}}))
        self.score("85")
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 1)
        fpp.write_text(json.dumps({"estimates_hash": "B", "data_hash": "d", "design_hash": "x", "models": {}}))
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 0)

    def test_6_missing_receipt_or_unknown_critic_allows(self):
        self.score("85")
        (self.t / "quality_reports" / "receipts.jsonl").unlink()
        self.assertEqual(run("dispatch-ok", "writer-critic", root=self.t)[0], 0)
        self.assertEqual(run("dispatch-ok", "no-such-critic", root=self.t)[0], 0)


class TestCriticContext(DispatchCase):
    def test_1_ledger_and_diff(self):
        self.init_git(); self.score("85")
        with self.ms.open("a") as f: f.write("\nA brand new sentence.\n")
        rc, out = run("ledger", "add", "--creator", "writer", "--report", "r.md", "--location", "Intro",
                      "--finding", "vague claim", root=self.t)
        self.assertEqual(rc, 0, out)
        rc, out = run("critic-context", "writer-critic", root=self.t)
        self.assertEqual(rc, 0, out)
        path = self.t / out.strip().split()[-1]
        self.assertTrue(path.is_file(), out)
        txt = path.read_text()
        self.assertIn("+A brand new sentence.", txt)
        self.assertIn("| id |", txt); self.assertIn("vague claim", txt)

    def test_2_no_prior_round(self):
        self.init_git()
        rc, out = run("critic-context", "writer-critic", root=self.t)
        self.assertEqual(rc, 0, out)
        self.assertIn("no prior scored round", (self.t / out.strip().split()[-1]).read_text())

    def test_3_not_a_git_repo(self):
        self.score("85")
        rc, out = run("critic-context", "writer-critic", root=self.t)
        self.assertEqual(rc, 0, out); self.assertNotIn("Traceback", out)
        self.assertIn("no prior scored round", (self.t / out.strip().split()[-1]).read_text())

    def test_4_unique_names(self):
        a = run("critic-context", "writer-critic", root=self.t)[1].strip()
        b = run("critic-context", "writer-critic", root=self.t)[1].strip()
        self.assertNotEqual(a, b)
