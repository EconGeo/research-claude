#!/usr/bin/env python3
"""check_review.py — /review <manuscript>: strategist-critic, writer-critic and verifier dispatched;
porcelain before and after the verifier; each component's report Written before its record-score;
critic-inputs runs before writer-critic and its log path is in the dispatch prompt;
disposition-pool.md never read in the main context. usage: check_review.py <transcript.jsonl> <project-dir>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evallib
uses = evallib.tool_uses(sys.argv[1])
fails = []
d = {a: evallib.agent(uses, a) for a in ("strategist-critic", "writer-critic", "verifier")}
for a, i in d.items():
    if i is None: fails.append(f"{a} was never dispatched")
c = d["writer-critic"]
ci = evallib.first(uses, lambda n, a: n == "Bash" and re.search(r"pipeline\.py\s+critic-inputs\b", a.get("command", "")))
if ci is None: fails.append("`pipeline.py critic-inputs` never ran")
elif c is not None and ci > c: fails.append("critic-inputs ran after writer-critic was dispatched")
if c is not None and "critic_inputs/" not in str(uses[c][1].get("prompt", "")): fails.append("the writer-critic dispatch does not name a critic_inputs/ log")
v = d["verifier"]
if v is not None:
    porc = [i for i, (n, a, _) in enumerate(uses) if n == "Bash" and re.search(r"git\s+status\s+--porcelain", a.get("command", ""))]
    if not any(i < v for i in porc): fails.append("no `git status --porcelain` before the verifier's dispatch")
    if not any(i > v for i in porc): fails.append("no `git status --porcelain` after the verifier returned")
for comp in ("strategy", "manuscript", "replication"):
    rec = evallib.first(uses, lambda n, a, comp=comp: n == "Bash" and re.search(rf"record-score\s+{comp}\b", a.get("command", "")))
    if rec is None: fails.append(f"record-score {comp} never ran"); continue
    m = re.search(r"--report\s+(\S+)", uses[rec][1].get("command", ""))
    if m and evallib.first(uses[:rec], lambda n, a, f=m.group(1).split("/")[-1]: n == "Write" and str(a.get("file_path", "")).endswith(f)) is None:
        fails.append(f"the {comp} report was not Written before its score was recorded")
if evallib.first(evallib.main_session_tool_uses(sys.argv[1]), lambda n, a: n == "Read" and "disposition-pool.md" in str(a.get("file_path", ""))) is not None:
    fails.append("disposition-pool.md was read in the main context (it is the editor's, in --peer)")
evallib.finish("check_review", fails, f"tool_use: {len(uses)} · dispatched: {[a for a, i in d.items() if i is not None]}")
