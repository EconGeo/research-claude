#!/usr/bin/env python3
"""author_token.py — the author's one-time approval for `pipeline.py design sign|unlock` (spec §0.3)
and for `pipeline.py sources approve <id>…` (the line `approve sources: <id>[, <id>…]`).

The author approves in chat; .claude/hooks/design-token.py (UserPromptSubmit) turns the approval line
into this token, and `design sign|unlock` refuses without a fresh one. An unattended run has no
author message, so it cannot sign or unlock. The approval grammar and the freshness rules are
stated in .claude/rules/core.md rule 13; keep the two in step.

Known limit: a prompt submitted by a nested `claude -p` fires UserPromptSubmit too, so the hook
cannot tell it from the author's; the design-guard hook refuses Bash commands that run `claude`
with an approval line.
"""
from __future__ import annotations
import datetime as dt, json, re
from pathlib import Path
from typing import Optional, Tuple

TOKEN_REL = Path(".claude") / "state" / "design_token.json"
TTL = dt.timedelta(minutes=30)
APPROVAL_RE = re.compile(r"^approve design (sign|unlock)(?:\s*(:)\s*(\S.*?)?)?\.?$", re.I)
SOURCES_RE = re.compile(r"^approve sources(?:\s*:\s*(\S.*?)?)?\.?$", re.I)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")

def _now(now: Optional[dt.datetime]) -> dt.datetime:
    return now or dt.datetime.now(dt.timezone.utc)

def source_ids(text: Optional[str]) -> Optional[list]:
    """The ids of `approve sources: a, b` in order, or None unless every comma-separated item is
    one word (so `approve sources: all of them` approves nothing)."""
    ids = [i.strip() for i in (text or "").split(",")]
    if not ids or any(not i or re.search(r"\s", i) for i in ids):
        return None
    return ids

def approval(prompt: str) -> Optional[Tuple[str, Optional[str]]]:
    found = []; in_fence = False
    for raw in (prompt or "").replace("\r\n", "\n").split("\n"):
        if FENCE_RE.match(raw):
            in_fence = not in_fence; continue
        line = "" if in_fence else raw.strip()
        m = APPROVAL_RE.match(line)
        if m:
            found.append((m.group(1).lower(), (m.group(3) or "").strip() or None, bool(m.group(2))))
        m = SOURCES_RE.match(line)
        if m:
            found.append(("sources", m.group(1), True))
    if len(found) != 1:
        return None
    op, reason, has_colon = found[0]
    if op == "sources":
        ids = source_ids(reason)
        return ("sources", ",".join(ids)) if ids else None
    if op == "unlock" and not reason:
        return None
    if op == "sign" and has_colon:
        return None
    return op, (reason if op == "unlock" else None)

def _name(op: Optional[str]) -> str:
    return "sources" if op == "sources" else f"design {op}"

def _path(root: Path) -> Path:
    return root / TOKEN_REL

def _read(root: Path) -> Optional[dict]:
    p = _path(root)
    return json.loads(p.read_text()) if p.exists() else None

def issue(root: Path, op: str, reason: Optional[str], design_hash: Optional[str], now: Optional[dt.datetime] = None,
          fingerprints: Optional[dict] = None) -> None:
    """Write the token. A sources token carries `fingerprints`: per tag id, the claim, registry
    entry and source file hashes as they stood when the author approved."""
    p = _path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    token = {"op": op, "reason": reason, "design_hash": design_hash,
             "issued_at": _now(now).isoformat(), "used_at": None}
    if fingerprints is not None:
        token["fingerprints"] = fingerprints
    p.write_text(json.dumps(token, indent=2) + "\n")

def revoke_unused(root: Path) -> None:
    t = _read(root)
    if t is not None and t.get("used_at") is None:
        _path(root).unlink()

def check(root: Path, op: str, design_hash: Optional[str], reason: Optional[str] = None,
          now: Optional[dt.datetime] = None) -> Tuple[bool, str]:
    t = _read(root)
    if t is None:
        if op == "sources":
            return False, "no author token — the author approves in chat with the line `approve sources: <id>[, <id>…]`"
        return False, f"no author token — the author approves in chat with the line `approve design {op}`" + (": <reason>`" if op == "unlock" else "`")
    if t.get("used_at"):
        return False, f"the author token was already used at {t['used_at']} — the author approves again in chat"
    if t.get("op") != op:
        return False, f"the author approved `{_name(t.get('op'))}`, not `{_name(op)}`"
    if _now(now) - dt.datetime.fromisoformat(t["issued_at"]) > TTL:
        return False, "the author token expired (30 minutes) — the author approves again in chat"
    # The sources token carries no design hash; its ids are the binding (set equality, any order).
    if op == "sources" and reason is not None and set(source_ids(reason) or []) != set(source_ids(t.get("reason")) or []):
        return False, f"the author approved sources {t.get('reason')!r}; approve exactly those ids"
    if t.get("design_hash") != design_hash:
        return False, "the author approved a different design block — show the author the block as it stands and ask again"
    # reason=None skips this comparison (design-guard's pre-check); the CLI always passes --reason.
    if op == "unlock" and reason is not None and " ".join(reason.split()) != " ".join((t.get("reason") or "").split()):
        return False, f"--reason must be the author's reason, verbatim: {t.get('reason')!r}"
    return True, t["issued_at"]

def consume(root: Path, op: str, design_hash: Optional[str], reason: Optional[str] = None,
            now: Optional[dt.datetime] = None) -> Tuple[bool, str]:
    ok, why = check(root, op, design_hash, reason, now)
    if ok:
        t = _read(root); t["used_at"] = _now(now).isoformat()
        _path(root).write_text(json.dumps(t, indent=2) + "\n")
    return ok, why
