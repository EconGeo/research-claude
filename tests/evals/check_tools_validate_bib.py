#!/usr/bin/env python3
"""check_tools_validate_bib.py — mechanism assertions for the /tools validate-bib eval.

The subcommand's mechanism is the shipped script (audit 2026-09-15 P5, closed 2026-09-24):

  1. A Bash tool_use runs `.claude/scripts/validate_bib.py` (any argv around it).
  2. No Bash tool_use re-implements the check inline: no `comm -`, no `/tmp/cited`,
     no `grep -oE '^@'` over the .bib — the retired pipeline must not come back by memory.
  3. The sources are untouched: no Write/Edit tool_use on a .qmd or .bib, and no Bash
     tool_use that redirects into one (`validate-bib` reports; it never deletes entries).
     Other writes are allowed — the first live run (2026-09-25) wrote SESSION_REPORT.md
     after the check because rules/logging.md asks for one, which is not a defect here.

usage: check_tools_validate_bib.py <transcript.jsonl> <unused>
The second argument keeps the runner/checker contract identical to the other two evals.
"""
import json, re, sys, pathlib

transcript = pathlib.Path(sys.argv[1])

uses = []
for line in transcript.read_text().splitlines():
    try:
        m = json.loads(line)
    except json.JSONDecodeError:
        continue
    msg = m.get("message") or {}
    if not isinstance(msg, dict):
        continue
    for b in msg.get("content") or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            uses.append((b.get("name") or "", b.get("input") or {}))

bash = [a.get("command", "") for n, a in uses if n == "Bash"]
fails = []

if not any("scripts/validate_bib.py" in c for c in bash):
    fails.append("no Bash call ran .claude/scripts/validate_bib.py")
INLINE = re.compile(r"comm -|/tmp/cited|grep -oE '\^@")
for c in bash:
    if INLINE.search(c):
        fails.append(f"an inline re-implementation ran instead of the script: {c[:80]!r}")
        break
SOURCE = re.compile(r"\.(qmd|bib)$")
for n, a in uses:
    if n in ("Write", "Edit", "MultiEdit") and SOURCE.search(str(a.get("file_path", ""))):
        fails.append(f"a {n} tool_use targeted a source file: {a.get('file_path')!r} — validate-bib must not modify the manuscript or the .bib")
        break
REDIRECT = re.compile(r">\s*\S*\.(qmd|bib)\b")
for c in bash:
    if REDIRECT.search(c):
        fails.append(f"a Bash call redirected into a .qmd or .bib: {c[:80]!r}")
        break

print(f"tool_use blocks: {len(uses)} · bash calls: {len(bash)}")
for f in fails:
    print(f"  FAIL {f}")
print("check_tools_validate_bib: " + ("PASS" if not fails else "FAIL"))
sys.exit(1 if fails else 0)
