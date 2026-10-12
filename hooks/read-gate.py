#!/usr/bin/env python3
"""read-gate.py — no edit to the manuscript by an agent that has not read all of it.

Enforces the global "Read before asserting" rule at the one point where skipping it is most
expensive: changing the declared manuscript (`manuscript: <file>.qmd` in the project's
CLAUDE.md). One file, two events:

  PostToolUse  Read|Edit|Write   record which lines of the manuscript this agent has read, and
                                 the file's size/mtime after each of its own reads and edits
  PreToolUse   Edit|Write|Bash   refuse a change unless this agent has read every line, and the
                                 file has not changed since (someone else's edit — the user in
                                 VS Code, a subagent — means a fresh read is needed)

"This agent" is keyed by session_id + agent_id, so a dispatched writer must read the manuscript
itself; the main session reading it does not count for the subagent, and vice versa.

Large manuscripts get a section gate instead. A full read of a 1 MB manuscript costs ~250k
tokens per agent, so above FULL_READ_MAX_LINES an Edit inside one code chunk needs that whole
chunk, and any other Edit needs every line of the level-1/level-2 section(s) it touches
(headings inside chunks and the YAML header are ignored), not the whole file. Write,
`replace_all` and Bash writes still need the whole file. A project can force full reads at any
size with a line `read-gate: full` in its CLAUDE.md.

Coverage comes from the Read result's `file.startLine/numLines/totalLines` when present, else
from tool_input offset/limit (default limit 2000, the Read tool's default). Chunked reads add up.
State is session-scoped under the system temp dir, never in the repo. Bash is gated best-effort
for in-place writes that name the manuscript (`sed -i`, `perl -i`, `>`, `>>`, `tee`, `cp`/`mv`
onto it). Fails open on any internal error.
"""
# Hook Event: PostToolUse|PreToolUse
import json, os, re, sys, tempfile
from pathlib import Path

DEFAULT_LIMIT = 2000
FULL_READ_MAX_LINES = 3000
HEADING = re.compile(r"^#{1,2}\s")
FENCE = re.compile(r"^\s*(```|~~~)")


def manuscript_path():
    root = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not root:
        return None
    claude_md = Path(root) / "CLAUDE.md"
    if not claude_md.exists():
        return None
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", claude_md.read_text(errors="ignore"), re.M)
    if len(hits) != 1:
        return None
    return (Path(root) / hits[0]).resolve()


def state_file(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "nosession")
    d = Path(tempfile.gettempdir()) / "claude-read-gate"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def stat_sig(p: Path):
    s = p.stat()
    return [s.st_size, s.st_mtime_ns]


def line_count(p: Path) -> int:
    with p.open("rb") as fh:
        n = sum(1 for _ in fh)
    return n


def merge(ranges):
    out = []
    for lo, hi in sorted(ranges):
        if out and lo <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def gaps(ranges, total):
    """Unread [lo, hi] spans of 1..total."""
    missing, nxt = [], 1
    for lo, hi in merge(ranges):
        if lo > nxt:
            missing.append([nxt, min(lo - 1, total)])
        nxt = max(nxt, hi + 1)
    if nxt <= total:
        missing.append([nxt, total])
    return [g for g in missing if g[0] <= g[1]]


def force_full() -> bool:
    claude_md = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")) / "CLAUDE.md"
    try:
        return bool(re.search(r"^read-gate:\s*full\s*$", claude_md.read_text(errors="ignore"), re.M))
    except OSError:
        return False


def sections_touched(text: str, old: str):
    """[lo, hi] the agent must have read to edit `old`, or None when `old` is absent.

    An edit wholly inside one code chunk needs that chunk, fences included. Anything else needs
    the level-1/2 section(s) it spans. Headings inside chunks (R comments) and inside the YAML
    front matter do not count as section breaks.
    """
    at = text.find(old) if old else -1
    if at < 0:
        return None
    first = text.count("\n", 0, at) + 1
    last = first + old.count("\n")
    lines = text.splitlines()
    heads, chunks, open_at = [], [], None
    start = 1
    if lines and lines[0].strip() == "---":
        end_yaml = next((i for i, l in enumerate(lines[1:], 2) if l.strip() in ("---", "...")), 1)
        start = end_yaml + 1
    for i in range(start, len(lines) + 1):
        line = lines[i - 1]
        if FENCE.match(line):
            if open_at is None:
                open_at = i
            else:
                chunks.append((open_at, i)); open_at = None
        elif open_at is None and HEADING.match(line):
            heads.append(i)
    for lo, hi in chunks:
        if lo <= first and last <= hi:
            return [lo, hi]
    lo = max([h for h in heads if h <= first], default=1)
    nxt = [h for h in heads if h > last]
    hi = (nxt[0] - 1) if nxt else len(lines)
    return [lo, hi]


