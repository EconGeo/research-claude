#!/usr/bin/env bash
# tests/evals/submit.sh — functionality eval for /submit final on a paper with code/manuscript/
# strategy scored today and NO ai_use_log.md: the disclosure audit must stop the run. Run alone.
# EVAL_TIMEOUT default 3600 (the verifier, and possibly a fresh comprehensive review, dispatch).
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score code 100 coder-critic; seed_score manuscript 96 writer-critic; seed_score strategy 90 strategist-critic
rm -f "$E/ai_use_log.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed scores" >/dev/null
eval_run '/submit final --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "Skill"
eval_finish check_submit.py "$LOG" "$E"
