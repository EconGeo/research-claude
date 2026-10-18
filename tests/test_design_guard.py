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

if __name__ == "__main__": unittest.main()
