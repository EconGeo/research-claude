#!/usr/bin/env python3
"""author_token.py — the author's one-time approval for `pipeline.py design sign|unlock` (spec §0.3).

The author approves in chat; .claude/hooks/design-token.py (UserPromptSubmit) turns the approval line
into this token, and `design sign|unlock` refuses without a fresh one. An unattended run has no
author message, so it cannot sign or unlock. The approval grammar and the freshness rules are
stated in .claude/rules/core.md rule 13; keep the two in step.
"""
from __future__ import annotations
import datetime as dt, json, re
from pathlib import Path
from typing import Optional, Tuple

TOKEN_REL = Path(".claude") / "state" / "design_token.json"
TTL = dt.timedelta(minutes=30)
APPROVAL_RE = re.compile(r"^approve design (sign|unlock)(?:\s*:\s*(\S.*?))?\.?$", re.I)
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")

def _now(now: Optional[dt.datetime]) -> dt.datetime:
    return now or dt.datetime.now(dt.timezone.utc)

def approval(prompt: str) -> Optional[Tuple[str, Optional[str]]]:
    found = []; in_fence = False
    for raw in (prompt or "").replace("\r\n", "\n").split("\n"):
        if FENCE_RE.match(raw):
            in_fence = not in_fence; continue
        m = None if in_fence else APPROVAL_RE.match(raw.strip())
        if m:
            found.append((m.group(1).lower(), (m.group(2) or "").strip() or None))
    if len(found) != 1:
        return None
    op, reason = found[0]
    if op == "unlock" and not reason:
        return None
    return op, (reason if op == "unlock" else None)

def _path(root: Path) -> Path:
    return root / TOKEN_REL

def _read(root: Path) -> Optional[dict]:
    p = _path(root)
    return json.loads(p.read_text()) if p.exists() else None

def issue(root: Path, op: str, reason: Optional[str], design_hash: Optional[str], now: Optional[dt.datetime] = None) -> None:
    p = _path(root); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"op": op, "reason": reason, "design_hash": design_hash,
                             "issued_at": _now(now).isoformat(), "used_at": None}, indent=2) + "\n")

def revoke_unused(root: Path) -> None:
    t = _read(root)
    if t is not None and t.get("used_at") is None:
        _path(root).unlink()

def check(root: Path, op: str, design_hash: Optional[str], reason: Optional[str] = None,
          now: Optional[dt.datetime] = None) -> Tuple[bool, str]:
    t = _read(root)
    if t is None:
        return False, f"no author token — the author approves in chat with the line `approve design {op}`" + (": <reason>`" if op == "unlock" else "`")
    if t.get("used_at"):
        return False, f"the author token was already used at {t['used_at']} — the author approves again in chat"
    if t.get("op") != op:
        return False, f"the author approved `design {t.get('op')}`, not `design {op}`"
    if _now(now) - dt.datetime.fromisoformat(t["issued_at"]) > TTL:
        return False, "the author token expired (30 minutes) — the author approves again in chat"
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
