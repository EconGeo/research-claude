#!/usr/bin/env bash
# tests/evals/ztp-tutor.sh — functionality eval for /ztp-tutor against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '/ztp-tutor deep reading guide for "Mortgage denial and neighborhood change" — I want to reproduce the method' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_ztp_tutor.py "$LOG" "$ERR"
