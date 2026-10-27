#!/usr/bin/env python3
"""design-guard.py — PreToolUse (Write|Edit|Bash): the signed design block is the author's.

Spec §4, §0.3. Once quality_reports/design_lock.json says `signed`, no agent edit may change the
manuscript's `design:` front-matter block. `design sign|unlock` run only with the author's
one-time token, issued by `.claude/hooks/design-token.py` from an approval line in the author's own chat
message. The lock, the token and the record files (including quality_reports/source_approvals.csv,
written by `pipeline.py sources approve` with an `approve sources:` token) are written only by
pipeline.py or the render.
Bash writes to the manuscript are refused while signed (use Edit, which this hook can evaluate).
A Bash command that invokes `claude` and contains the text `approve design` or `approve sources` is
refused: a nested `claude -p` would fire UserPromptSubmit and self-issue the token. So is any `claude` fed its prompt
by a `<` redirect, a heredoc or here-string, or a pipe (`cat f | claude -p`, `claude -p < f`),
whatever the text: the prompt is then not on the command line to check. A Bash command that names
`source_approvals` is refused unless each of its stages only reads or stages the file (cat, head,
grep, git add/diff/…, or `pipeline.py sources approve`) with no `>` beside the name. A Bash command that names
`author_token` (the token module) is refused, and so is one that names `design_lock` beside an
interpreter (python, perl, ruby, node, Rscript), which could write the lock directly. The author
approves in their own chat message; a session never submits an approval line.
Known limit: every Bash check here is a text match on the command. A command assembled from
variables or fragments (`c=claude; $c -p ...`, a path built from pieces) evades it, and so does an
indirect writer (a script file that does the write, run by name). The token's binding to the
design hash and its one-message lifetime bound the damage.
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
INTERP_RE = re.compile(r"(?:^|[\s;&|(`/])(?:python[\d.]*|perl|ruby|node|Rscript)(?=[\s;&|)`]|$)")

# `claude` as the command word of a pipeline stage: after env assignments and launch wrappers.
CLAUDE_CMD_RE = re.compile(r"^[\s({`]*(?:\w+=\S*\s+)*(?:(?:npx|exec|command|env|nohup|time|sudo|xargs)"
                           r"(?:\s+-\S+)*\s+)*(?:\S*/)?claude(?=[\s)`]|$)")

def fed_claude(cmd: str) -> bool:
    """A `claude` command word whose input is a `<` redirect, heredoc, here-string, or a pipe."""
    for seg in re.split(r"\n|;|&&|\|\||(?<![|>])&(?![&>])", cmd):
        parts = re.split(r"(?<!\|)\|(?!\|)", seg)
        for i, part in enumerate(parts):
            if CLAUDE_CMD_RE.search(part) and (i > 0 or "<" in part): return True
    return False

# A Bash command that names source_approvals may only read it or stage it: every stage of the
# command is one of these (or `pipeline.py sources approve`), and the stage naming it has no `>`.
APPROVALS_STAGE_RE = re.compile(r"^\s*(?:(?:cat|head|tail|wc|less|grep|ls|sort|column|echo|cd)\b"
                                r"|git\s+(?:add|diff|log|show|status)\b"
                                r"|\S*python[\d.]*\s+\S*pipeline\.py\b[^\n;&|]*\bsources\s+approve\b)")

def writes_approvals(cmd: str) -> bool:
    if "source_approvals" not in cmd:
        return False
    for stage in re.split(r"\n|;|&&|\|\||\||&", cmd):
        if not stage.strip():
            continue
        if not APPROVALS_STAGE_RE.match(stage):
            return True
        if "source_approvals" in stage and ">" in stage:
            return True
    return False

PIPELINE_ONLY = {"design_lock.json", "design_token.json", "design_amendments.csv", "design_amendments.md",
                 "source_approvals.csv",
                 "render_fingerprint.json", "cold_render.json", "findings_ledger.md", "rulings_log.md"}

def deny(msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "deny", "permissionDecisionReason": "design-guard: " + msg}}))

# A Bash command that names none of these can trip no check below, so it returns before any
# file is read (this hook runs on every Bash call; keep the common case to a regex).
BASH_TRIGGER_RE = re.compile(r"design|claude|author_token|source_approvals|pipeline\.py|sed|perl|tee|cp|mv|>|\.qmd", re.I)

def main() -> int:
    payload = json.load(sys.stdin); root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    tool = payload.get("tool_name", ""); ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "") if tool == "Bash" else ""
    if tool == "Bash" and not BASH_TRIGGER_RE.search(cmd): return 0
    if tool not in ("Bash", "Edit", "Write"): return 0
    if tool in ("Edit", "Write") and Path(ti.get("file_path", "")).name in PIPELINE_ONLY:
        deny(f"{Path(ti['file_path']).name} is written only by pipeline.py or the render."); return 0
    if re.search(r"design_token\.json", cmd):
        deny("the author token is written only by the design-token hook."); return 0
    if re.search(r"\bauthor_token\b", cmd):
        deny("the author token module is run only by the design-token hook and pipeline.py."); return 0
    if writes_approvals(cmd):
        deny("source_approvals.csv is written only by `pipeline.py sources approve` with the author's "
             "token; a Bash command naming it may only read or stage it.")
        return 0
    if cmd and fed_claude(cmd):
        deny("a nested claude may not take its prompt from a file, heredoc, here-string or pipe "
             "(the prompt could carry an approval line); pass the prompt as an argument."); return 0
    if re.search(r"\bdesign_lock\b", cmd) and INTERP_RE.search(cmd):
        deny("design_lock.json is written only by pipeline.py; an interpreter command may not name it."); return 0
    if cmd and CLAUDE_RE.search(cmd) and re.search(r"approve\s+(design|sources)", cmd, re.I):
        deny("a session never submits an approval line (a nested claude would self-issue the author "
             "token); the author approves in their own chat message."); return 0
    ms = db.manuscript_path(root)
    if not ms or not ms.exists(): return 0
    m = SIGN_RE.search(cmd)
    if m:
        ok, why = tok.check(root, m.group(1), db.design_hash(ms.read_text()))
        if not ok: deny(f"`design {m.group(1)}` needs the author's approval in chat: {why}")
        return 0
    if tool == "Bash":
        if not re.search(INPLACE_RE.format(name=re.escape(ms.name)), cmd): return 0
    elif Path(ti.get("file_path", "")).resolve() != ms: return 0
    lock = db.read_lock(root)                      # read only once the call can touch the manuscript
    if not lock or lock.get("status") != "signed": return 0
    if tool == "Bash":
        deny(f"the design is signed; edit {ms.name} with the Edit tool so the design block can be checked."); return 0
    text = ms.read_text()
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
