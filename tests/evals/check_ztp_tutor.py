#!/usr/bin/env python3
"""check_ztp_tutor.py — /ztp-tutor: get_paper_for_tutor is the first mock call (Step 1); with
persona null the skill asks once and stops (Step 2a), so no save_reading_persona, no annotate_pdf,
no specs JSON written. usage: check_ztp_tutor.py <transcript.jsonl> <mock-log>"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, calls = evallib.tool_uses(sys.argv[1]), evallib.mock_calls(sys.argv[2])
tools = [t for _, t, _, _ in calls]
fails = []
if not tools: fails.append("no call reached the mock")
elif tools[0] != "get_paper_for_tutor": fails.append(f"first mock call was {tools[0]}, not get_paper_for_tutor")
if "save_reading_persona" in tools: fails.append("save_reading_persona ran before the user gave preferences")
if "annotate_pdf" in tools: fails.append("annotate_pdf ran before the persona question was answered")
if any(n == "Write" and str(x.get("file_path", "")).endswith(".json") and "tutor" in str(x.get("file_path", "")) for n, x, _ in uses):
    fails.append("a specs JSON was written before the persona question was answered")
evallib.finish("check_ztp_tutor", fails, f"tool_use: {len(uses)} · mock calls: {len(calls)}")
