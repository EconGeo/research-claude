#!/usr/bin/env python3
"""check_strategize.py — /strategize: strategist then strategist-critic; the strategist is handed only
the chosen design's checklist (did or event-study for a staggered panel; never iv/rdd/structural/
descriptive); record-score strategy once at >= 80, or followed by a revision round and a second score below 80 (Step 5);
a decision record with Alternatives exists.
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
    # Every strategist dispatch, not just the first: Step 1's Pre-Strategy Report may be its own
    # dispatch, before the Step 2 gate has picked a design, so it names no checklist.
    ps = [str(a.get("prompt", "")) for n, a, _ in uses if n == "Agent" and a.get("subagent_type") == "strategist"]
    if not any(re.search(r"design-checklists/(did|event-study)\.md", p) for p in ps): fails.append("no strategist prompt names did.md or event-study.md")
    wrong = sorted({w for p in ps for w in re.findall(r"design-checklists/(iv|rdd|structural|descriptive)\.md", p)})
    if wrong: fails.append(f"a strategist prompt names other designs' checklists: {wrong}")
recs = [(i, a.get("command", "")) for i, (n, a, _) in enumerate(uses) if n == "Bash" and re.search(r"record-score\s+strategy\b", a.get("command", ""))]
if not recs: fails.append("record-score strategy never ran")
else:
    # Step 5: below 80 the strategist revises and the critic re-scores (a second record); at or above 80 the
    # first score is the only one.
    m = re.search(r"record-score\s+strategy\s+(\d+)", recs[0][1]); first_score = int(m.group(1)) if m else None
    revised = evallib.first(uses[recs[0][0]:], lambda n, a: n == "Agent" and a.get("subagent_type") == "strategist")
    if first_score is not None and first_score < 80 and (len(recs) < 2 or revised is None):
        fails.append(f"first strategy score {first_score} < 80 but no revision round followed (Step 5: strategist revises, critic re-scores)")
    if (first_score is None or first_score >= 80) and len(recs) != 1:
        fails.append(f"record-score strategy ran {len(recs)} times after a passing first score (expected exactly 1)")
dec = list(proj.glob("quality_reports/decisions/strategy_*.md"))
if not dec: fails.append("no quality_reports/decisions/strategy_*.md was written")
elif not any(re.search(r"^#+\s*.*Alternatives", d.read_text(), re.M | re.I) for d in dec): fails.append("the decision record has no Alternatives section")
evallib.finish("check_strategize", fails, f"tool_use: {len(uses)} · records: {len(recs)} · decision records: {len(dec)}")
