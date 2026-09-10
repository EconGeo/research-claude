"""The three session-continuity hooks must read and write an artifact that
`rules/logging.md` actually defines.

Before this file, `log-reminder.py` told sessions to create
`quality_reports/session_logs/<date>_*.md`, and `pre-compact.py` and
`post-compact-restore.py` read that directory for compaction recovery — but
`rules/logging.md` defines exactly four artifacts and names no such directory.
Compaction recovery was reading a directory nothing was instructed to write.

The fix is NOT a fifth artifact. `rules/session-handoff.md` settles it: session
continuity "is already designed" around `SESSION_REPORT.md` and
`research_journal.md`, and "the fix is not another document" — that rule uses
"becomes a second session log" to name the failure it is warding off. So the
hooks repoint at `SESSION_REPORT.md`, which `rules/logging.md` §Session Report
mandates be appended to "at end of session or before context compression".
"""

import importlib.util, io, json, os, pathlib, sys, tempfile, unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(stem):
    spec = importlib.util.spec_from_file_location(
        stem.replace("-", "_"), ROOT / "hooks" / f"{stem}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENTRY = """# Session Report — Fixture

## 2026-09-09 11:00 — Earlier work

**Decisions:**
- Chose the mechanical tier — the live tier needs a real Zotero library

## 2026-09-10 14:30 — The most recent entry

**Operations:**
- Ran the fixture

**Decisions:**
- Repointed the hooks at SESSION_REPORT.md — logging.md defines no session_logs
- Kept `JHE` in the health entries — a global rename corrupts them

**Status:**
- Done: the repoint
"""


class TestLogReminder(unittest.TestCase):
    """The Stop advisory must name the artifact logging.md mandates."""

    def setUp(self):
        self.mod = _load("log-reminder")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_finds_session_report_at_project_root(self):
        p = pathlib.Path(self.tmp) / "SESSION_REPORT.md"
        p.write_text(ENTRY)
        found, mtime = self.mod.find_session_report(self.tmp)
        self.assertEqual(found, p)
        self.assertGreater(mtime, 0.0)

    def test_finds_session_report_under_docs_when_root_has_none(self):
        """research-claude's own CLAUDE.md relocates it to docs/SESSION_REPORT.md.
        A hook that only checks the root would nag forever in this very repo."""
        docs = pathlib.Path(self.tmp) / "docs"
        docs.mkdir()
        p = docs / "SESSION_REPORT.md"
        p.write_text(ENTRY)
        found, _ = self.mod.find_session_report(self.tmp)
        self.assertEqual(found, p)

    def test_root_wins_over_docs(self):
        root = pathlib.Path(self.tmp) / "SESSION_REPORT.md"
        root.write_text(ENTRY)
        docs = pathlib.Path(self.tmp) / "docs"
        docs.mkdir()
        (docs / "SESSION_REPORT.md").write_text(ENTRY)
        found, _ = self.mod.find_session_report(self.tmp)
        self.assertEqual(found, root)

    def test_returns_none_when_absent(self):
        found, mtime = self.mod.find_session_report(self.tmp)
        self.assertIsNone(found)
        self.assertEqual(mtime, 0.0)

    def test_advisory_names_session_report_not_session_logs(self):
        """The whole defect in one assertion: the nudge must not send the user to
        a directory no rule defines."""
        home = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(home, ignore_errors=True))
        buf = io.StringIO()
        argv_stdin = io.StringIO(json.dumps({"cwd": self.tmp}))
        old_stdin, old_home, old_pdir = sys.stdin, os.environ.get("HOME"), os.environ.get("CLAUDE_PROJECT_DIR")
        sys.stdin = argv_stdin
        os.environ["HOME"] = home
        os.environ["CLAUDE_PROJECT_DIR"] = self.tmp
        try:
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    self.mod.main()
            self.assertEqual(cm.exception.code, 0)
        finally:
            sys.stdin = old_stdin
            if old_home is not None:
                os.environ["HOME"] = old_home
            if old_pdir is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = old_pdir
        out = buf.getvalue()
        self.assertIn("hookSpecificOutput", out)
        self.assertIn("SESSION_REPORT.md", out)
        self.assertNotIn("session_logs", out)


class TestPreCompact(unittest.TestCase):
    """Decisions are captured from the section logging.md's entry format defines."""

    def setUp(self):
        self.mod = _load("pre-compact")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_extracts_decisions_from_the_latest_entry_only(self):
        (pathlib.Path(self.tmp) / "SESSION_REPORT.md").write_text(ENTRY)
        decisions = self.mod.extract_recent_decisions(self.tmp)
        self.assertEqual(len(decisions), 2)
        self.assertTrue(any("Repointed the hooks" in d for d in decisions))
        self.assertFalse(
            any("mechanical tier" in d for d in decisions),
            "decisions from a superseded entry are not current state",
        )

    def test_extracts_nothing_when_no_report(self):
        self.assertEqual(self.mod.extract_recent_decisions(self.tmp), [])

    def test_appends_compaction_marker_to_session_report(self):
        p = pathlib.Path(self.tmp) / "SESSION_REPORT.md"
        p.write_text(ENTRY)
        self.mod.append_compaction_note(self.tmp, "auto")
        text = p.read_text()
        self.assertTrue(text.startswith(ENTRY), "append-only: prior content is untouched")
        self.assertIn("Context compaction", text)
        self.assertIn("auto", text)

    def test_does_not_create_the_report(self):
        """A hook that conjures the file would make `/checkpoint`'s first entry
        land in a file it never wrote a header for."""
        self.mod.append_compaction_note(self.tmp, "auto")
        self.assertFalse((pathlib.Path(self.tmp) / "SESSION_REPORT.md").exists())


class TestPostCompactRestore(unittest.TestCase):
    """Restoration surfaces the last entry, not just a filename."""

    def setUp(self):
        self.mod = _load("post-compact-restore")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_surfaces_the_most_recent_entry_heading(self):
        (pathlib.Path(self.tmp) / "SESSION_REPORT.md").write_text(ENTRY)
        info = self.mod.find_session_report(self.tmp)
        self.assertIsNotNone(info)
        self.assertIn("SESSION_REPORT.md", info["report_path"])
        self.assertEqual(info["last_entry"], "2026-09-10 14:30 — The most recent entry")

    def test_none_when_absent(self):
        self.assertIsNone(self.mod.find_session_report(self.tmp))

    def test_report_reaches_the_restoration_message(self):
        (pathlib.Path(self.tmp) / "SESSION_REPORT.md").write_text(ENTRY)
        info = self.mod.find_session_report(self.tmp)
        msg = self.mod.format_restoration_message(None, None, None, info)
        self.assertIn("SESSION_REPORT.md", msg)
        self.assertIn("The most recent entry", msg)


class TestNoHookNamesSessionLogs(unittest.TestCase):
    """Belt and braces: the string must be gone from the shipped hooks entirely,
    so a future edit cannot quietly reintroduce the unauthorised directory."""

    def test_shipped_hooks_do_not_reference_session_logs(self):
        offenders = [
            p.name
            for p in (ROOT / "hooks").glob("*.py")
            if "session_logs" in p.read_text()
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
