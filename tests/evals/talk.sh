#!/usr/bin/env bash
# tests/evals/talk.sh — functionality eval for /talk create lightning. manuscript is scored 85 so
# the storyteller's requires pass; talks/ has no manuscript symlink yet. Run alone. EVAL_TIMEOUT 3600.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
seed_score() {
  mkdir -p "$E/quality_reports/reviews"
  echo "# $3 — seeded fixture input ($(date +%F))" >"$E/quality_reports/reviews/$3_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$E" state record-score "$1" "$2" --critic "$3" --report "quality_reports/reviews/$3_seed.md" >/dev/null
}
eval_setup
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
seed_score manuscript 85 writer-critic
# The fixture commits talks/manuscript_fixture.qmd as a relative symlink (e0c6c90, R-5); remove
# it here so Step 1 of /talk create must create it, exercising the "symlink before render" step.
rm -f "$E/talks/manuscript_fixture.qmd"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed manuscript score; remove pre-existing talks/ symlink" >/dev/null
eval_run '/talk create lightning --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent"
eval_finish check_talk.py "$LOG" "$E"
