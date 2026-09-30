"""Shared fixture for the ZotPilot eval-checker tests: runs a checker over a synthetic transcript
that records a skill load, so the checker's load assertions can be exercised without a live run."""
import json, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(check, transcript, mock_log, skill, load="project"):
    """load: "project" (loaded from <eval dir>/.claude/skills), "personal"
    (/Users/x/.claude/skills), or None (no load recorded). Never touches the real ~/.claude."""
    with tempfile.TemporaryDirectory() as d:
        pt, pe = pathlib.Path(d, "t.jsonl"), pathlib.Path(d, "e.log")
        base = {"project": f"{d}/.claude/skills/{skill}", "personal": f"/Users/x/.claude/skills/{skill}"}.get(load)
        head = ""
        if base:
            head = json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "text", "text": f"Base directory for this skill: {base}\n"}]}}) + "\n"
        pt.write_text(head + transcript); pe.write_text(mock_log)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=d)
        r = subprocess.run([sys.executable, str(check), str(pt), str(pe)], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout
