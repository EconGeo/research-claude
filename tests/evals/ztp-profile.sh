#!/usr/bin/env bash
# tests/evals/ztp-profile.sh — functionality eval for /ztp-profile against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
eval_mock
eval_run '/ztp-profile my library is a mess — merge duplicate tags' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_ztp_profile.py "$LOG" "$ERR"
