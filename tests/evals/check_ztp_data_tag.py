#!/usr/bin/env python3
"""check_ztp_data_tag.py — mechanism assertions for the /ztp-data-tag eval (plan Task C2).

Inputs: the `claude -p ... --output-format stream-json` transcript, and the mock server's
stderr (its `WRITE <tool> <args> -> <result>` lines). Asserts mechanism, never outcome
(audit 2026-09-15 §3 P7 rule 3):

  1. data-tag-extractor is dispatched (Agent tool_use, subagent_type) before any manage_tags.
  2. every manage_tags write has action "add" and allow_new true — never "set".
  3. for every item_key, a create_note write precedes its manage_tags write.
  4. no manage_tags write for an item whose create_note returned created: false.

usage: check_ztp_data_tag.py <transcript.jsonl> <mock-stderr.log>
exit 0 = every assertion holds; 1 = at least one failed (each is printed).
"""
import json, re, sys, pathlib

transcript, mock_err = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])

# ── the parent transcript: tool_use blocks in order ──
uses = []
for line in transcript.read_text().splitlines():
    try:
        m = json.loads(line)
    except json.JSONDecodeError:
        continue
    msg = m.get("message") or {}
    for b in msg.get("content") or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            uses.append((b.get("name"), b.get("input") or {}))

# ── the mock's writes, in the order the server received them ──
WRITE = re.compile(r"^WRITE (\w+) (\{.*\}) -> (\{.*\})$")
writes = []
for line in mock_err.read_text().splitlines():
    w = WRITE.match(line.strip())
    if w:
        writes.append((w.group(1), json.loads(w.group(2)), json.loads(w.group(3))))

fails = []

# 1. extractor dispatched before any manage_tags
first_extractor = next((i for i, (n, a) in enumerate(uses)
                        if n == "Agent" and a.get("subagent_type") == "data-tag-extractor"), None)
first_tags = next((i for i, (n, a) in enumerate(uses) if n and n.endswith("manage_tags")), None)
if first_extractor is None:
    fails.append("data-tag-extractor was never dispatched")
elif first_tags is not None and first_tags < first_extractor:
    fails.append("manage_tags was called before data-tag-extractor was dispatched")

# 2. every manage_tags write is add + allow_new
for tool, args, _ in writes:
    if tool == "manage_tags":
        if args.get("action") != "add":
            fails.append(f"manage_tags action={args.get('action')!r} (must be 'add')")
        if not args.get("allow_new"):
            fails.append(f"manage_tags without allow_new=true for {args.get('item_key')}")

# 3 + 4. note before tags, and no tags for a skipped note
seen_note, skipped = {}, set()
for tool, args, result in writes:
    k = args.get("item_key")
    if tool == "create_note":
        seen_note[k] = True
        if result.get("created") is False:
            skipped.add(k)
    elif tool == "manage_tags":
        if k not in seen_note:
            fails.append(f"manage_tags for {k} with no prior create_note")
        if k in skipped:
            fails.append(f"manage_tags for {k} although its create_note was skipped (created: false)")

print(f"tool_use blocks: {len(uses)} · mock writes: {len(writes)} · "
      f"extractor dispatched: {first_extractor is not None}")
if not writes:
    print("  note: no writes reached the mock, so assertions 2–4 are vacuous — expected under "
          "--yes, which answers option gates only; Step 4's batch confirmation is a hard wait")
for f in fails:
    print(f"  FAIL {f}")
print("check_ztp_data_tag: " + ("PASS" if not fails else "FAIL"))
sys.exit(1 if fails else 0)
