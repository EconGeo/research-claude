#!/usr/bin/env bash
# tests/evals/write.sh — functionality eval for /write conclusion. code=85 so the writer's requires
# pass; a filled style guide so the VOICE block does not halt the run. The mock is registered because
# write's frontmatter does not need it but the writer-critic's local-literature sweep may. Run alone.
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
seed_score code 85 coder-critic
cat >"$E/.claude/references/personal-style-guide.md" <<'MD'
# Personal Style Guide

## Source Corpus
**Extracted on:** 2026-09-25
**Papers analyzed:** 2 (fixture)

## Sentence-level patterns
- Declarative openings; the finding first, the mechanism second.
- Numbers in prose are inline `r` expressions, never typed.

## Paragraph moves
- Claim → evidence (a table or figure reference) → caveat.

## Self-citation
- None.
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed code score + style guide" >/dev/null
eval_run '/write conclusion --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent" "mcp__zotpilot__*"
python3 "$RC/scripts/prose_number_check.py" "$E/manuscript_fixture.qmd" >"$E/prose.log" 2>&1; PRC=$?
eval_finish check_write.py "$LOG" "$E" "$PRC"
