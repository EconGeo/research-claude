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

    def test_write_tool_also_protected(self):
        code, _ = run("Write", "/tmp/proj/quality_reports/pipeline_state.json")
        self.assertEqual(code, 2)

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
