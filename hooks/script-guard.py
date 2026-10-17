#!/usr/bin/env python3
"""script-guard.py — PreToolUse (Write|Edit|Bash): no new analysis scripts outside their homes.

Enforces .claude/rules/quarto-empirical.md ("No external R analysis scripts"): in a project that
declares `manuscript: <file>.qmd` in its CLAUDE.md, a NEW code file (R, Python, Julia,
R Markdown or notebook)
may be created only under

  explorations/     — model tests kept out of the manuscript (own .qmd or scripts, anything goes)
  scripts/acquire/  — thin acquisition scripts that write data/raw/
  .claude/ .pipeline/ — pipeline machinery

or outside the project entirely (the session scratchpad). Everything else is refused before the
tool runs. Existing files are not touched by this guard: editing or overwriting a legacy script
is allowed, so older projects keep working. Bash is checked best-effort for the common ways a
file gets created (`>`, `>>`, `tee`, `touch`, `cp`/`mv` targets).

Why a hook and not a rule: the rule lives in quarto-empirical.md, which is excluded from session
start, and the only other check was a coder-critic deduction that runs inside /analyze. Ad-hoc
exploration sessions bypassed both. Fails open on any internal error.
"""
# Hook Event: PreToolUse
import json, os, re, shlex, sys
from pathlib import Path

CODE_EXT = {".r", ".py", ".jl", ".rmd", ".ipynb"}  # <!-- residue:prohibition -->
ALLOWED_DIRS = ("explorations", "scripts/acquire", ".claude", ".pipeline")


def project_root():
    root = os.environ.get("CLAUDE_PROJECT_DIR", "")
    return Path(root).resolve() if root else None


def declares_manuscript(root: Path):
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return None
    hits = re.findall(r"^manuscript:\s*(\S+\.qmd)\s*$", claude_md.read_text(errors="ignore"), re.M)
    return hits[0] if len(hits) == 1 else None


def violation(target: Path, root: Path) -> bool:
    """True when creating `target` breaks the rule."""
    if target.suffix.lower() not in CODE_EXT or target.exists():
        return False
    try:
        rel = target.resolve().relative_to(root)
    except ValueError:
        return False  # outside the project: scratchpad, /tmp
    rel_posix = rel.as_posix()
    return not any(rel_posix == d or rel_posix.startswith(d + "/") for d in ALLOWED_DIRS)


def bash_targets(command: str, cwd: Path):
    """Paths a shell command would plausibly create. Best-effort, not a parser."""
    found = [m.group(1) for m in re.finditer(r"(?<![0-9&])>>?\s*([^\s;&|<>()]+)", command)]
    for segment in re.split(r"\|\||&&|[;|\n]", command):
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            tokens = segment.split()
        args = [t for t in tokens[1:] if not t.startswith("-")]
        if not tokens or not args:
            continue
        if tokens[0] in ("tee", "touch"):
            found += args
        elif tokens[0] in ("cp", "mv") and len(args) >= 2:
            found.append(args[-1])
    out = []
    for f in found:
        f = expand_vars(f.strip("'\""), shell_assignments(command))
        if f is None:
            continue  # a variable this hook cannot resolve: fail open
        p = Path(os.path.expanduser(f))
        out.append(p if p.is_absolute() else cwd / p)
    return out


ASSIGN = re.compile(r"(?:^|[;&|\n(]|\bexport)\s*([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|[^\s;&|)]*)")
VAR = re.compile(r"\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))")


def shell_assignments(command: str) -> dict:
    """`NAME=value` and `export NAME=value` in the command itself, in order: a scratchpad path is
    usually set and used in one call (`S=/tmp/...; cat > $S/x.R`)."""
    names = {}
    for m in ASSIGN.finditer(command):
        value = expand_vars(m.group(2).strip("'\""), names)
        if value is not None:
            names[m.group(1)] = value
    return names


def expand_vars(text: str, names: dict):
    """Substitute $NAME / ${NAME} from the command's assignments, then the environment.
    None when any variable stays unresolved."""
    unresolved = False

    def sub(m):
        nonlocal unresolved
        name = m.group(1) or m.group(2)
        value = names.get(name, os.environ.get(name))
        if value is None:
            unresolved = True
            return ""
        return value

    out = VAR.sub(sub, text)
    return None if unresolved else out


def deny(target: Path, root: Path, manuscript: str):
    try:
        shown = target.resolve().relative_to(root).as_posix()
    except ValueError:
        shown = str(target)
    reason = (
        f"script-guard: refused to create {shown}. Analysis code lives in a chunk of {manuscript}. "
        "Model tests that should stay out of the manuscript go under explorations/ (its own .qmd "
        "or scripts). Acquisition scripts go under scripts/acquire/. One-off throwaway code goes "
        "in the session scratchpad. Rule: .claude/rules/quarto-empirical.md."
    )
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
    root = project_root()
    if root is None:
        return 0
    manuscript = declares_manuscript(root)
    if manuscript is None:
        return 0  # not a pipeline paper project

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or root)

    if tool == "Write":
        targets = [Path(tool_input.get("file_path", ""))]
    elif tool == "Bash":
        targets = bash_targets(tool_input.get("command", ""), cwd)
    else:
        return 0  # Edit needs an existing file, which this guard allows

    for target in targets:
        if str(target) and violation(target, root):
            deny(target, root, manuscript)
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open — a hook bug must never block the session
