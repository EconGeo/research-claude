#!/usr/bin/env bash
# tests/evals/seed-papers.sh — functionality eval for /seed-papers against the ZotPilot mock. Run alone.
source "$(dirname "$0")/_lib.sh"
eval_setup
eval_mock
eval_run '/seed-papers statewide zoning preemption and housing supply' "$LOG" "mcp__zotpilot__*" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "Skill"
eval_finish check_seed_papers.py "$LOG" "$ERR"
