#!/usr/bin/env python3
"""check_lit_position.py — mechanism assertions for the /lit-position eval (plan Task C3).

Local-first (`rules/literature-search-order.md`) as a transcript property:

  1. lit-scout is dispatched (Agent tool_use, subagent_type) before /ztp-research is invoked
     (Skill tool_use, or any call to search_academic_databases / ingest_by_identifiers).
  2. The mock saw search_topic and advanced_search CALLs before any
     search_academic_databases CALL (the scout's sweep precedes external search).
  3. No WRITE reached the mock before the first external call — the sweep reads only.

usage: check_lit_position.py <transcript.jsonl> <mock-stderr.log>
"""
import json, re, sys, pathlib

transcript, mock_err = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])

uses = []
for line in transcript.read_text().splitlines():
    try:
        m = json.loads(line)
    except json.JSONDecodeError:
        continue
    msg = m.get("message") or {}
    if not isinstance(msg, dict):
        continue
    for b in msg.get("content") or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            uses.append((b.get("name") or "", b.get("input") or {}))

CALL = re.compile(r"^(CALL|WRITE) (\w+) ")
calls = [(w.group(1), w.group(2)) for w in
         (CALL.match(l.strip()) for l in mock_err.read_text().splitlines()) if w]

fails = []

def idx(pred):
    return next((i for i, u in enumerate(uses) if pred(*u)), None)

scout = idx(lambda n, a: n == "Agent" and a.get("subagent_type") == "lit-scout")
external = idx(lambda n, a: (n == "Skill" and "ztp-research" in json.dumps(a))
               or n.endswith("search_academic_databases") or n.endswith("ingest_by_identifiers"))
if scout is None:
    fails.append("lit-scout was never dispatched")
elif external is not None and external < scout:
    fails.append("external search (/ztp-research) began before lit-scout was dispatched")

first_ext_call = next((i for i, (k, t) in enumerate(calls) if t == "search_academic_databases"), None)
before = calls[:first_ext_call] if first_ext_call is not None else calls
for t in ("search_topic", "advanced_search"):
    if not any(tt == t for _, tt in before):
        fails.append(f"the mock never saw {t} before external search")
if any(k == "WRITE" for k, _ in before):
    fails.append("a write reached the mock during the local sweep")

print(f"tool_use blocks: {len(uses)} · mock calls: {len(calls)} · scout dispatched: {scout is not None}")
for f in fails:
    print(f"  FAIL {f}")
print("check_lit_position: " + ("PASS" if not fails else "FAIL"))
sys.exit(1 if fails else 0)
