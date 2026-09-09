#!/usr/bin/env bash
# run_fixture.sh — the repeatable end-to-end check against tests/fixture-project.
#   tests/run_fixture.sh               # mechanical tier: no LLM, simulated dispatch log
#   tests/run_fixture.sh --live        # also runs `claude -p '/pipeline ...'` in the temp copy
#   tests/run_fixture.sh --keep        # leave the temp copy on disk and print its path
# Exit 0 = every check passed. Every check is named so a red can be cited.
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIVE=false; KEEP=false
for a in "$@"; do case "$a" in --live) LIVE=true;; --keep) KEEP=true;; esac; done

T="$(mktemp -d)"; export T RC
[[ "$KEEP" == true ]] || trap 'rm -rf "$T"' EXIT
cp -R "$RC/tests/fixture-project/." "$T/"
git -C "$T" init -q && git -C "$T" add -A && git -C "$T" -c user.name=fx -c user.email=fx@x commit -qm "fixture"
fail=0
ok()  { echo "PASS [$1]"; }
bad() { echo "FAIL [$1] ${2:-}"; fail=1; }
run() { # run <name> <command...>  — PASS iff command exits 0
  local name="$1"; shift
  if out="$("$@" 2>&1)"; then ok "$name"; else bad "$name" "$(printf '%s' "$out" | tail -3 | tr '\n' ' ')"; fi
}
expect_fail() { # expect_fail <name> <command...> — PASS iff command exits non-zero (a red test)
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then bad "$name" "expected non-zero exit"; else ok "$name"; fi
}

echo "══ fixture copy: $T"
run link "$RC/apply.sh" --project-dir "$T" --link

# ── mechanical checks (extended by later tasks; keep the names stable) ──
run manuscript-declared   python3 "$RC/scripts/pipeline.py" --root "$T" manuscript
run state-init            python3 "$RC/scripts/pipeline.py" --root "$T" state init
run state-valid           python3 "$RC/scripts/pipeline.py" --root "$T" state validate
run registry-check        python3 "$RC/scripts/pipeline.py" --root "$RC" registry check
expect_fail pre-writer-red   python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
run         record-code      python3 "$RC/scripts/pipeline.py" --root "$T" state record-score code 85 --critic coder-critic --report quality_reports/reviews/coder-critic_fixture.md
run         pre-writer-green python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
run         log-coder        python3 "$RC/scripts/pipeline.py" --root "$T" log coder
expect_fail post-coder-red   python3 "$RC/scripts/pipeline.py" --root "$T" post coder
run         log-coder-critic bash -c "sleep 1; python3 '$RC/scripts/pipeline.py' --root '$T' log coder-critic"
run         post-coder-green python3 "$RC/scripts/pipeline.py" --root "$T" post coder
expect_fail conflicts-red    python3 "$RC/scripts/pipeline.py" --root "$T" conflicts coder writer
run         score            python3 "$RC/scripts/pipeline.py" --root "$T" score
run render                bash -c "cd '$T' && quarto render manuscript_fixture.qmd >/dev/null 2>&1"
run prose-check           python3 "$RC/scripts/prose_number_check.py" "$T/manuscript_fixture.qmd"

if [[ "$LIVE" == true ]]; then
  echo "── live tier"
  run live-pipeline bash -c "cd '$T' && claude -p '/pipeline run --until analyze --yes' --permission-mode acceptEdits >/dev/null 2>&1"
  run live-dispatch-log test -s "$T/quality_reports/agent_dispatch.jsonl"
fi

[[ $fail -eq 0 ]] && echo "✓ run_fixture: PASS" || echo "✗ run_fixture: FAIL"
[[ "$KEEP" == true ]] && echo "kept: $T"
exit $fail
