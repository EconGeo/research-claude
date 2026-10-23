import datetime as dt, json, pathlib, shutil, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_guard_hooks import ProjectCase
from test_design_block import BASE
import author_token as tok, design_block as dsb
HOOK = ROOT / "hooks" / "design-token.py"
T0 = dt.datetime(2026, 10, 20, 12, 0, tzinfo=dt.timezone.utc)

class TestApprovalGrammar(unittest.TestCase):
    def test_exact_lines(self):
        self.assertEqual(tok.approval("approve design sign"), ("sign", None))
        self.assertEqual(tok.approval("Looks right.\n  Approve design sign.  \n"), ("sign", None))
        self.assertEqual(tok.approval("approve design unlock: cluster at state level"),
                         ("unlock", "cluster at state level"))
    def test_not_approvals(self):
        for msg in ("approve design unlock", "please approve design sign", "> approve design sign",
                    "```\napprove design sign\n```", "I approve the design sign-off",
                    "approve design sign\napprove design sign", "don't approve design sign yet", "approve design sign: not yet",
                    "approve design sign:", ""):
            self.assertIsNone(tok.approval(msg), msg)

class TestTokenRules(unittest.TestCase):
    def setUp(self): self.r = pathlib.Path(tempfile.mkdtemp())
    def tearDown(self): shutil.rmtree(self.r)
    def test_one_use(self):
        tok.issue(self.r, "sign", None, "h", now=T0)
        self.assertTrue(tok.consume(self.r, "sign", "h", now=T0)[0])
        ok, why = tok.consume(self.r, "sign", "h", now=T0); self.assertFalse(ok); self.assertIn("already used", why)
    def test_expiry(self):
        tok.issue(self.r, "sign", None, "h", now=T0)
        ok, why = tok.check(self.r, "sign", "h", now=T0 + dt.timedelta(minutes=31)); self.assertFalse(ok); self.assertIn("expired", why)
    def test_op_hash_and_reason_must_match(self):
        tok.issue(self.r, "unlock", "why", "h", now=T0)
        self.assertFalse(tok.check(self.r, "sign", "h", now=T0)[0])
        self.assertIn("different design block", tok.check(self.r, "unlock", "other", reason="why", now=T0)[1])
        self.assertIn("reason", tok.check(self.r, "unlock", "h", reason="not why", now=T0)[1])
        self.assertTrue(tok.check(self.r, "unlock", "h", reason="why", now=T0)[0])
    def test_missing(self):
        ok, why = tok.check(self.r, "sign", "h"); self.assertFalse(ok); self.assertIn("no author token", why)

class TestHook(ProjectCase):
    def setUp(self): super().setUp(); self.ms.write_text(BASE)
    def prompt(self, text):
        return self.run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "prompt": text})
    def token(self):
        p = self.proj / tok.TOKEN_REL
        return json.loads(p.read_text()) if p.exists() else None
    def test_issues_on_approval(self):
        out = self.prompt("approve design sign")
        self.assertEqual(self.token()["op"], "sign"); self.assertEqual(self.token()["design_hash"], dsb.design_hash(BASE))
        self.assertIn("design-token", out)
    def test_next_message_revokes_unused(self):
        self.prompt("approve design sign"); self.prompt("actually, wait")
        self.assertIsNone(self.token())
    def test_used_token_kept_as_record(self):
        self.prompt("approve design sign"); tok.consume(self.proj, "sign", dsb.design_hash(BASE))
        self.prompt("thanks"); self.assertIsNotNone(self.token()["used_at"])
    def test_no_claude_md_is_silent(self):
        (self.proj / "CLAUDE.md").unlink(); self.assertEqual(self.prompt("approve design sign"), "")

if __name__ == "__main__": unittest.main()