def same_file(a, b: Path) -> bool:
    try:
        return Path(a).resolve() == b
    except (OSError, ValueError):
        return False


def read_range(tool_input: dict, tool_response) -> list:
    info = tool_response.get("file") if isinstance(tool_response, dict) else None
    if isinstance(info, dict) and "startLine" in info and "numLines" in info:
        start = int(info["startLine"])
        return [start, start + max(int(info["numLines"]), 1) - 1]
    start = max(int(tool_input.get("offset") or 1), 1)
    limit = int(tool_input.get("limit") or DEFAULT_LIMIT)
    return [start, start + limit - 1]


def bash_writes(command: str, ms: Path) -> bool:
    name = re.escape(ms.name)
    if not re.search(name, command):
        return False
    patterns = [
        r"\bsed\b[^|;&]*\s-i",
        r"\bperl\b[^|;&]*\s-[a-z]*i",
        r">>?\s*\S*" + name,
        r"\btee\b[^|;&]*" + name,
        r"\b(cp|mv)\b[^|;&]*" + name + r"\s*($|[;&|])",
    ]
    return any(re.search(p, command) for p in patterns)


def deny(reason: str):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    ms = manuscript_path()
    if ms is None:
        return 0

    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    agent_key = payload.get("agent_id") or "main"
    sf = state_file(payload.get("session_id", ""))
    state = load_state(sf)
    rec = state.get(agent_key, {"ranges": [], "sig": None, "total": None})

    if event == "PostToolUse":
        if not ms.exists() or not same_file(tool_input.get("file_path", ""), ms):
            return 0
        total_now = line_count(ms)
        if tool == "Read":
            if rec["sig"] is not None and rec["sig"] != stat_sig(ms):
                rec["ranges"] = []  # file changed under us: earlier chunks no longer count
            rec["ranges"] = merge(rec["ranges"] + [read_range(tool_input, payload.get("tool_response"))])
        elif tool in ("Edit", "Write"):
            # Coverage is judged against the line count the reads were made at, so an edit that
            # shifts lines keeps a full read full (a Write means the agent wrote every line).
            known_total = rec.get("total") or total_now
            if tool == "Write" or not gaps(rec["ranges"], known_total):
                rec["ranges"] = [[1, total_now]]
        else:
            return 0
        rec["sig"] = stat_sig(ms)
        rec["total"] = total_now
        state[agent_key] = rec
        sf.write_text(json.dumps(state))
        return 0

    if event != "PreToolUse" or not ms.exists():
        return 0  # creating a brand-new manuscript needs no prior read
    if tool in ("Edit", "Write"):
        if not same_file(tool_input.get("file_path", ""), ms):
            return 0
    elif tool == "Bash":
        if not bash_writes(tool_input.get("command", ""), ms):
            return 0
    else:
        return 0

    total = line_count(ms)
    changed = rec["sig"] is not None and rec["sig"] != stat_sig(ms)
    ranges = [] if changed else rec["ranges"]
    section = None
    if (tool == "Edit" and total > FULL_READ_MAX_LINES and not tool_input.get("replace_all")
            and not force_full()):
        section = sections_touched(ms.read_text(errors="ignore"), tool_input.get("old_string", ""))
        if section is None:
            return 0  # old_string not in the file: the Edit tool will refuse it itself
    if section:
        lo, hi = section
        missing = [[max(a, lo), min(b, hi)] for a, b in gaps(ranges, hi) if b >= lo]
        what = f"the chunk or section you are editing (lines {lo}-{hi})"
    else:
        missing = gaps(ranges, total if changed else (rec.get("total") or total))
        what = f"all {total} lines"
    if missing:
        spans = ", ".join(f"{a}-{b}" for a, b in missing[:8])
        why = (f"{ms.name} changed since you last read it (another agent, the user, or a tool "
               f"outside Edit/Write)" if changed else f"you have not read {what} of {ms.name}")
        deny(f"read-gate: {why}. Unread lines: {spans}. Read {what} before changing it — Read "
             f"with offset/limit in chunks of {DEFAULT_LIMIT}. Rule: read before asserting "
             f"(~/.claude/CLAUDE.md).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open — a hook bug must never block the session
