import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_guard_hooks import ProjectCase
from test_design_block import BASE
import author_token as tok, design_block as db
HOOK = ROOT / "hooks" / "design-guard.py"

class TestDesignGuard(ProjectCase):
    def setUp(self):
        super().setUp(); self.ms.write_text(BASE)
    def sign(self):
        db.write_lock(self.proj, {"status": "signed", "hash": db.design_hash(BASE)})
    def edit(self, old, new, path=None):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(path or self.ms), "old_string": old, "new_string": new}})
    def write(self, path, content="x"):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Write",
            "tool_input": {"file_path": str(path), "content": content}})
    def bash(self, cmd):
        return self.run_hook(HOOK, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})

    def test_unsigned_project_allows_design_edits(self):
        self.assertFalse(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_signed_blocks_design_edit(self):
        self.sign(); self.assertTrue(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_signed_allows_title_and_body(self):
        self.sign()
        self.assertFalse(self.denied(self.edit('title: "T"', 'title: "U"')))
        self.assertFalse(self.denied(self.edit("Body text.", "New body.")))
    def test_signed_blocks_write_changing_block(self):
        self.sign(); self.assertTrue(self.denied(self.write(self.ms, BASE.replace("region", "state"))))
    def test_unlocked_status_allows(self):
        db.write_lock(self.proj, {"status": "unlocked", "hash": db.design_hash(BASE)})
        self.assertFalse(self.denied(self.edit("cluster: region", "cluster: state")))
    def test_sign_and_unlock_need_a_token(self):
        cmds = ("python3 .claude/scripts/pipeline.py design sign --signer me",
                "cd x && python3 .claude/scripts/pipeline.py --root . design unlock --reason r")
        for c in cmds: self.assertTrue(self.denied(self.bash(c)), c)
        tok.issue(self.proj, "sign", None, db.design_hash(BASE))
        self.assertFalse(self.denied(self.bash(cmds[0])))
        self.assertTrue(self.denied(self.bash(cmds[1])))                       # a sign token is not an unlock token
        self.assertFalse(self.denied(self.bash("python3 .claude/scripts/pipeline.py design status")))
    def test_record_files_are_pipeline_only(self):
        for rel in ("quality_reports/design_lock.json", ".claude/state/design_token.json",
                    "quality_reports/design_amendments.csv", "quality_reports/render_fingerprint.json",
                    "quality_reports/findings_ledger.md", "quality_reports/rulings_log.md"):
            self.assertTrue(self.denied(self.write(self.proj / rel)), rel)
        self.assertTrue(self.denied(self.bash("python3 -c \"open('.claude/state/design_token.json','w')\"")))
    def test_bash_inplace_write_blocked_when_signed(self):
        self.sign()
        self.assertTrue(self.denied(self.bash("sed -i '' 's/region/state/' manuscript_p.qmd")))
        self.assertFalse(self.denied(self.bash("grep cluster manuscript_p.qmd")))

    def test_token_filename_not_substring(self):
        self.assertFalse(self.denied(self.bash("python3 -m pytest -q tests/test_design_token.py")))
        self.assertTrue(self.denied(self.bash("cat .claude/state/design_token.json")))

    def test_nested_claude_cannot_submit_an_approval(self):
        for cmd in ('claude -p "approve design sign"', 'claude -p "Approve Design unlock: x"',
                    'npx claude -p "approve design sign"', '/usr/local/bin/claude -p "approve design sign"',
                    'cd x && claude --print "approve design unlock: r"'):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)
        for cmd in ('claude -p "summarise the design"', "echo approve design sign",
                    "ls .claude/scripts && echo approve design sign"):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)

    def test_guard_refuses_nested_approve_sources(self):
        for cmd in ('claude -p "approve sources: t1"', 'claude -p "Approve  Sources: t1, t2"',
                    'cd x && npx claude --print "approve sources: design"'):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)
        for cmd in ('claude -p "summarise the sources"', "echo approve sources: t1"):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)
    def test_source_approvals_are_pipeline_only(self):
        self.assertTrue(self.denied(self.write(self.proj / "quality_reports/source_approvals.csv")))
        self.assertFalse(self.denied(self.write(self.proj / "quality_reports/sources.csv")))

    # Final review finding 3: Bash cannot forge an approval row.
    def test_bash_cannot_write_source_approvals(self):
        for cmd in ("echo 't1,ok,a,b,c,d' >> quality_reports/source_approvals.csv",
                    "python3 -c \"open('quality_reports/source_approvals.csv','a').write('x')\"",
                    "cat forged.csv > quality_reports/source_approvals.csv",
                    "cp /tmp/forged.csv quality_reports/source_approvals.csv",
                    "printf x | tee -a quality_reports/source_approvals.csv",
                    "sed -i '' 's/a/b/' quality_reports/source_approvals.csv",
                    "git checkout HEAD~3 -- quality_reports/source_approvals.csv",
                    "python3 .claude/scripts/pipeline.py sources approve t1 && echo x >> quality_reports/source_approvals.csv",
                    "cat quality_reports/source_approvals.csv | python3 -c 'import sys'"):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)
        for cmd in ("python3 .claude/scripts/pipeline.py sources approve t1 t2",
                    "cat quality_reports/source_approvals.csv",
                    "git add quality_reports/source_approvals.csv quality_reports/sources.csv",
                    "git diff -- quality_reports/source_approvals.csv",
                    "head -5 quality_reports/source_approvals.csv"):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)

    def test_author_token_module_is_hook_only(self):
        for cmd in ('python3 -c "import author_token as t; t.issue(\'.\', \'sign\', None, \'h\')"',
                    "cd .claude/scripts && python3 -m author_token", "cat .claude/scripts/author_token.py"):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)

    def test_claude_fed_from_file_heredoc_or_pipe(self):
        for cmd in ("cat f | claude -p", "claude -p < prompt.txt", "claude -p <<EOF\nhello\nEOF",
                    "claude -p <<< \"$msg\"", "echo hi | npx claude --print", "cd x && cat f |claude -p",
                    "claude -p < <(cat f)", "printf x | /usr/local/bin/claude -p",
                    "cat f | FOO=1 npx -y claude -p", "(claude -p < f)"):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)
        for cmd in ('claude -p "summarise the design"', 'claude -p "x" 2>&1 | tail -5',
                    'claude -p "x" > out.txt', "cat f | grep claude", "ps aux | grep claude",
                    "grep claude < notes.txt", "ls | wc -l && claude -p \"y\""):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)

    def test_interpreter_naming_design_lock_denied(self):
        for cmd in ("python3 -c \"import json; json.dump({}, open('quality_reports/design_lock.json','w'))\"",
                    "perl -e 'open(F, \">quality_reports/design_lock.json\")'", "node -e \"fs.writeFileSync('design_lock.json','{}')\"",
                    "Rscript -e 'writeLines(\"{}\", \"quality_reports/design_lock.json\")'",
                    "ruby -e 'File.write(\"design_lock.json\", \"x\")'", "python -c 'print(1)' design_lock.json"):
            self.assertTrue(self.denied(self.bash(cmd)), cmd)

    def test_ordinary_commands_stay_allowed(self):
        for cmd in ("python3 .claude/scripts/pipeline.py design status", "pytest tests/test_design_token.py",
                    "python3 -m pytest -q tests/test_design_lock.py", "cat quality_reports/design_lock.json",
                    "git add quality_reports/design_lock.json", 'claude -p "summarise the design"'):
            self.assertFalse(self.denied(self.bash(cmd)), cmd)

    def test_bash_without_trigger_words_returns_before_any_read(self):
        # The common case: no design/claude/token/write word in the command. The hook must answer
        # without reading the manuscript or lock — shown by removing them and expecting no error.
        self.sign(); self.ms.unlink(); (self.proj / db.LOCK_REL).write_text("{not json")
        for cmd in ("ls -la", "git status", "python3 -m pytest -q tests", "quarto render paper.qmd 2>&1 | tail"):
            p = self.bash(cmd); self.assertFalse(self.denied(p), cmd)
        # and a command that could matter still goes through every check
        self.ms.write_text(BASE); (self.proj / db.LOCK_REL).unlink(); self.sign()
        self.assertTrue(self.denied(self.bash(f"sed -i '' 's/a/b/' {self.ms.name}")))

if __name__ == "__main__": unittest.main()
