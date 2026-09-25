#!/usr/bin/env bash
# tests/evals/review.sh — functionality eval for the comprehensive /review. code and strategy are
# scored so the manuscript route is open; three critics dispatch in one turn. Run alone.
# EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score code 85 coder-critic; seed_score strategy 85 strategist-critic
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed scores" >/dev/null
eval_run '/review manuscript_fixture.qmd --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_review.py "$LOG" "$E"
