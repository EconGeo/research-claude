#!/usr/bin/env python3
"""live_summary.py — say what the live pipeline run actually did, and assert a critic ran.

The live tier's only assertions used to be `exit 0` and a non-empty dispatch log, which is
compatible with the driver dispatching one creator and stopping. The claim the repair exists
to make is narrower and checkable: a creator does not advance without its critic. So:

  * PRINT every agent that completed, in order, with its registry role — evidence a human can
    read, on a red or a green.
  * EXIT 1 if no agent the registry declares as a critic ever completed.

Deliberately does NOT assert which stages ran. `/pipeline run --until analyze` had never been
executed when this was written, so pinning an expected stage list here would encode a guess as
a gate. Tighten it once the first run has shown the real shape.

usage: live_summary.py <project-root> <research-claude-root>
"""
import json, sys, pathlib

proj, rc_root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(rc_root / "scripts"))
import registry_lib as rl  # noqa: E402

reg = rl.load_registry(rc_root)
roles = {a: e.get("role", "?") for a, e in reg["agents"].items()}

log_path = proj / "quality_reports" / "agent_dispatch.jsonl"
entries = []
if log_path.exists():
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  ! unparseable dispatch-log line: {line[:80]}")

if not entries:
    print("  (dispatch log empty or absent — nothing was dispatched)")
else:
    print(f"  {len(entries)} completion(s), in order:")
    for e in entries:
        agent = e.get("agent", "?")
        role = roles.get(agent, "NOT IN REGISTRY")
        print(f"    {e.get('at','?'):32s}  {agent:22s} [{role}]  via {e.get('source','?')}")

state = proj / "quality_reports" / "pipeline_state.json"
if state.exists():
    st = json.loads(state.read_text())
    comps, secs = st.get("components") or {}, st.get("sections") or {}
    def fmt(d):
        # Built outside the f-string: nesting the same quote inside one is a SyntaxError
        # before 3.12, and this tree targets 3.9.
        return ", ".join("{}={}".format(k, v.get("score")) for k, v in d.items()) or "(none)"
    print("  components scored: " + fmt(comps))
    print("  sections scored  : " + fmt(secs))
    print(f"  strikes          : {st.get('strikes') or '(none)'}")
else:
    print("  (no pipeline_state.json)")

critics = sorted({e.get("agent") for e in entries if roles.get(e.get("agent")) == "critic"})
if critics:
    print(f"  critics that completed: {', '.join(critics)}")
    sys.exit(0)
print("  NO declared critic completed — a creator advanced unpaired")
sys.exit(1)
