#!/usr/bin/env python3
"""check_submit.py — /submit final with no ai_use_log.md: the verifier runs and its replication
score is recorded; the disclosure check looks for ai_use_log.md; the run stops — no cover letter,
no submission checklist, no record-verify-claims. usage: check_submit.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
cmds = evallib.bash(uses)
fails = []
v = evallib.agent(uses, "verifier")
if v is None: fails.append("the verifier was never dispatched (Step 2: replication audit)")
rec = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"record-score\s+replication\b", a.get("command", "")))
if rec is None: fails.append("record-score replication never ran")
elif v is not None and rec < v: fails.append("record-score replication ran before the verifier was dispatched")
if evallib.first(uses, lambda n, a: "ai_use_log" in (str(a.get("file_path", "")) + str(a.get("command", "")) + str(a.get("pattern", "")) + str(a.get("path", "")))) is None:
    fails.append("ai_use_log.md was never checked (Step 2.5)")
if any("record-verify-claims" in c for c in cmds): fails.append("record-verify-claims ran although the disclosure check must stop the run")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit") and re.search(r"cover[_-]?letter|submission[_-]?checklist", fp, re.I):
        fails.append(f"submission material was written for a failing paper: {fp}"); break
if list(proj.glob("quality_reports/*cover*")) or list(proj.glob("quality_reports/*checklist*")) or list(proj.glob("*cover_letter*")):
    fails.append("a cover letter or checklist exists on disk")
evallib.finish("check_submit", fails, f"tool_use: {len(uses)} · verifier: {v is not None} · bash: {len(cmds)}")
