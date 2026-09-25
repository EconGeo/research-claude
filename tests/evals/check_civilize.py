#!/usr/bin/env python3
"""check_civilize.py — /civilize <file>: one civilize-auditor dispatch for that file only; the
report is written under quality_reports/civilize_<stem>*_report.md; nothing else is edited
(the skill "does NOT rewrite"). SESSION_REPORT.md (root) is excluded from the source-file scan:
rules/logging.md has every skill run append it, and the first live run (2026-09-25) did — that
is pipeline logging, not civilize touching a source file (same carve-out as
check_tools_validate_bib.py). usage: check_civilize.py <transcript.jsonl> <project-dir>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
auditors = [x for n, x, _ in uses if n == "Agent" and x.get("subagent_type") == "civilize-auditor"]
if len(auditors) != 1: fails.append(f"civilize-auditor dispatched {len(auditors)} times (expected 1 for one file)")
else:
    p = str(auditors[0].get("prompt", ""))
    if "manuscript_fixture.qmd" not in p: fails.append("the auditor's prompt does not name manuscript_fixture.qmd")
    if "references.bib" in p or "talks/" in p: fails.append("the auditor's prompt names files outside the requested target")
if not list(proj.glob("quality_reports/civilize_manuscript_fixture*_report.md")): fails.append("no quality_reports/civilize_manuscript_fixture*_report.md was written")
for n, x, _ in uses:
    fp = str(x.get("file_path", ""))
    if n in ("Write", "Edit", "MultiEdit") and re.search(r"\.(qmd|bib|md)$", fp) and "quality_reports/" not in fp and pathlib.Path(fp).name != "SESSION_REPORT.md":
        fails.append(f"{n} touched a source file: {fp}"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+manuscript_fixture\.qmd", porc, re.M): fails.append("manuscript_fixture.qmd is modified")
evallib.finish("check_civilize", fails, f"tool_use: {len(uses)} · auditor dispatches: {len(auditors)}")
