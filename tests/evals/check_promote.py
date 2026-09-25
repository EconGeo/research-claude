#!/usr/bin/env python3
"""check_promote.py — /promote: Step 1 resolves the checkout with `readlink .claude/skills/write`
before anything else; Step 2 runs `git … status --porcelain` on it; a commit upstream is preceded
by check_fork.sh (Step 4) and never carries the file naming a journal; nothing is pushed.
usage: check_promote.py <transcript.jsonl> <clone-dir> <orig-head-sha>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
t, clone, orig = sys.argv[1], sys.argv[2], sys.argv[3].strip()
uses = evallib.tool_uses(t); cmds = evallib.bash(uses)
fails = []
if not cmds or "readlink" not in cmds[0] or ".claude/skills/write" not in cmds[0]:
    fails.append(f"the first Bash call was not `readlink .claude/skills/write`: {cmds[0][:80] if cmds else '(none)'!r}")
if not any(re.search(r"git\b[^\n]*status\s+--porcelain", c) for c in cmds): fails.append("`git status --porcelain` on the checkout never ran")
if any(re.search(r"\bgit\b[^\n]*\bpush\b", c) for c in cmds): fails.append("git push ran — /promote never pushes")
commit_i = next((i for i, c in enumerate(cmds) if re.search(r"\bgit\b[^\n]*\bcommit\b", c)), None)
if commit_i is not None and not any("check_fork.sh" in c for c in cmds[:commit_i]):
    fails.append("a git commit ran before check_fork.sh")
def git(*a): return subprocess.run(["git", "-C", clone, *a], capture_output=True, text=True).stdout
head = git("rev-parse", "HEAD").strip()
if head != orig:
    committed = git("diff", "--name-only", orig, head)
    if "skills/write/SKILL.md" in committed: fails.append("the journal-naming edit (skills/write/SKILL.md) was committed upstream")
if "skills/write/SKILL.md" not in git("status", "--porcelain"):
    fails.append("the journal-naming edit is no longer an uncommitted change in the clone (committed or reverted)")
evallib.finish("check_promote", fails, f"bash calls: {len(cmds)} · clone HEAD moved: {head != orig}")
