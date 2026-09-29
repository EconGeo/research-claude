#!/usr/bin/env python3
"""wrap_hooks.py — route a project's settings.json hook commands through .claude/run-hook.sh.

    wrap_hooks.py <settings.json>

Rewrites `[python3 ]"$CLAUDE_PROJECT_DIR"/.claude/hooks/<file>` to
`"$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh <file>` by text substitution, so the project's
formatting and every other key are untouched. Idempotent. Prints the number of commands
rewritten. settings.json is project-owned; this is the one surgical edit apply.sh makes to it,
because a hook command that points straight at an untracked link breaks every fresh worktree.
"""
import re, sys
from pathlib import Path

PAT = re.compile(r'(?:python3 )?\\"\$CLAUDE_PROJECT_DIR\\"/\.claude/hooks/([A-Za-z0-9_.-]+)')

def wrap(text: str) -> tuple[str, int]:
    return PAT.subn(lambda m: r'\"$CLAUDE_PROJECT_DIR\"/.claude/run-hook.sh ' + m.group(1), text)

if __name__ == "__main__":
    p = Path(sys.argv[1])
    new, n = wrap(p.read_text())
    if n: p.write_text(new)
    print(n)
