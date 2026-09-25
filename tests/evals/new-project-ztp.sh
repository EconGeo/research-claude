#!/usr/bin/env bash
# tests/evals/new-project-ztp.sh — functionality eval for /new-project-ztp against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '/new-project-ztp' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_new_project_ztp.py "$LOG" "$ERR"
