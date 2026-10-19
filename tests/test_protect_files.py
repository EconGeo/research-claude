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


def run_bash(cmd, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if cwd: payload["cwd"] = cwd
    p = subprocess.run([str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True)
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

    def test_timestamped_strategy_memo_protected_undated_name_not(self):
        """2026-09-25: memos are `strategy_memo_<YYYY-MM-DD_HHMM>.md`, one per round, created once
        and never rewritten — so the timestamped name is protected. The old fixed name was
        rewritten every strategist→critic round and protecting it blocked the revision loop;
        the digit class also keeps `strategy_memo_review*.md` out of the pattern."""
        self.assertBlocked("/tmp/proj/quality_reports/strategy/proj/strategy_memo_2026-09-25_1430.md")
        self.assertAllowed("Edit", "/tmp/proj/quality_reports/strategy/proj/strategy_memo.md")
        self.assertAllowed("Edit", "/tmp/proj/quality_reports/strategy/proj/strategy_memo_review.md")

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

    def test_bash_shell_writes_to_protected_files_blocked(self):
        for cmd in ("echo x > quality_reports/pipeline_state.json", "rm quality_reports/design_lock.json",
                    "cp a.json quality_reports/design_lock.json", "sed -i '' s/a/b/ .claude/state/design_token.json",
                    "echo x | tee quality_reports/findings_ledger.md", "mv x quality_reports/rulings_log.md",
                    "tee -a quality_reports/findings_ledger.md", "git rm quality_reports/rulings_log.md",
                    "cp seeds/settings.json .claude/settings.json"):
            code, err = run_bash(cmd)
            self.assertEqual(code, 2, cmd)

    def test_bash_reads_and_other_commands_allowed(self):
        for cmd in ("cat quality_reports/pipeline_state.json", "grep x quality_reports/design_lock.json",
                    "python3 .claude/scripts/pipeline.py status", "ls quality_reports && echo done > notes.txt",
                    "jq . quality_reports/receipts.jsonl | head", "quarto render manuscript_p.qmd 2>&1 | tail -5"):
            code, err = run_bash(cmd)
            self.assertEqual(code, 0, f"{cmd}: {err}")

    def test_bash_names_without_writing_are_allowed(self):
        for cmd in ('git commit -m "a -> settings.json"', 'git commit -m "x rm findings_ledger.md"',
                    "cp .claude/settings.json /tmp/x", 'grep -n ">" .claude/settings.json'):
            code, err = run_bash(cmd)
            self.assertEqual(code, 0, f"{cmd}: {err}")

    def test_bash_critic_report_create_allowed_overwrite_denied(self):
        with tempfile.TemporaryDirectory() as d:
            new = pathlib.Path(d, "explorer-critic_2026-10-18.md")
            code, err = run_bash(f"cat > {new} <<EOF\nbody 'it's\nEOF", cwd=d)
            self.assertEqual(code, 0, err)
            new.write_text("x")
            code, _ = run_bash(f"cat > {new} <<EOF\nbody\nEOF", cwd=d)
            self.assertEqual(code, 2)
            code, _ = run_bash("echo x >> explorer-critic_2026-10-18.md", cwd=d)
            self.assertEqual(code, 2)

    def test_bash_ampersand_redirect_dd_and_here_string(self):
        for cmd in ("echo x &> quality_reports/pipeline_state.json", "echo x &>> quality_reports/rulings_log.md",
                    "make &>quality_reports/design_lock.json",
                    "dd if=/dev/null of=quality_reports/design_lock.json", "dd of='quality_reports/cold_render.json' bs=1",
                    "cat <<< x\necho y > quality_reports/pipeline_state.json",
                    "tr a b <<< \"$x\" > .claude/settings.json"):
            code, err = run_bash(cmd)
            self.assertEqual(code, 2, cmd)
        for cmd in ("dd if=quality_reports/design_lock.json of=/tmp/copy.json", "cat <<< x\necho y > notes.txt",
                    "echo x &> build.log"):
            code, err = run_bash(cmd)
            self.assertEqual(code, 0, f"{cmd}: {err}")

    def test_bash_unparseable_command_falls_back_to_a_scan(self):
        """shlex fails on a quoted string that spans lines; that used to exit 0 (fail open)."""
        for cmd in ('git commit -m "a\nb" && echo x > quality_reports/pipeline_state.json',
                    'git commit -m "a\nb" && rm quality_reports/design_lock.json',
                    'echo "a\nb" | tee quality_reports/findings_ledger.md',
                    'git commit -m "a\nb" ; dd of=quality_reports/cold_render.json',
                    'echo "a\nb" &>> quality_reports/rulings_log.md'):
            code, err = run_bash(cmd)
            self.assertEqual(code, 2, cmd)
        for cmd in ('git commit -m "a\nb"', 'git commit -m "first\nsecond" && echo ok > notes.txt'):
            code, err = run_bash(cmd)
            self.assertEqual(code, 0, f"{cmd}: {err}")

    def test_bash_unparseable_create_of_new_report_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            code, err = run_bash('echo "a\nb" > explorer-critic_2026-10-18.md', cwd=d)
            self.assertEqual(code, 0, err)

    def test_new_record_files_protected_for_edit(self):
        for n in ("design_lock.json", "design_token.json", "design_amendments.csv", "design_amendments.md",
                  "render_fingerprint.json", "cold_render.json", "findings_ledger.md", "rulings_log.md"):
            self.assertBlocked("/tmp/proj/quality_reports/" + n)

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
