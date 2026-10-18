"""Task 9: finding ledger, rulings log, questions for the author, ledger-closed predicate."""
import datetime as dt, os, pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_pipeline import FixtureCase, run
from test_fingerprint_staleness import StaleCase
import findings_ledger as fl

TODAY = dt.date.today().isoformat()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def init_repo(root):
    git(root, "init", "-q"); git(root, "config", "user.email", "t@t"); git(root, "config", "user.name", "t")
    git(root, "add", "-A"); git(root, "commit", "-qm", "init", "--no-verify")
    return git(root, "rev-parse", "HEAD")


class LedgerMixin:
    def ledger(self, *a):
        return run("ledger", *a, root=self.t)

    def add(self, creator="writer", finding="bad claim", proposal=False):
        extra = ["--proposal"] if proposal else []
        rc, out = self.ledger("add", "--creator", creator, "--report", "r.md", "--location", "sec 2", "--finding", finding, *extra)
        self.assertEqual(rc, 0, out); return out.strip().split()[-1]

    def text(self, rel):
        return (self.t / rel).read_text()

    def rows(self, rel=None):
        return fl.rows(self.t / (rel or fl.LEDGER_REL))


class TestLedger(LedgerMixin, FixtureCase):
    def test_add_creates_from_template(self):
        self.assertEqual(self.add(), "F-001"); self.assertEqual(self.add(), "F-002")
        t = self.text(fl.LEDGER_REL)
        self.assertTrue(t.startswith("# Finding ledger")); self.assertIn("| id | created |", t)
        self.assertEqual([r["status"] for r in self.rows()], ["open", "open"])

    def test_pipe_escaped_roundtrip(self):
        self.add(finding="a | b")
        self.assertIn(r"a \| b", self.text(fl.LEDGER_REL))
        self.assertEqual(self.rows()[0]["finding"], "a | b")

    def test_close_bad_sha(self):
        init_repo(self.t); self.add()
        self.assertEqual(self.ledger("close", "F-001", "--sha", "deadbeef")[0], 1)

    def test_close_real_sha_and_guard(self):
        sha = init_repo(self.t); self.add()
        rc, out = self.ledger("close", "F-001", "--sha", sha, "--guard", "stopifnot in tbl-main")
        self.assertEqual(rc, 0, out)
        r = self.rows()[0]
        self.assertEqual(r["status"], "closed " + sha[:7]); self.assertEqual(r["guard"], "stopifnot in tbl-main")

    def test_close_needs_sha_or_pending(self):
        self.add(); self.assertEqual(self.ledger("close", "F-001")[0], 2)

    def test_close_unknown_id(self):
        self.add(); self.assertEqual(self.ledger("close", "F-009", "--pending")[0], 1)

    def test_decline_requires_reason_and_by(self):
        self.add()
        self.assertEqual(self.ledger("decline", "F-001", "--by", "session")[0], 2)
        self.assertEqual(self.ledger("decline", "F-001", "--reason", "x")[0], 2)

    def test_decline_logs_ruling(self):
        self.add()
        rc, out = self.ledger("decline", "F-001", "--reason", "out of scope", "--by", "session"); self.assertEqual(rc, 0, out)
        self.assertEqual(self.rows()[0]["status"], "declined: out of scope")
        rr = self.rows(fl.RULINGS_REL)
        self.assertEqual(len(rr), 1)
        self.assertEqual((rr[0]["date"], rr[0]["by"], rr[0]["decision"], rr[0]["alternative"], rr[0]["reason"]),
                         (TODAY, "session", "F-001 declined", "fix it", "out of scope"))

    def test_post_blocks_open_then_passes(self):
        self.log("writer"); self.add()
        rc, out = run("post", "writer", root=self.t)
        self.assertEqual(rc, 1); self.assertRegex(out, r"ledger-closed: 1 open for writer: F-001")
        sha = init_repo(self.t)
        self.assertEqual(self.ledger("close", "F-001", "--sha", sha)[0], 0)
        self.assertIn("ledger-closed: no open findings", run("post", "writer", root=self.t)[1])

    def test_other_creator_does_not_block(self):
        self.log("writer"); self.add(creator="coder")
        self.assertIn("ledger-closed: no open findings", run("post", "writer", root=self.t)[1])

    def test_no_ledger_file_passes(self):
        self.assertIn("ledger-closed: no open findings", run("post", "writer", root=self.t)[1])

    def test_proposal_lifecycle(self):
        self.add(finding="restructure", proposal=True)
        self.assertEqual(self.rows()[0]["status"], "proposal: pending")
        self.assertEqual(len(fl.blocking(self.t / fl.LEDGER_REL, "writer")), 1)
        self.assertEqual(self.ledger("reject", "F-001", "--by", "session")[0], 2)   # reason required
        rc, out = self.ledger("reject", "F-001", "--by", "session", "--reason", "r"); self.assertEqual(rc, 0, out)
        self.assertEqual(fl.blocking(self.t / fl.LEDGER_REL, "writer"), [])
        rr = self.rows(fl.RULINGS_REL)
        self.assertEqual((rr[0]["decision"], rr[0]["alternative"], rr[0]["by"]), ("F-001 rejected", "accept it", "session"))

    def test_proposal_accept_blocks_until_closed(self):
        self.add(finding="p", proposal=True)
        rc, out = self.ledger("accept", "F-001", "--by", "author"); self.assertEqual(rc, 0, out)
        self.assertEqual(self.rows()[0]["status"], "proposal: accepted")
        self.assertEqual(len(fl.blocking(self.t / fl.LEDGER_REL, "writer")), 1)
        rr = self.rows(fl.RULINGS_REL); self.assertEqual((rr[0]["decision"], rr[0]["alternative"]), ("F-001 accepted", "reject it"))
        sha = init_repo(self.t)
        self.assertEqual(self.ledger("close", "F-001", "--sha", sha)[0], 0)
        self.assertEqual(fl.blocking(self.t / fl.LEDGER_REL, "writer"), [])

    def test_accept_only_on_proposal(self):
        self.add(); self.assertEqual(self.ledger("accept", "F-001", "--by", "author")[0], 1)

    def test_show(self):
        self.add(); self.add(creator="coder")
        rc, out = self.ledger("show", "--creator", "coder", "--open")
        self.assertEqual(rc, 0); self.assertIn("F-002", out); self.assertNotIn("F-001", out)

    def test_ruling_add(self):
        rc, out = run("ruling", "add", "--decision", "d", "--alternative", "a", "--reason", "why", root=self.t)
        self.assertEqual(rc, 0, out)
        r = self.rows(fl.RULINGS_REL)[0]
        self.assertEqual((r["date"], r["by"], r["decision"]), (TODAY, "session", "d"))
        self.assertEqual(run("ruling", "add", "--decision", "d", "--reason", "why", root=self.t)[0], 2)

    def test_question_add(self):
        rc, out = run("question", "add", "--text", "Which sample?", "--blocks", "strategy", root=self.t)
        self.assertEqual(rc, 0, out)
        t = self.text(fl.QUESTIONS_REL)
        self.assertIn(f"## {TODAY} — blocks strategy", t); self.assertIn("Which sample?", t)

    def test_templates_found_through_symlinked_scripts(self):
        link = self.t / ".claude" / "scripts" / "pipeline.py"
        os.symlink(ROOT / "scripts" / "pipeline.py", link)
        p = subprocess.run([sys.executable, str(link), "--root", str(self.t), "ruling", "add", "--decision", "d",
                            "--alternative", "a", "--reason", "r"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(self.text(fl.RULINGS_REL).startswith("# Rulings log"))


class TestLedgerPending(LedgerMixin, StaleCase):
    def make_stale(self):
        self.fp("A"); self.score("manuscript", "writer-critic"); self.fp("B")

    def ms_commit(self):
        ms = self.t / "manuscript_fixture.qmd"; ms.write_text(ms.read_text() + "\nx\n")
        git(self.t, "add", "-A"); git(self.t, "commit", "-qm", "ms", "--no-verify")
        return git(self.t, "rev-parse", "HEAD")[:7]

    def test_pending_refused_when_not_stale(self):
        self.add()
        self.assertEqual(self.ledger("close", "F-001", "--pending")[0], 1)

    def test_pending_and_settle(self):
        init_repo(self.t); self.log("writer"); self.add(); self.make_stale()
        rc, out = self.ledger("close", "F-001", "--pending"); self.assertEqual(rc, 0, out)
        self.assertEqual(self.rows()[0]["status"], "closed pending")
        self.assertNotIn("ledger-closed: 1 open", run("post", "writer", root=self.t)[1])
        # a non-manuscript commit settles nothing
        (self.t / "other.txt").write_text("o"); git(self.t, "add", "-A"); git(self.t, "commit", "-qm", "o", "--no-verify")
        self.assertEqual(self.ledger("settle")[0], 0)
        self.assertEqual(self.rows()[0]["status"], "closed pending")
        # manuscript commit while still stale: stays pending
        self.ms_commit(); self.assertEqual(self.ledger("settle")[0], 0)
        self.assertEqual(self.rows()[0]["status"], "closed pending")
        # re-score, then a manuscript commit: settles to that commit
        self.score("manuscript", "writer-critic")
        sha7 = self.ms_commit(); self.assertEqual(self.ledger("settle")[0], 0)
        self.assertEqual(self.rows()[0]["status"], "closed " + sha7)


class TestRideAlongs(StaleCase):
    def test_hook_silent_on_config_error(self):
        os.symlink(ROOT / "scripts" / "pipeline.py", self.t / ".claude" / "scripts" / "pipeline.py")
        (self.t / "CLAUDE.md").write_text("# no declaration\n")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.t))
        p = subprocess.run([sys.executable, str(ROOT / "hooks" / "stale-stages.py")], capture_output=True, text=True, env=env)
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_next_skips_manuscript_lookup_for_components_that_do_not_go_stale(self):
        import inspect, pipeline
        self.score("code", "coder-critic")
        real = pipeline.declared_manuscript; callers = []
        def spy(root):
            callers.append(inspect.stack()[1].function); return real(root)
        pipeline.declared_manuscript = spy
        try:
            pipeline.next_report(self.t, pipeline.load_reg(self.t))
        finally:
            pipeline.declared_manuscript = real
        self.assertNotIn("next_report", callers)


if __name__ == "__main__":
    unittest.main()
