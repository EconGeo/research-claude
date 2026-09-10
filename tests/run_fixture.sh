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

T="$(mktemp -d)"; H="$(mktemp -d)"; export T H RC
# H: an isolated fake HOME for critic-pairing.py's checks below. Its sentinel file lives
# under Path.home()/.claude/sessions/ (R-114) — never the developer's real home directory.
[[ "$KEEP" == true ]] || trap 'rm -rf "$T" "$H"' EXIT
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
run templates-linked test -L "$T/.claude/templates/pipeline-state.json"
run scripts-linked   test -L "$T/.claude/scripts/pipeline.py"
run settings-seeded  bash -c "grep -q 'dispatch-log.py' '$T/.claude/settings.json' && grep -q 'critic-pairing.py' '$T/.claude/settings.json'"

# ── mechanical checks (extended by later tasks; keep the names stable) ──
run manuscript-declared   python3 "$RC/scripts/pipeline.py" --root "$T" manuscript
run state-init            python3 "$RC/scripts/pipeline.py" --root "$T" state init
run state-valid           python3 "$RC/scripts/pipeline.py" --root "$T" state validate
run registry-check        python3 "$RC/scripts/pipeline.py" --root "$RC" registry check
expect_fail pre-writer-red   python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
# The score must be recorded AFTER the creator's completion, or `critic-ran` rejects it as a
# score from an earlier round. Recording it first — as this sequence used to — made the harness
# itself an instance of the staleness bug it is supposed to catch.
run         log-coder        python3 "$RC/scripts/pipeline.py" --root "$T" log coder
expect_fail post-coder-red   python3 "$RC/scripts/pipeline.py" --root "$T" post coder
run         log-coder-critic bash -c "sleep 1; python3 '$RC/scripts/pipeline.py' --root '$T' log coder-critic"
expect_fail post-coder-unscored-red python3 "$RC/scripts/pipeline.py" --root "$T" post coder
run         record-code      python3 "$RC/scripts/pipeline.py" --root "$T" state record-score code 85 --critic coder-critic --report quality_reports/reviews/coder-critic_fixture.md
run         post-coder-green python3 "$RC/scripts/pipeline.py" --root "$T" post coder
run         pre-writer-green python3 "$RC/scripts/pipeline.py" --root "$T" pre writer
expect_fail conflicts-red    python3 "$RC/scripts/pipeline.py" --root "$T" conflicts coder writer
run         score            python3 "$RC/scripts/pipeline.py" --root "$T" score
run render                bash -c "cd '$T' && quarto render manuscript_fixture.qmd >/dev/null 2>&1"
run prose-check           python3 "$RC/scripts/prose_number_check.py" "$T/manuscript_fixture.qmd"

# ── critic-pairing.py Stop hook (Task 5.2): a creator that ran without its critic ──
# coder-critic already ran (paired) above; log coder again so its last completion is
# newer than coder-critic's, recreating the unpaired condition on purpose.
# A real Stop payload always carries a non-empty session_id — use one here so
# pairing-block/-once/-active-guard/-clean exercise the sentinel path they are meant to
# (Fix round 1, Finding 2: an all-empty sid made pairing-once pass for the wrong reason).
SID="fx-session-1"
echo '{"session_id":"'"$SID"'","cwd":"'"$T"'"}' > "$T/.pairing-payload.json"
echo '{"session_id":"'"$SID"'","cwd":"'"$T"'","stop_hook_active":true}' > "$T/.pairing-payload-active.json"
echo '{"session_id":"","cwd":"'"$T"'"}' > "$T/.pairing-payload-emptysid.json"
python3 "$RC/scripts/pipeline.py" --root "$T" log coder >/dev/null
run pairing-block         bash -c "CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload.json' | grep -q '\"decision\": \"block\"'"
run pairing-once          bash -c "CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload.json' | { ! grep -q '\"decision\"'; }"
run pairing-active-guard  bash -c "[ -z \"\$(CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload-active.json')\" ]"
sleep 1
python3 "$RC/scripts/pipeline.py" --root "$T" log coder-critic >/dev/null
run pairing-clean         bash -c "[ -z \"\$(CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload.json')\" ]"

