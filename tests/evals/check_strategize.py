#!/usr/bin/env python3
"""check_strategize.py — /strategize: strategist then strategist-critic; the strategist is handed only
the chosen design's checklist (did or event-study for a staggered panel; never iv/rdd/structural/
descriptive); exactly one record-score strategy; a decision record with Alternatives exists.
usage: check_strategize.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
s, c = evallib.agent(uses, "strategist"), evallib.agent(uses, "strategist-critic")
if s is None: fails.append("strategist was never dispatched")
if c is None: fails.append("strategist-critic was never dispatched")
elif s is not None and c < s: fails.append("strategist-critic ran before strategist")
if s is not None:
    p = str(uses[s][1].get("prompt", ""))
    if not re.search(r"design-checklists/(did|event-study)\.md", p): fails.append("the strategist's prompt names neither did.md nor event-study.md")
    wrong = re.findall(r"design-checklists/(iv|rdd|structural|descriptive)\.md", p)
    if wrong: fails.append(f"the strategist's prompt names other designs' checklists: {sorted(set(wrong))}")
recs = [x for x in evallib.bash(uses) if re.search(r"record-score\s+strategy\b", x)]
if len(recs) != 1: fails.append(f"record-score strategy ran {len(recs)} times (expected exactly 1)")
dec = list(proj.glob("quality_reports/decisions/strategy_*.md"))
if not dec: fails.append("no quality_reports/decisions/strategy_*.md was written")
elif not any(re.search(r"^#+\s*.*Alternatives", d.read_text(), re.M | re.I) for d in dec): fails.append("the decision record has no Alternatives section")
evallib.finish("check_strategize", fails, f"tool_use: {len(uses)} · records: {len(recs)} · decision records: {len(dec)}")
