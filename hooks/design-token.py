#!/usr/bin/env python3
"""design-token.py — UserPromptSubmit: the author's chat approval becomes a one-time token.

Spec §0.3. A line `approve design sign` or `approve design unlock: <reason>` in the author's own
message issues .claude/state/design_token.json for the design block as it stands now; any other
message revokes an unused token. `pipeline.py design sign|unlock` spends it. A line
`approve sources: <id>[, <id>…]` issues the same file as a `sources` token for those ids (no design
hash), which `pipeline.py sources approve <id>…` spends. Never blocks a prompt. Fails open on
internal error.

Approval grammar (.claude/rules/core.md rule 13): a whole line, trimmed, case-insensitive, optionally
ending in one `.`; not inside a fenced block or a `>` quote; exactly one per message.

tested: 2026-10-18, `claude -p "approve design sign"` in a scratch project wired with the seed
settings fired this hook, and the payload key `prompt` carried the message (the token file appeared).

Known limit: a prompt submitted by a nested `claude -p` fires UserPromptSubmit too, so this hook
cannot tell it from the author's; the design-guard hook refuses Bash commands that run `claude`
with an approval line.

Hook Event: UserPromptSubmit
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import author_token as tok
import design_block as dsb

def main() -> int:
    payload = json.load(sys.stdin)
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).resolve()
    if not (root / "CLAUDE.md").exists():
        return 0
    found = tok.approval(payload.get("prompt", ""))
    if found is None:
        tok.revoke_unused(root); return 0
    op, reason = found
    if op == "sources":
        tok.issue(root, "sources", reason, None)
        ids = ", ".join(tok.source_ids(reason))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
            f"design-token: the author approved sources {ids} in this message. The token is good for one "
            f"`pipeline.py sources approve` this turn, with exactly these ids: {ids}."}}))
        return 0
    ms = dsb.manuscript_path(root)
    tok.issue(root, op, reason, dsb.design_hash(ms.read_text()) if ms and ms.exists() else None)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
        f"design-token: the author approved `design {op}` in this message. The token is good for one "
        "`pipeline.py design " + op + "` this turn, for the design block exactly as it stands now."}}))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
