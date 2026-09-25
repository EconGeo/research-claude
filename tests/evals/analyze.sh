#!/usr/bin/env bash
# tests/evals/analyze.sh — functionality eval for /analyze with no strategy memo. strategy=85 so
# `pre coder` passes. Four agent dispatches: the longest eval — EVAL_TIMEOUT 5400. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=5400}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score strategy 85 strategist-critic
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed strategy score" >/dev/null
eval_run '/analyze "add a robustness check clustering by year and an event-study figure" --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
( cd "$E" && quarto render manuscript_fixture.qmd >"$E/render.log" 2>&1 ); RRC=$?
python3 "$RC/scripts/prose_number_check.py" "$E/manuscript_fixture.qmd" >"$E/prose.log" 2>&1; PRC=$?
eval_finish check_analyze.py "$LOG" "$E" "$RRC" "$PRC"
