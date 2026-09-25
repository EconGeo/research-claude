#!/usr/bin/env bash
# tests/evals/discover.sh — functionality eval for /discover data. The explorer has its own web tools
# (agents/explorer.md); the main session must not. The mock is registered for the critic's local
# literature sweep. Run alone. EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "state init" >/dev/null
eval_run '/discover data Need county-by-quarter teen employment and state minimum-wage changes, 2010–2020, US, staggered DiD. --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_discover.py "$LOG" "$E"
