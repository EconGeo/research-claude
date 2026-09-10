#!/usr/bin/env python3
"""critic-pairing.py — surface a creator that ran without its critic.

Hook Event: Stop
Reads quality_reports/agent_dispatch.jsonl (this session's lines) and .claude/rules/registry.yaml.
For every creator whose last completion has no later completion of its paired critic, emits:
  - hookSpecificOutput.additionalContext (Claude-visible) and systemMessage (user-visible), and
  - by default, ONE block per session per creator: {"decision":"block","reason":...}, guarded by
    stop_hook_active and a sentinel under ~/.claude/sessions/<hash>/. RC_CRITIC_PAIRING_ADVISORY=1
    turns the block off (advisory only). Fail open on any error.

Session filter: agent_dispatch.jsonl has two writers. dispatch-log.py (this hook's sibling,
SubagentStop) stamps a "session" key. pipeline.py's `append_log` (the `pipeline.py log <agent>`
standalone path that every stage skill's non-orchestrated step uses) does NOT — see
.claude/scripts/pipeline.py:101-103. A line with no "session" key is therefore unattributed, not
foreign: treat it as belonging to every session rather than dropping it, or this hook goes
blind to exactly the creators dispatched outside the orchestrated loop, which is the group
most likely to skip a critic. (R-113)
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

def session_dir(project: str) -> Path:
    d = Path.home() / ".claude" / "sessions" / (hashlib.md5(project.encode()).hexdigest()[:8] if project else "default")
    d.mkdir(parents=True, exist_ok=True); return d

def main() -> int:
    """Fail open, unconditionally: any exception the checks below don't already
    anticipate must still exit 0, or a Stop-hook crash puts a `<hook name> hook
    error` banner in front of the user on every single Stop event (Finding 1)."""
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
    if inp.get("stop_hook_active"):
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or inp.get("cwd") or ""
    if not project:
        return 0
    root = Path(project)
    sys.path.insert(0, str(root / ".claude" / "scripts"))
    try:
        import registry_lib as rl  # type: ignore
        reg = rl.load_yaml_subset((root / ".claude" / "rules" / "registry.yaml").read_text())
    except Exception:
        return 0
    if not isinstance(reg, dict) or not isinstance(reg.get("agents"), dict):
        return 0  # parses cleanly but lacks (or misshapes) the agents: block — mid-edit/mid-merge
    log_p = root / "quality_reports" / "agent_dispatch.jsonl"
    if not log_p.exists():
        return 0
    sid = inp.get("session_id", "")
    entries = []
    for ln in log_p.read_text().splitlines():
        try: e = json.loads(ln)
        except json.JSONDecodeError: continue
        if not isinstance(e, dict): continue  # same non-object case, one log line at a time
        if not sid or (e.get("session") or "") in ("", sid): entries.append(e)
    unpaired = []
    for creator in rl.creators(reg):
        crit = rl.critic_of(reg, creator)
        if not crit: continue
        last_c = max((e["at"] for e in entries if e.get("agent") == creator), default=None)
        last_k = max((e["at"] for e in entries if e.get("agent") == crit), default=None)
        if last_c and (last_k is None or last_k < last_c):
            unpaired.append((creator, crit))
    if not unpaired:
        return 0
    msg = "Creator ran without its critic this session: " + "; ".join(f"{c} → dispatch {k}" for c, k in unpaired) + \
          ". Dispatch the critic and record its score with `python3 .claude/scripts/pipeline.py state record-score` before stopping."
    out = {"systemMessage": "⚠ " + msg, "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
    if os.environ.get("RC_CRITIC_PAIRING_ADVISORY") != "1":
        if not sid:
            # Finding 2: the sentinel key is "<sid>:<creator>", keyed by project hash only. With
            # sid == "" every incident collapses onto the same ":<creator>" token, so a later
            # session's genuinely new unpaired creator would find its one block already spent —
            # permanently, since the sentinel is never pruned. "Once per session" isn't keepable
            # without a session id, so without one this always blocks and never writes a sentinel.
            out.update({"decision": "block", "reason": msg})
        else:
            sentinel = session_dir(project) / "critic-pairing-blocked.json"
            try: blocked = set(json.loads(sentinel.read_text())) if sentinel.exists() else set()
            except Exception: blocked = set()
            fresh = [c for c, _ in unpaired if f"{sid}:{c}" not in blocked]
            if fresh:
                try: sentinel.write_text(json.dumps(sorted(blocked | {f'{sid}:{c}' for c in fresh})))
                except OSError: pass
                out.update({"decision": "block", "reason": msg})
    print(json.dumps(out))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
