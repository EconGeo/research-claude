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
# The live tier gets its OWN copy. Sharing $T with the mechanical tier is not a tidiness
# question: the mechanical checks write five coder/coder-critic lines and a code=85.0 score
# into $T, so every "did the live run do anything?" assertion passes on that residue without
# claude contributing a thing — and worse, the sequence deliberately ENDS on an unpaired
# `coder` (pairing-empty-sid), which critic-pairing.py then fires on at the live session's
# Stop, blocking a session that dispatched nothing. Observed both, 2026-09-10.
L=""; [[ "$LIVE" == true ]] && L="$(mktemp -d)"
# H: an isolated fake HOME for critic-pairing.py's checks below. Its sentinel file lives
# under Path.home()/.claude/sessions/ (R-114) — never the developer's real home directory.
[[ "$KEEP" == true ]] || trap 'rm -rf "$T" "$H" ${L:+"$L"}' EXIT
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
  echo "── live tier (clean copy: $L)"
  cp -R "$RC/tests/fixture-project/." "$L/"
  git -C "$L" init -q && git -C "$L" add -A && git -C "$L" -c user.name=fx -c user.email=fx@x commit -qm "fixture"
  run live-link "$RC/apply.sh" --project-dir "$L" --link
  run live-clean-log bash -c "[ ! -e '$L/quality_reports/agent_dispatch.jsonl' ]"

  # ── seed ONLY the stage a temp dir cannot run ──────────────────────────────────────────
  # literature is the sole creator with `kind: skill`: it delegates to /lit-position, which
  # calls /ztp-research + /ztp-review, i.e. ZotPilot against a real Zotero library. A
  # mktemp -d has none, so the stage correctly stops and asks rather than inventing a
  # bibliography (observed 2026-09-10 — the run exited cleanly after ~3.5 min having
  # dispatched nothing). Because `run` walks stages in REQUIRES order, `--until analyze`
  # necessarily starts there, so the live tier could never reach the stages worth testing.
  #
  # Seeding literature's OUTPUT leaves data → strategy → analyze to run for real. Every one
  # of those creators is `kind: agent`, so that path is what exercises this tier's whole
  # point: Agent dispatch → SubagentStop → dispatch-log.py, critic-pairing.py, post, scoring.
  #
  # This is INPUT state and is deliberately NOT the residue problem that produced the false
  # green: it seeds an artifact and a score, and NEVER the dispatch log — so
  # live-dispatch-log and live-critic-ran still measure only what the live run itself did.
  mkdir -p "$L/quality_reports/literature/fixture" "$L/quality_reports/reviews"
  cat > "$L/quality_reports/literature/fixture/positioning.md" <<'SEED'
# Positioning — seeded fixture input

Stands in for `/lit-position` output so the driver can reach the stages a temp dir can
actually run. Not a claim about any real literature.

**Gap.** No published estimate of the fixture's synthetic treatment effect.
**Contribution.** Estimates it on the fixture panel.
SEED
  echo '# lit-critic — seeded fixture input' > "$L/quality_reports/reviews/lit-critic_seed.md"
  python3 "$RC/scripts/pipeline.py" --root "$L" state init >/dev/null 2>&1
  python3 "$RC/scripts/pipeline.py" --root "$L" state record-score literature 88 \
    --critic lit-critic --report quality_reports/reviews/lit-critic_seed.md >/dev/null 2>&1
  # Prove the seed did its job BEFORE claude runs: strategy is now reachable.
  run live-seed-reaches-strategy python3 "$RC/scripts/pipeline.py" --root "$L" pre strategist

  LIVE_LOG="$L/live-pipeline.log"
  # Measured 2026-09-10: strategist took 12 min and strategist-critic another 12. A stage
  # that strikes (score < 80) re-dispatches both, so ONE stage can want ~50 min; --until
  # analyze wants ~90+. Default to the narrowest scope that still exercises the entire
  # chain — dispatch → SubagentStop → dispatch-log → critic → score → strike — and let a
  # fuller run be asked for explicitly.
  LIVE_UNTIL="${LIVE_UNTIL:-strategy}"
  LIVE_TIMEOUT="${LIVE_TIMEOUT:-3600}"
  if ! command -v claude >/dev/null 2>&1; then
    bad live-claude-present "claude not on PATH — the live tier cannot run"
  else
    ok live-claude-present
    # cd into the project FIRST: skills resolve from the cwd's .claude/, and research-claude
    # itself has no .claude/skills/, so running from the script's cwd makes every /skill an
    # "Unknown command". No timeout(1) on macOS; perl's alarm(2) survives exec, so the
    # watchdog outlives the replacement of perl by claude (SIGALRM ends it at exit 142).
    # stream-json, not the default text: `claude -p` text output is written only at the END,
    # so SIGALRM killed a 30-minute run and left a 0-line transcript — the run that finally
    # exercised the whole chain reported "claude produced no output at all". Streaming means
    # a killed run still leaves everything it had emitted.
    ( cd "$L" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "$LIVE_TIMEOUT" \
        claude -p "/pipeline run --until $LIVE_UNTIL --yes" --permission-mode acceptEdits \
        --output-format stream-json --verbose \
    ) >"$LIVE_LOG" 2>&1
    lrc=$?
    # `claude -p` EXITS 0 ON AN UNKNOWN COMMAND (tested 2026-09-10: a bogus /command prints
    # "Unknown command: ..." and returns 0), so the exit code alone cannot tell a real run
    # from one that never started. Read the transcript.
    live_bad=0
    if [[ $lrc -eq 142 ]]; then
      # FIRST: a timeout also produces an empty/short transcript, so testing emptiness ahead
      # of it reported every timeout as "claude produced no output at all" (observed).
      bad live-pipeline "TIMED OUT after ${LIVE_TIMEOUT}s — raise LIVE_TIMEOUT, or lower LIVE_UNTIL"; live_bad=1
    elif grep -qi 'Unknown command:' "$LIVE_LOG"; then
      bad live-pipeline "claude did not recognise the command"; live_bad=1
    elif [[ ! -s "$LIVE_LOG" ]]; then
      bad live-pipeline "empty transcript — claude produced no output at all"; live_bad=1
    elif [[ $lrc -ne 0 ]]; then
      bad live-pipeline "exit $lrc"; live_bad=1
    else
      ok live-pipeline
    fi
    echo "    transcript: $LIVE_LOG ($(wc -l <"$LIVE_LOG" 2>/dev/null | tr -d ' ') lines)"
    [[ $live_bad -eq 0 ]] || { echo "    ── last 25 lines"; tail -25 "$LIVE_LOG" 2>/dev/null | sed 's/^/    | /'; }
  fi

  # These now mean something: $L was empty of dispatch state until claude ran, so any entry
  # is necessarily the live run's.
  run live-dispatch-log test -s "$L/quality_reports/agent_dispatch.jsonl"
  run live-state-valid  python3 "$RC/scripts/pipeline.py" --root "$L" state validate
  echo "    ── what actually ran"
  if python3 "$RC/tests/live_summary.py" "$L" "$RC" | sed 's/^/    /'; then
    ok  live-critic-ran
  else
    bad live-critic-ran "no declared critic completed — see the summary above"
  fi
fi

[[ $fail -eq 0 ]] && echo "✓ run_fixture: PASS" || echo "✗ run_fixture: FAIL"
[[ "$KEEP" == true ]] && { echo "kept: $T"; [[ -n "$L" ]] && echo "kept (live): $L"; }
exit $fail
