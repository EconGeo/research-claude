#!/usr/bin/env python3
"""design-token.py — UserPromptSubmit: the author's chat approval becomes a one-time token.

Spec §0.3. A line `approve design sign` or `approve design unlock: <reason>` in the author's own
message issues .claude/state/design_token.json for the design block as it stands now; any other
message revokes an unused token. `pipeline.py design sign|unlock` spends it. A line
`approve sources: <id>[, <id>…]` issues the same file as a `sources` token for those ids (no design
hash), carrying each id's claim, registry-entry and source-file hashes as they stand at that message
(no token at all, with the reason in additionalContext, if they cannot be taken); `pipeline.py
sources approve <id>…` spends it only while they still match. Never blocks a prompt. Fails open on
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
import source_check

def say(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))

def sources_token(root: Path, reason: str) -> int:
    """Issue a sources token bound to what the author saw: per id, the claim, registry entry and
    source file hashes as they stand at this message. If they cannot be taken, issue no token."""
    id_list = tok.source_ids(reason)
    ids = ", ".join(id_list)
    try:
        ms = source_check.declared_manuscript(root)
        if ms is None or not ms.is_file():
            raise ValueError("no declared manuscript (CLAUDE.md `manuscript:` line)")
        prints = source_check.fingerprints(root, ms.read_text(encoding="utf-8"), id_list)
    except (ValueError, OSError, UnicodeDecodeError) as err:
        tok.revoke_unused(root)
        say(f"design-token: the author's line `approve sources: {ids}` issued no token: {err}. "
            "Nothing can be approved; tell the author why and let them approve again.")
        return 0
    tok.issue(root, "sources", reason, None, fingerprints=prints)
    say(f"design-token: the author approved sources {ids} in this message. The token is good for one "
        f"`pipeline.py sources approve` this turn, with exactly these ids: {ids}, and only while each "
        "claim, its registry entry and its source file are as they stand now.")
    return 0

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
        return sources_token(root, reason)
    ms = dsb.manuscript_path(root)
    tok.issue(root, op, reason, dsb.design_hash(ms.read_text()) if ms and ms.exists() else None)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
        f"design-token: the author approved `design {op}` in this message. The token is good for one "
        "`pipeline.py design " + op + "` this turn, for the design block exactly as it stands now."}}))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: sys.exit(0)
