#!/usr/bin/env python3
"""check_analyze.py — /analyze: Step 0 (`pipeline.py manuscript`, `pre coder`) before any dispatch;
data-engineer → coder-critic → coder → coder-critic as a subsequence; each record-score code after
a Write of its report; render and prose check exit 0 afterwards (runner-supplied codes).
usage: check_analyze.py <transcript.jsonl> <project-dir> <render-rc> <prose-rc>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, render_rc, prose_rc = evallib.tool_uses(sys.argv[1]), int(sys.argv[3]), int(sys.argv[4])
fails = []
first_agent = evallib.first(uses, lambda n, a: n == "Agent")
for pat, label in ((r"pipeline\.py\s+manuscript\b", "pipeline.py manuscript"), (r"pipeline\.py\s+pre\s+coder\b", "pipeline.py pre coder")):
    i = evallib.first(uses, lambda n, a, pat=pat: n == "Bash" and re.search(pat, a.get("command", "")))
    if i is None: fails.append(f"Step 0: `{label}` never ran")
    elif first_agent is not None and first_agent < i: fails.append(f"Step 0: `{label}` ran after an agent was dispatched")
seq = [a.get("subagent_type") for n, a, _ in uses if n == "Agent"]
want = ["data-engineer", "coder-critic", "coder", "coder-critic"]
it = iter(seq)
if not all(any(s == w for s in it) for w in want): fails.append(f"dispatch order {seq} does not contain data-engineer → coder-critic → coder → coder-critic")
for i, (n, a, _) in enumerate(uses):
    if n == "Bash" and re.search(r"record-score\s+code\b", a.get("command", "")):
        m = re.search(r"--report\s+(\S+)", a.get("command", ""))
        if m and evallib.first(uses[:i], lambda n2, a2, f=m.group(1).split("/")[-1]: n2 == "Write" and str(a2.get("file_path", "")).endswith(f)) is None:
            fails.append(f"a code score was recorded before its report {m.group(1)} was Written"); break
if render_rc != 0: fails.append(f"quarto render exited {render_rc} after the analysis")
if prose_rc != 0: fails.append(f"prose_number_check exited {prose_rc} after the analysis")
evallib.finish("check_analyze", fails, f"tool_use: {len(uses)} · dispatches: {seq} · render rc {render_rc} · prose rc {prose_rc}")
