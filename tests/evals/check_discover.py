#!/usr/bin/env python3
"""check_discover.py — /discover data: the domain profile is read before dispatch; explorer then
explorer-critic; record-score data after its report is written; no web tool in the main session;
data_sources.md, data_dictionary.md, access_instructions.md exist.
usage: check_discover.py <transcript.jsonl> <project-dir>"""
# The web-tool check must look only at the main session's own tool_use blocks
# (evallib.main_session_tool_uses), not the flattened `uses` list: a dispatched explorer's own
# WebSearch/WebFetch calls are folded into the same transcript, tagged with a
# `parent_tool_use_id` pointing at the Agent block, and the mechanism this asserts is that the
# *session* never called a web tool — the explorer is explicitly allowed to (agents/explorer.md).
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses, proj = evallib.tool_uses(sys.argv[1]), pathlib.Path(sys.argv[2])
fails = []
prof = evallib.first(uses, lambda n, a: n == "Read" and str(a.get("file_path", "")).endswith("domain-profile.md"))
ex, cr = evallib.agent(uses, "explorer"), evallib.agent(uses, "explorer-critic")
if ex is None: fails.append("explorer was never dispatched")
elif prof is None or prof > ex: fails.append("domain-profile.md was not Read before the explorer was dispatched")
if cr is None: fails.append("explorer-critic was never dispatched")
elif ex is not None and cr < ex: fails.append("explorer-critic ran before explorer")
rec = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"record-score\s+data\b", a.get("command", "")))
if rec is None: fails.append("record-score data never ran")
else:
    m = re.search(r"--report\s+(\S+)", uses[rec][1].get("command", ""))
    if m and evallib.first(uses[:rec], lambda n, a: n == "Write" and str(a.get("file_path", "")).endswith(m.group(1).split("/")[-1])) is None:
        fails.append("the explorer-critic report was not Written before its score was recorded")
main_uses = evallib.main_session_tool_uses(sys.argv[1])
if any(n in ("WebSearch", "WebFetch") for n, _, _ in main_uses): fails.append("the main session called a web tool — that is the explorer's job")
for f in ("data_sources.md", "data_dictionary.md", "access_instructions.md"):
    if not list(proj.glob(f"quality_reports/data-assessment/*/{f}")): fails.append(f"quality_reports/data-assessment/*/{f} was not written")
evallib.finish("check_discover", fails, f"tool_use: {len(uses)} · explorer: {ex is not None} · critic: {cr is not None}")
