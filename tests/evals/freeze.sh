#!/usr/bin/env bash
# tests/evals/freeze.sh — functionality eval for /freeze: three `claude -p` runs in one project
# (the guard persists on disk). careful is pre-seeded active so activation must read-modify-write.
# Run alone. No timeout (EVAL_TIMEOUT=<s> opts in).
source "$(dirname "$0")/_lib.sh"
eval_setup
mkdir -p "$E/.claude/state"
cat >"$E/.claude/state/session-guards.json" <<'JSON'
{"careful": {"active": true, "activated_at": "2026-09-25T00:00:00", "reason": "seeded"}}
JSON
eval_run '/freeze talks/' "$E/run-a.jsonl" "Read" "Bash"
cp "$E/.claude/state/session-guards.json" "$E/g_a.json"
eval_run 'Using the Edit tool only (never Bash), append the sentence "Fixture edit." to the end of the Conclusion section of manuscript_fixture.qmd. Then, again with the Edit tool only, append the same sentence to the end of talks/seminar_talk.qmd. Report what happened to each edit; if one is refused, do not try another way.' \
  "$E/run-b.jsonl" "Read" "Edit" "Write" "Grep" "Bash"
git -C "$E" status --porcelain >"$E/porcelain.txt"
eval_run '/freeze off' "$E/run-c.jsonl" "Read" "Bash"
cp "$E/.claude/state/session-guards.json" "$E/g_c.json"
eval_finish check_freeze.py "$E/run-a.jsonl" "$E/run-b.jsonl" "$E/run-c.jsonl" "$E/g_a.json" "$E/g_c.json" "$E/porcelain.txt"
