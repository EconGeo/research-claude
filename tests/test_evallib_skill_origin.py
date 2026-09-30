import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "evals"))
import evallib

def transcript(d, base):
    line = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": f"Base directory for this skill: {base}\n\n# ZTP"}]}}
    p = pathlib.Path(d) / "eval.stream.jsonl"; p.write_text(json.dumps(line) + "\n"); return p

class T(unittest.TestCase):
    def test_project_copy_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, f"{d}/.claude/skills/ztp-research")), [])
    def test_personal_copy_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, "/Users/x/.claude/skills/ztp-research")),
                             ["/Users/x/.claude/skills/ztp-research"])
    def test_unrelated_skill_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(evallib.skills_loaded_outside_project(transcript(d, "/Users/x/.claude/skills/regression-table")), [])

if __name__ == "__main__": unittest.main()
