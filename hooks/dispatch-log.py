#!/usr/bin/env python3
"""dispatch-log.py — append one line per subagent completion.

Hook Event: SubagentStop
Input (stdin JSON, per docs): session_id, transcript_path, cwd, hook_event_name, agent_type
  (the subagent's name as dispatched), plus stop_hook_active. Older builds may send
  agent_name or subagent_type; all three are accepted.
Output: none (exit 0 always; fail open). Writes quality_reports/agent_dispatch.jsonl in
  $CLAUDE_PROJECT_DIR (or cwd). The line shape is what pipeline.py `critic-ran` reads.

Timestamp format MUST match pipeline.py's `now()` (UTC, explicit offset, millisecond
precision) exactly: `critic-ran` compares an `at` written here (agent_dispatch.jsonl,
gitignored, local) against one written by pipeline.py (pipeline_state.json, committed)
with a plain string `>`. A naive local-time, second-resolution string would compare
wrong across machines, go backwards at DST fall-back, and collide when a creator and
its critic finish inside the same second. See pipeline.py's `now()` docstring.
"""
from __future__ import annotations
import datetime as dt, json, os, sys
from pathlib import Path

def now() -> str:
    """Same format as pipeline.py `now()` — import it; fall back only if that fails."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from pipeline import now as pipeline_now  # type: ignore
        return pipeline_now()
    except Exception:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")

def main() -> int:
    """Fail open, unconditionally — any exception the checks below don't already
    anticipate must still exit 0 (Finding 1)."""
    try:
        return _run()
    except Exception:
        return 0

def _run() -> int:
    try:
        inp = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(inp, dict):
        return 0  # valid JSON, not an object — e.g. `42`, `[1,2,3]`, `"text"`, `null`
    agent = inp.get("agent_type") or inp.get("agent_name") or inp.get("subagent_type") or ""
    if not agent:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or ".")
    log = root / "quality_reports" / "agent_dispatch.jsonl"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps({"at": now(), "agent": agent,
                                "session": inp.get("session_id", ""), "source": "hook"}) + "\n")
    except OSError:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
