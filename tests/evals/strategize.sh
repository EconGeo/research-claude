#!/usr/bin/env bash
# tests/evals/strategize.sh — functionality eval for /strategize. Seeds positioning.md and
# data_sources.md (the strategist's any_of requires) as run_fixture.sh seeds literature. Run alone.
# EVAL_TIMEOUT 3600 (two 12-minute agents, plus a possible second round).
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=3600}"
eval_setup
eval_mock
python3 "$RC/scripts/pipeline.py" --root "$E" state init >/dev/null
mkdir -p "$E/quality_reports/literature/fixture" "$E/quality_reports/data-assessment/fixture"
cat >"$E/quality_reports/literature/fixture/positioning.md" <<'MD'
# Positioning — seeded fixture input

**Gap.** No county-level estimate of paid-sick-leave mandates on workplace injury rates.
**Contribution.** A staggered-adoption design on a county-year panel with never-treated states.
MD
cat >"$E/quality_reports/data-assessment/fixture/data_sources.md" <<'MD'
# Data sources — seeded fixture input

| Dataset | Access | Coverage | Grade |
|---|---|---|---|
| County-year injury rates (synthetic stand-in, `data/raw/panel.csv`) | public | 2012–2020, all counties | A |
| State mandate dates (hand-coded) | public | 2012–2020 | A |
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed discovery inputs" >/dev/null
eval_run '/strategize Did staggered state paid-sick-leave mandates (2012–2020) reduce county injury rates? County-year panel, never-treated states. --yes' \
  "$LOG" "Read" "Grep" "Glob" "Write" "Bash" "Agent" "mcp__zotpilot__*"
eval_finish check_strategize.py "$LOG" "$E"
