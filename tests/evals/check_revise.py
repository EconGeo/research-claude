#!/usr/bin/env python3
"""check_revise.py — /revise on a report with a FATAL comment: the report is read; the manuscript
is listed (grep for labels/headings), not read whole; the FATAL escalates before any coder/writer
dispatch; the manuscript is not edited; a tracker, if written, names every class.
usage: check_revise.py <transcript.jsonl> <project-dir>"""
import re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
if evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("referee_report_fixture.md")) is None:
    fails.append("the referee report was never Read")
listed = evallib.first(uses, lambda n, a: (n == "Grep" and "manuscript_fixture.qmd" in str(a.get("path", "")) + str(a.get("glob", "")))
                       or (n == "Bash" and "manuscript_fixture.qmd" in a.get("command", "") and re.search(r"grep|rg|awk|sed -n", a.get("command", ""))))
if listed is None: fails.append("the manuscript was never listed (no grep for its labels/headings)")
if evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("manuscript_fixture.qmd") and not a.get("offset") and not a.get("limit")) is not None:
    fails.append("the manuscript was Read in full — the skill lists it; the dispatched agent reads it")
for ag in ("coder", "writer"):
    if evallib.agent(uses, ag) is not None: fails.append(f"{ag} was dispatched although a FATAL comment escalates first")
for n, x, _ in uses:
    if n in ("Write", "Edit", "MultiEdit") and str(x.get("file_path", "")).endswith("manuscript_fixture.qmd"):
        fails.append(f"{n} modified the manuscript"); break
porc = subprocess.run(["git", "-C", str(proj), "status", "--porcelain"], capture_output=True, text=True).stdout
if re.search(r"^\s*M\s+manuscript_fixture\.qmd", porc, re.M): fails.append("manuscript_fixture.qmd is modified on disk")
tracker = proj / "quality_reports" / "referee_response_tracker.md"
if tracker.exists():
    txt = tracker.read_text()
    missing = [c for c in ("FATAL", "TASTE", "NEW ANALYSIS", "CLARIFICATION", "MINOR", "DISAGREE") if c not in txt]
    if missing: fails.append(f"tracker written without: {missing}")
evallib.finish("check_revise", fails, f"tool_use: {len(uses)} · tracker written: {tracker.exists()}")
