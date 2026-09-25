#!/usr/bin/env bash
# tests/evals/revise.sh — functionality eval for /revise on a six-comment synthetic report whose
# first comment is FATAL. Run alone. EVAL_TIMEOUT default 1800.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=1800}"
eval_setup
mkdir -p "$E/quality_reports"
cat >"$E/quality_reports/referee_report_fixture.md" <<'MD'
# Referee Report — Fixture manuscript

## Referee 1

1. The treatment indicator in `build-panel` is defined from the same outcome it predicts; if so, the headline coefficient in Table 1 is mechanical and the main claim does not survive. Please re-derive treatment from the adoption dates alone and re-estimate.
2. I would have framed this as a paper about neighbourhood sorting rather than adoption effects; the current framing is not the paper I would write.
3. Add an event-study figure with leads and lags and a placebo on never-treated units.

## Referee 2

4. Section 3 does not explain how the comparison group is constructed; a paragraph clarifying this would help.
5. Typo in the abstract: "fourty" → "forty"; Table 1 lacks a note on clustering.
6. The authors should drop the year fixed effects; they absorb the variation of interest. (I disagree with the authors' rationale.)
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "referee report" >/dev/null
eval_run '/revise quality_reports/referee_report_fixture.md --yes' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash" "Agent"
eval_finish check_revise.py "$LOG" "$E"
