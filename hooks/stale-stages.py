#!/usr/bin/env python3
"""stale-stages.py — SessionStart: name the review stages a re-estimation or design change made stale.

Spec §0.6. Silent when nothing is stale, when the project has no state file, or when pipeline.py
is not linked. Never blocks a session. Fails open.

Hook Event: SessionStart
"""
import json, os, subprocess, sys
from pathlib import Path

def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    script = root / ".claude" / "scripts" / "pipeline.py"
    if not script.exists() or not (root / "quality_reports" / "pipeline_state.json").exists():
        return 0
    p = subprocess.run([sys.executable, str(script), "--root", str(root), "stale"], capture_output=True, text=True, timeout=20)
    if p.returncode != 1:
        return 0
    # exit 1 also means a config error (no `manuscript:` line); only STALE lines are a finding
    body = "\n".join(ln for ln in p.stdout.splitlines() if ln.startswith("STALE ")).strip()
    if not body:
        return 0
    print(json.dumps({"systemMessage": "Stale review stages:\n" + body,
                      "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
                          "## Stale review stages\n\n```\n" + body + "\n```\n\nWhile the manuscript stage is stale, manuscript "
                          "commits are refused until it is re-scored under the current fingerprint (rule 15 of .claude/rules/core.md)."}}))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
