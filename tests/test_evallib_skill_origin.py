import json, os, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "evals"))
import evallib

def transcript(d, base):
    """Create a stream transcript with base dir in message."""
    line = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": f"Base directory for this skill: {base}\n\n# ZTP"}]}}
    p = pathlib.Path(d) / "eval.stream.jsonl"; p.write_text(json.dumps(line) + "\n"); return p

def transcript_with_session(d, session_id, base):
    """Create a stream transcript with session_id + session transcript with base dir."""
    stream_line = {"type": "result", "session_id": session_id, "message": {"role": "user", "content": []}}
    stream_path = pathlib.Path(d) / "eval.stream.jsonl"
    stream_path.write_text(json.dumps(stream_line) + "\n")

    # Create session transcript directory and file
    session_dir = pathlib.Path(d) / "projects" / "x"
    session_dir.mkdir(parents=True)
    session_line = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": f"Base directory for this skill: {base}\n\n# ZTP"}]}}
    session_path = session_dir / f"{session_id}.jsonl"
    session_path.write_text(json.dumps(session_line) + "\n")
    return stream_path

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

    def test_session_transcript_personal_copy_reported(self):
        with tempfile.TemporaryDirectory() as d:
            old_env = os.environ.get("CLAUDE_CONFIG_DIR")
            try:
                os.environ["CLAUDE_CONFIG_DIR"] = d
                path = transcript_with_session(d, "test-session-1", "/Users/x/.claude/skills/ztp-research")
                self.assertEqual(evallib.skills_loaded_outside_project(str(path)),
                                 ["/Users/x/.claude/skills/ztp-research"])
            finally:
                if old_env:
                    os.environ["CLAUDE_CONFIG_DIR"] = old_env
                else:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_session_transcript_project_copy_clean(self):
        with tempfile.TemporaryDirectory() as d:
            old_env = os.environ.get("CLAUDE_CONFIG_DIR")
            try:
                os.environ["CLAUDE_CONFIG_DIR"] = d
                path = transcript_with_session(d, "test-session-2", f"{d}/.claude/skills/ztp-research")
                self.assertEqual(evallib.skills_loaded_outside_project(str(path)), [])
                self.assertNotEqual(evallib.skill_loads(str(path)), [])
            finally:
                if old_env:
                    os.environ["CLAUDE_CONFIG_DIR"] = old_env
                else:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_no_skill_loads_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            old_env = os.environ.get("CLAUDE_CONFIG_DIR")
            try:
                os.environ["CLAUDE_CONFIG_DIR"] = d
                # Create stream with session_id but no loads in transcript
                stream_line = {"type": "result", "session_id": "test-session-3", "message": {"role": "user", "content": []}}
                stream_path = pathlib.Path(d) / "eval.stream.jsonl"
                stream_path.write_text(json.dumps(stream_line) + "\n")

                # Create empty session transcript
                session_dir = pathlib.Path(d) / "projects" / "x"
                session_dir.mkdir(parents=True)
                session_line = {"type": "user", "message": {"role": "user", "content": [
                    {"type": "text", "text": "No skill load here"}]}}
                session_path = session_dir / "test-session-3.jsonl"
                session_path.write_text(json.dumps(session_line) + "\n")

                self.assertEqual(evallib.skill_loads(str(stream_path)), [])
            finally:
                if old_env:
                    os.environ["CLAUDE_CONFIG_DIR"] = old_env
                else:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)

if __name__ == "__main__": unittest.main()
