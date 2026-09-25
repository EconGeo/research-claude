#!/usr/bin/env python3
"""check_write.py — /write <section>: `pipeline.py manuscript` before any dispatch; writer then
writer-critic; the manuscript score is recorded section-scoped with a --report that was written
first; the prose-number check passes afterwards (runner-supplied exit code).
usage: check_write.py <transcript.jsonl> <project-dir> <prose-check-exit-code>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj, prose_rc = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
fails = []
ms = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"pipeline\.py\s+manuscript\b", a.get("command", "")))
first_agent = evallib.first(uses, lambda n, a: n == "Agent")
if ms is None: fails.append("`pipeline.py manuscript` never ran")
elif first_agent is not None and first_agent < ms: fails.append("an agent was dispatched before the manuscript was resolved")
w, c = evallib.agent(uses, "writer"), evallib.agent(uses, "writer-critic")
if w is None: fails.append("writer was never dispatched")
if c is None: fails.append("writer-critic was never dispatched")
elif w is not None and c < w: fails.append("writer-critic ran before writer")
recs = [(i, a.get("command", "")) for i, (n, a, _) in enumerate(uses) if n == "Bash" and re.search(r"record-score\s+manuscript\b", a.get("command", ""))]
if not recs: fails.append("record-score manuscript never ran")
for i, cmd in recs:
    if not re.search(r"--scope\s+section:\S*conclusion", cmd, re.I): fails.append(f"record-score manuscript is not scoped to section:Conclusion: {cmd[:100]!r}")
    m = re.search(r"--report\s+(\S+)", cmd)
    if m and evallib.first(uses[:i], lambda n, a: n == "Write" and str(a.get("file_path", "")).endswith(m.group(1).split("/")[-1])) is None:
        fails.append(f"the report {m.group(1)} was not Written before its score was recorded")
if prose_rc != 0: fails.append(f"prose_number_check exited {prose_rc} after the draft")
evallib.finish("check_write", fails, f"tool_use: {len(uses)} · records: {len(recs)} · prose check rc: {prose_rc}")
