#!/usr/bin/env bash
# tests/evals/checkpoint.sh — functionality eval for /checkpoint --auto. Seeds a docs/ report
# (moved there by CLAUDE.md), a stale plan (claims M1 is next; tbl-main is committed), no Obsidian
# config, and a committed history to log. Memory writes land under ~/.claude/projects/<$E encoded>/,
# a dir claude creates for every eval run anyway; it is removed on PASS. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
eval_setup
printf '\nSESSION_REPORT.md lives at docs/SESSION_REPORT.md, not the repo root.\n' >>"$E/CLAUDE.md"
mkdir -p "$E/docs" "$E/quality_reports/plans"
cat >"$E/docs/SESSION_REPORT.md" <<'MD'
# Session Report — Fixture project

## 2026-09-20 — Fixture panel and first estimate

Built `data/raw/panel.csv`, added `tbl-main` and `fig-trends`. Next: M1.
MD
cat >"$E/quality_reports/plans/2026-09-20-fixture-plan.md" <<'MD'
# Fixture plan

## Status

- M0 — synthetic panel: done
- M1 — add the `tbl-main` regression table: **next** (not started)
- M2 — event-study figure: pending
MD
# Seed copies live outside $E entirely (not just under a generic name inside it): the checker
# needs seed_plan's basename to match the live plan's filename (proj/quality_reports/plans/
# <seed_plan.name>), and a same-named duplicate sitting inside the project is fair game for the
# skill's own file discovery — it would "fix" that copy too, collapsing the before/after diff
# the checker relies on. Keeping the seed dir outside $E removes it from anything the skill reads.
SEED="$(mktemp -d)"
cp "$E/docs/SESSION_REPORT.md" "$SEED/seed_report.md"; cp "$E/quality_reports/plans/2026-09-20-fixture-plan.md" "$SEED/2026-09-20-fixture-plan.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "seed report and stale plan"
eval_run '/checkpoint --auto' "$LOG" "Read" "Grep" "Glob" "Write" "Edit" "Bash"
python3 "$RC/tests/evals/check_checkpoint.py" "$LOG" "$E" "$SEED/seed_report.md" "$SEED/2026-09-20-fixture-plan.md"; status=$?
rm -rf "$SEED"
enc="$(printf '%s' "$(cd "$E" && pwd -P)" | tr -c 'A-Za-z0-9\n' '-')"
[[ $status -eq 0 && -d "$HOME/.claude/projects/$enc" ]] && rm -rf "$HOME/.claude/projects/$enc"
[[ "$(git -C "$RC" status --porcelain)" == "$RC_BEFORE" ]] || { echo "FAIL checkout modified"; status=1; }
exit $status
