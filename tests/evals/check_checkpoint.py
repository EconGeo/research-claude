#!/usr/bin/env python3
"""check_checkpoint.py — mechanism assertions for the /checkpoint eval.

  1. docs/SESSION_REPORT.md after the run starts with the seeded file's exact bytes and is
     longer (append-only, rules/logging.md).
  2. No SESSION_REPORT.md at the project root (CLAUDE.md moved it to docs/).
  3. No tool_use whose name contains "obsidian" and no Bash command mentioning obsidian
     (.claude/state/obsidian-config.md is absent: Obsidian is inactive).
  4. No Write/Edit on quality_reports/research_journal.md and no Bash redirect into it — no
     agent work happened this session.
  5. The seeded stale plan (quality_reports/plans/*.md) differs from its seed — the plan
     staleness sweep fixed it in place (rules/session-handoff.md R1). Audit: red today.

usage: check_checkpoint.py <transcript.jsonl> <project-dir> <seed-report.md> <seed-plan.md>
"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib

t, proj, seed_report, seed_plan = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
uses = evallib.tool_uses(t)
fails = []

rep = proj / "docs" / "SESSION_REPORT.md"
before = seed_report.read_bytes()
after = rep.read_bytes() if rep.exists() else b""
if not after.startswith(before): fails.append("docs/SESSION_REPORT.md no longer starts with its prior bytes (not append-only)")
elif len(after) == len(before): fails.append("docs/SESSION_REPORT.md was not appended to")
if (proj / "SESSION_REPORT.md").exists(): fails.append("a root SESSION_REPORT.md was written although CLAUDE.md moved it to docs/")
if any("obsidian" in n.lower() for n, _, _ in uses) or any("obsidian" in c.lower() for c in evallib.bash(uses) if not re.search(r"test -f|ls |\[ -f", c)):
    fails.append("an Obsidian call was made with no obsidian-config.md")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("research_journal.md"):
        fails.append("research_journal.md was written although no agent ran"); break
if any(re.search(r">>?\s*\S*research_journal\.md", c) for c in evallib.bash(uses)):
    fails.append("a Bash redirect wrote research_journal.md")
plan = proj / "quality_reports" / "plans" / seed_plan.name
if not plan.exists() or plan.read_bytes() == seed_plan.read_bytes():
    fails.append("plan staleness sweep did not fix the stale plan in place (audit §6: red today)")

evallib.finish("check_checkpoint", fails, f"tool_use: {len(uses)} · report {len(before)}→{len(after)} bytes")
