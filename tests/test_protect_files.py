"""Contracts for hooks/protect-files.sh.

Wired by default since 2026-09-24 (Phase 4.1, divergence D-3) after the hook shipped
dead for months: the pattern matching in `[[ "$BASENAME" == "$PATTERN" ]]` quotes the
pattern, which turns off glob matching in bash and makes every wildcard pattern compare
as a literal string, so it never matched anything, including before this hook was ever
touched today. Cases below exercise wildcard patterns specifically for that reason, not
just the literal ones.
"""
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "protect-files.sh"


def run(tool_name, file_path):
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"file_path": file_path}})
    p = subprocess.run([str(HOOK)], input=payload, capture_output=True, text=True)
    return p.returncode, p.stderr


class TestProtectFiles(unittest.TestCase):
    def assertBlocked(self, file_path):
        code, err = run("Edit", file_path)
        self.assertEqual(code, 2, f"{file_path} should be blocked, stderr={err!r}")
        self.assertIn(pathlib.Path(file_path).name, err)

    def assertAllowed(self, tool_name, file_path):
        code, _ = run(tool_name, file_path)
        self.assertEqual(code, 0, f"{file_path} should be allowed")

    def test_literal_patterns_blocked(self):
        self.assertBlocked("/tmp/proj/.claude/settings.json")
        self.assertBlocked("/tmp/proj/quality_reports/pipeline_state.json")

    def test_receipts_jsonl_blocked(self):
        """The receipt log is an append-only audit trail; nothing should be able to
        rewrite it via Edit/Write, same as pipeline_state.json."""
        self.assertBlocked("/tmp/proj/quality_reports/receipts.jsonl")

    def test_wildcard_critic_report_blocked(self):
        """The glob-quoting bug meant this never matched before the fix."""
        self.assertBlocked("/tmp/proj/quality_reports/reviews/writer-critic_1.md")
        self.assertBlocked("/tmp/proj/quality_reports/reviews/coder-critic_3.md")

    def test_wildcard_ai_audit_reports_blocked(self):
        self.assertBlocked("/tmp/proj/quality_reports/civilize_final_report.md")
        self.assertBlocked("/tmp/proj/quality_reports/verify_claims_2026-09-24.md")

    def test_peer_review_reports_blocked(self):
        self.assertBlocked("/tmp/proj/quality_reports/peer_review_1/desk_review.md")
        self.assertBlocked("/tmp/proj/quality_reports/peer_review_1/referee_domain.md")
        self.assertBlocked("/tmp/proj/quality_reports/peer_review_1/referee_methods.md")

    def test_ordinary_manuscript_edit_allowed(self):
        self.assertAllowed("Edit", "/tmp/proj/manuscript_foo.qmd")

    def test_non_edit_tool_allowed(self):
        self.assertAllowed("Bash", "/tmp/proj/quality_reports/pipeline_state.json")

    def test_write_over_an_existing_protected_file_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d, "pipeline_state.json"); f.write_text("{}")
            code, _ = run("Write", str(f))
            self.assertEqual(code, 2)

    def test_write_that_creates_a_protected_file_allowed(self):
        """2026-09-24, live fixture: every critic returns text and the SESSION saves it to
        quality_reports/reviews/<critic>_<date>.md — a Write that CREATES a file matching
        `*-critic_*.md`. Blocking creation meant `post` could never see a report, so no
        stage could close (the driver stopped at `data` with `post explorer: FAIL`). The
        protection exists to stop a later restamp of a committed report, which is the
        Edit/overwrite case; creation is the pipeline working."""
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d, "quality_reports", "reviews", "explorer-critic_2026-09-24.md")
            self.assertAllowed("Write", str(f))
            self.assertFalse(f.exists())
            code, _ = run("Edit", str(f))
            self.assertEqual(code, 2, "Edit of a protected path is blocked even when absent")

    def test_hook_is_wired_in_the_seed(self):
        seed = json.loads((ROOT / "seeds" / "settings.json").read_text())
        commands = [
            h["command"]
            for block in seed["hooks"].get("PreToolUse", [])
            for h in block["hooks"]
        ]
        self.assertTrue(
            any("protect-files.sh" in c for c in commands),
            "protect-files.sh must be wired in seeds/settings.json's PreToolUse — "
            "seeding it only reaches new projects; check_install.sh's hooks-wired "
            "derives its required set from this file",
        )


if __name__ == "__main__":
    unittest.main()