# pairing-empty-sid: with no session id to key a sentinel on, the hook must block EVERY
# time and never suppress (Finding 2) — recreate the unpaired condition, then call twice.
python3 "$RC/scripts/pipeline.py" --root "$T" log coder >/dev/null
run pairing-empty-sid     bash -c "
  a=\$(CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload-emptysid.json')
  b=\$(CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/critic-pairing.py' < '$T/.pairing-payload-emptysid.json')
  echo \"\$a\" | grep -q '\"decision\": \"block\"' && echo \"\$b\" | grep -q '\"decision\": \"block\"'
"

# ── D-14: hooks emit on the documented JSON channel, not bare stderr (Task 7.1) ──
# $T has no quality_reports/session_logs/ yet — the fixture's own state dir is keyed
# on $T's path, so the "no log" advisory fires fresh here regardless of what earlier
# checks above did.
run hook-log-reminder     bash -c "echo '{\"cwd\":\"$T\"}' | CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/log-reminder.py' | grep -q '\"hookSpecificOutput\"'"

echo 'setwd("/tmp")' > "$T/hook-lint-fixture.R"
run hook-post-edit-lint   bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/hook-lint-fixture.R\"}}' | '$RC/hooks/post-edit-lint.sh' | grep -q '\"hookSpecificOutput\"'"

# ── lint-scripts.sh reads .qmd chunks via scripts/qmd_chunks.py (Task 7.3) ──
# Clean: an ordinary modelsummary(booktabs=TRUE) table plus a "reboot your R
# session" comment — real R-125-adjacent regression for the old bare `boot`
# pattern, which false-flagged the comment as stochastic code (see
# docs/audits/... task-7.3-report.md for the red). Must report CLEAN.
cat > "$T/lint-qmd-clean-fixture.qmd" <<'EOF'
---
title: booktabs test
---

```{r}
#| label: tbl-x
# reboot your R session if renv appears stale, then re-render
modelsummary(m, booktabs = TRUE)
```
EOF
run lint-qmd-clean bash -c "'$RC/hooks/lint-scripts.sh' '$T/lint-qmd-clean-fixture.qmd' | grep -q 'Status: CLEAN'"

# setwd() inside an R chunk must be caught at its correct SOURCE line (line 8
# here) — the whole point of scripts/qmd_chunks.py blanking non-chunk lines
# instead of dropping them.
cat > "$T/lint-qmd-setwd-fixture.qmd" <<'EOF'
---
title: setwd test
---

```{r}
#| label: fig-y
x <- 1
setwd("/Users/x")
```
EOF
run lint-qmd-setwd bash -c "out=\$('$RC/hooks/lint-scripts.sh' '$T/lint-qmd-setwd-fixture.qmd'); echo \"\$out\" | grep -q 'lint-qmd-setwd-fixture.qmd (2 issues)' && echo \"\$out\" | grep -q 'Line 8: setwd() '"

run hook-pre-compact      bash -c "echo '{\"trigger\":\"auto\"}' | CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/pre-compact.py' | grep -q '\"systemMessage\"'"

# ── session-guard.py: exemption protects its own state file, not the rest of .claude/ (Task 7.2) ──
mkdir -p "$T/.claude/state" "$T/.claude/rules"
echo '{"freeze":{"active":true,"allowed_paths":[]}}' > "$T/.claude/state/session-guards.json"
run session-guard-denies-state bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/.claude/state/session-guards.json\"}}' | CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/session-guard.py' | grep -q '\"permissionDecision\": \"deny\"'"
echo '# scratch' > "$T/.claude/rules/hook-fixture-scratch.md"
run session-guard-allows-rules bash -c "[ -z \"\$(echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/.claude/rules/hook-fixture-scratch.md\"}}' | CLAUDE_PROJECT_DIR='$T' HOME='$H' python3 '$RC/hooks/session-guard.py')\" ]"
rm -f "$T/.claude/state/session-guards.json"

if [[ "$LIVE" == true ]]; then
  echo "── live tier"
  run live-pipeline bash -c "cd '$T' && claude -p '/pipeline run --until analyze --yes' --permission-mode acceptEdits >/dev/null 2>&1"
  run live-dispatch-log test -s "$T/quality_reports/agent_dispatch.jsonl"
fi

[[ $fail -eq 0 ]] && echo "✓ run_fixture: PASS" || echo "✗ run_fixture: FAIL"
[[ "$KEEP" == true ]] && echo "kept: $T"
exit $fail
