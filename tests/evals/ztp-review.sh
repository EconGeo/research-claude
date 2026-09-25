#!/usr/bin/env bash
# tests/evals/ztp-review.sh — functionality eval for /ztp-review against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '/ztp-review what do my papers say about zoning and housing supply elasticity?' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_ztp_review.py "$LOG" "$ERR"
