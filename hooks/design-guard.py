#!/usr/bin/env python3
"""design-guard.py — PreToolUse (Write|Edit|Bash): the signed design block is the author's.

Spec §4, §0.3. Once quality_reports/design_lock.json says `signed`, no agent edit may change the
manuscript's `design:` front-matter block. `design sign|unlock` run only with the author's
one-time token, issued by `.claude/hooks/design-token.py` from an approval line in the author's own chat
message. The lock, the token and the record files are written only by pipeline.py or the render.
Bash writes to the manuscript are refused while signed (use Edit, which this hook can evaluate).
A Bash command that invokes `claude` and contains the text `approve design` is refused: a nested
`claude -p` would fire UserPromptSubmit and self-issue the token. The author approves in their own
chat message; a session never submits an approval line.
Fails open on internal error.

Hook Event: PreToolUse
"""
import json, os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import author_token as tok
import design_block as db

SIGN_RE = re.compile(r"pipeline\.py\b[^\n;&|]*\bdesign\s+(sign|unlock)\b")
INPLACE_RE = r"(sed\s+-i|perl\s+-[a-z]*i|>>?|\btee\b|\bcp\b|\bmv\b)[^\n;&|]*{name}"
CLAUDE_RE = re.compile(r"(?:^|[\s;&|(`/])claude(?=[\s;&|)`]|$)")
PIPELINE_ONLY = {"design_lock.json", "design_token.json", "design_amendments.csv", "design_amendments.md",
                 "render_fingerprint.json", "cold_render.json", "findings_ledger.md", "rulings_log.md"}

def deny(msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "deny", "permissionDecisionReason": "design-guard: " + msg}}))

def main() -> int:
    payload = json.load(sys.stdin); root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    tool = payload.get("tool_name", ""); ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "") if tool == "Bash" else ""
    if tool in ("Edit", "Write") and Path(ti.get("file_path", "")).name in PIPELINE_ONLY:
        deny(f"{Path(ti['file_path']).name} is written only by pipeline.py or the render."); return 0
    if "design_token" in cmd:
        deny("the author token is written only by the design-token hook."); return 0
    if cmd and CLAUDE_RE.search(cmd) and re.search(r"approve\s+design", cmd, re.I):
        deny("a session never submits an approval line (a nested claude would self-issue the author "
             "token); the author approves in their own chat message."); return 0
    ms = db.manuscript_path(root)
    text = ms.read_text() if ms and ms.exists() else ""
    m = SIGN_RE.search(cmd)
    if m:
        ok, why = tok.check(root, m.group(1), db.design_hash(text))
        if not ok: deny(f"`design {m.group(1)}` needs the author's approval in chat: {why}")
        return 0
    lock = db.read_lock(root)
    if not ms or not ms.exists() or not lock or lock.get("status") != "signed": return 0
    if tool == "Bash":
        if re.search(INPLACE_RE.format(name=re.escape(ms.name)), cmd):
            deny(f"the design is signed; edit {ms.name} with the Edit tool so the design block can be checked.")
        return 0
    if tool not in ("Edit", "Write") or Path(ti.get("file_path", "")).resolve() != ms: return 0
    if tool == "Write": new = ti.get("content", "")
    else:
        old, rep = ti.get("old_string", ""), ti.get("new_string", "")
        new = text.replace(old, rep) if ti.get("replace_all") else text.replace(old, rep, 1)
    if db.design_hash(new) != lock.get("hash"):
        deny("this edit changes the signed design: block. Ask the author to approve in chat with "
             "`approve design unlock: <reason>`; then run `pipeline.py design unlock --reason \"<reason>\"`.")
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
