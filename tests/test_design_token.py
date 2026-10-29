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
    def test_approval_sources_line(self):
        self.assertEqual(tok.approval("approve sources: t2, t1"), ("sources", "t2,t1"))
        self.assertEqual(tok.approval("Read them.\n  Approve Sources: a,b ,design.  \n"), ("sources", "a,b,design"))
        self.assertEqual(tok.approval("approve sources: t1"), ("sources", "t1"))
    def test_sources_needs_ids(self):
        for msg in ("approve sources", "approve sources:", "approve sources: ", "approve sources: ,",
                    "approve sources: a,,b", "approve sources: all of them", "> approve sources: t1",
                    "```\napprove sources: t1\n```", "please approve sources: t1",
                    "approve sources: t1\napprove design sign", "approve sources t1"):
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
    def test_sources_ids_set_equality(self):
        tok.issue(self.r, "sources", "t1,t2", None, now=T0)
        self.assertTrue(tok.check(self.r, "sources", None, reason="t2,t1", now=T0)[0])
        self.assertIn("t1,t2", tok.check(self.r, "sources", None, reason="t1", now=T0)[1])
        self.assertFalse(tok.check(self.r, "sign", None, now=T0)[0])     # a sources token is not a design token
    def test_sources_missing_names_the_line(self):
        self.assertIn("approve sources:", tok.check(self.r, "sources", None, reason="t1")[1])
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
    def sources_project(self):
        import csv, source_check as sc
        (self.proj / "src.txt").write_text("Intro.\n\nThe Firm shall disclose the fee. Then the rule took effect.\n")
        self.ms.write_text(BASE + '\n[A claim.]{.src ref="ok" id="t1"}\n')
        reg = self.proj / "quality_reports" / "sources.csv"
        reg.parent.mkdir(exist_ok=True)
        with open(reg, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=sc.REGISTRY_COLS)
            w.writeheader()
            w.writerow({"id": "ok", "file": "src.txt", "label": "L", "page": "1",
                        "sentence": "The Firm shall disclose the fee.", "cleanup": "", "ocr": ""})
            w.writerow({"id": "design:key2024", "file": "src.txt", "label": "L", "page": "1",
                        "sentence": "", "cleanup": "", "ocr": ""})
        return sc
    def test_issues_sources_token(self):
        sc = self.sources_project()
        out = self.prompt("approve sources: t1, design")
        t = self.token()
        self.assertEqual((t["op"], t["reason"], t["design_hash"]), ("sources", "t1,design", None))
        self.assertIn("t1, design", out)
        # Final review finding 2: the token carries what the author saw at approval.
        self.assertEqual(t["fingerprints"], sc.fingerprints(self.proj, self.ms.read_text(), ["t1", "design"]))
    def test_sources_token_not_issued_without_fingerprints(self):
        self.sources_project()
        self.prompt("approve design sign")                      # an unused token, to be revoked
        out = self.prompt("approve sources: t1, nope")
        self.assertIsNone(self.token())
        self.assertIn("no token", out)
        self.assertIn("nope", out)
    def test_next_message_revokes_unused(self):
        self.prompt("approve design sign"); self.prompt("actually, wait")
        self.assertIsNone(self.token())
    def test_used_token_kept_as_record(self):
        self.prompt("approve design sign"); tok.consume(self.proj, "sign", dsb.design_hash(BASE))
        self.prompt("thanks"); self.assertIsNotNone(self.token()["used_at"])
    def test_no_claude_md_is_silent(self):
        (self.proj / "CLAUDE.md").unlink(); self.assertEqual(self.prompt("approve design sign"), "")

if __name__ == "__main__": unittest.main()
