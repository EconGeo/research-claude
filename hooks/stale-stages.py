#!/usr/bin/env python3
"""stale-stages.py — SessionStart: name the review stages a re-estimation or design change made stale.

Spec §0.6. Silent when nothing is stale, when the project has no state file, or when pipeline.py
is not linked. Never blocks a session. Fails open, but says so when `pipeline.py stale` crashes or
times out.

Hook Event: SessionStart
"""
import json, os, subprocess, sys
from pathlib import Path

def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    script = root / ".claude" / "scripts" / "pipeline.py"
    if not script.exists() or not (root / "quality_reports" / "pipeline_state.json").exists():
        return 0
    try:
        p = subprocess.run([sys.executable, str(script), "--root", str(root), "stale"], capture_output=True, text=True, timeout=20)
        # A crash exits 1 like a finding does; a traceback with no STALE line tells them apart. The
        # config errors (`pipeline.py: …` via sys.exit) stay silent, as before.
        crashed = p.returncode not in (0, 1) or (p.returncode == 1 and "Traceback" in p.stderr
                                                 and "STALE " not in p.stdout)
        failed = f"exit {p.returncode}: {(p.stderr.strip().splitlines() or [''])[-1]}" if crashed else None
    except subprocess.TimeoutExpired:
        failed = "timed out after 20 s"
    if failed:
        # A check that could not run says so, rather than looking like "nothing is stale" (audit 2026-11-04).
        print(json.dumps({"systemMessage": f"stale-stages: could not check for stale review stages ({failed}). "
                                           "Run `python3 .claude/scripts/pipeline.py stale` to see why."}))
        return 0
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
