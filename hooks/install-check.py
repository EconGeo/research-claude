#!/usr/bin/env python3
"""
Install-Integrity Hook

Fires at SessionStart and runs check_install.sh against this project. When the
install is clean it prints NOTHING; when it is not, it injects the failing
checks into context so the session sees them before doing any work.

Why this exists. check_install.sh has always been able to detect a mis-installed
or contaminated pipeline -- dangling links, committed symlinks, stale membership,
project-local tooling shadowing a shared rule. It was invoked from exactly one
place: `/promote`, the workflow a paper session almost never runs. So the
diagnostic existed and nothing scheduled it, and on 2026-09-23 a single session
found, one trip-over at a time: a project-local skill that had silently waived a
real defect through two critic rounds for three months; four reference files
shadowing upstream with stale copies, one contradicting the very invariant the
project was scored against; a rule superseded months earlier still linked into
six repos; and two divergent copies of the same gate script. Every one of those
is a check_install.sh FAIL line. Nobody had run it.

A rule that tells an agent to verify the install is the same class of artifact
that already failed here -- the rules were right and nothing executed them. So
this is a hook, not a paragraph.

Hook Event: SessionStart
Returns: exit 0 always (advisory; never blocks a session)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 25


def resolve_checker(project_dir: Path) -> Path | None:
    """Find check_install.sh through the project's own link tree.

    The links are ground truth: whatever .claude/scripts or .claude/rules points
    at IS the pipeline this project loads. Resolving through them means the hook
    checks the checkout actually in use, not one named by an env var that may be
    stale.
    """
    for sub in ("scripts", "rules", "skills", "agents"):
        d = project_dir / ".claude" / sub
        if not d.is_dir():
            continue
        for entry in d.iterdir():
            if not entry.is_symlink():
                continue
            try:
                target = entry.resolve(strict=True)
            except OSError:
                continue
            for parent in target.parents:
                cand = parent / "scripts" / "check_install.sh"
                if cand.is_file() and (parent / "agents").is_dir():
                    return cand
    return None


def main() -> int:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "")).expanduser()
    if not project_dir.is_dir() or not (project_dir / ".claude").is_dir():
        return 0

    checker = resolve_checker(project_dir)
    if checker is None:
        return 0

    try:
        proc = subprocess.run(
            [str(checker), "--project-dir", str(project_dir)],
            capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0

    if proc.returncode == 0:
        return 0  # clean install: say nothing, cost nothing

    # Report the FAIL lines plus any indented detail that follows them.
    lines = proc.stdout.splitlines()
    keep: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith("FAIL "):
            keep.append(line)
            capturing = True
        elif capturing and (line.startswith("    ") or line.startswith("\t")):
            keep.append(line)
        else:
            capturing = False
    if not keep:
        return 0

    body = "\n".join(keep)
    message = (
        "## Pipeline install check FAILED\n\n"
        f"`check_install.sh` reports this project's link tree is not correctly "
        f"installed:\n\n```\n{body}\n```\n\n"
        "Treat this as a finding about the toolchain, not noise. A contaminated "
        "install means a shared rule, skill or agent may be shadowed by a local "
        "copy, so gates can pass while enforcing something other than the current "
        "standard. Resolve or explicitly note these before relying on any quality "
        "gate in this session.\n\n"
        f"Full detail: `{checker} --project-dir {project_dir}`"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open — never block a session on a hook bug
