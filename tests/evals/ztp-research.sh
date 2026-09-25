#!/usr/bin/env bash
# tests/evals/ztp-research.sh — functionality eval for /ztp-research against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '/ztp-research survey papers on staggered difference-in-differences since 2020' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_ztp_research.py "$LOG" "$ERR"
