#!/usr/bin/env bash
# tests/evals/_lib.sh — sourced by every eval runner under tests/evals/. Not a script.
#
# eval_setup   builds $E: a copy of tests/fixture-project, git-initialised, linked to this
#              checkout (or $RC_LINK), with every .claude/references/ link replaced by a copy —
#              references/ are LINKED (apply.sh, D-26), so a skill filling domain-profile.md in
#              the project would otherwise edit the canonical file. Snapshots the checkout's
#              porcelain status so eval_finish can refuse a run that wrote through a link.
# eval_mock    registers tests/mock_zotpilot.py as the `zotpilot` MCP server for this run,
#              logging to $ERR (the client does not forward a server's stderr).
# eval_run     runs one `claude -p` to completion. NO TIMEOUT by default — a watchdog killed
#              two correct /strategize runs mid-critic on 2026-09-25; EVAL_TIMEOUT=<s> opts in
#              (perl alarm; 0 = none). stream-json so a killed run still leaves what it emitted.
# eval_finish  checkout-drift check, then the checker. Its exit code is the eval's.
#
# Env: EVAL_TIMEOUT (s, default 0 = no limit; opt-in only) · KEEP=1 keeps $E on PASS (a FAIL always keeps it).
# The drift check only watches paths apply.sh actually links into a project (agents/ skills/
# rules/ hooks/ templates/ references/ scripts/ zotpilot-skills/ ai-audit/); an untracked file
# elsewhere in the checkout (a scratch doc, a sibling eval task in progress) is not a write
# through a link and must not fail the run.
set -u
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
status=1
LINKED_DIRS_RE='^.. (agents|skills|rules|hooks|templates|references|scripts|zotpilot-skills|ai-audit)/'

eval_cleanup() {
  if [[ "${KEEP:-0}" == 1 || "${status:-1}" != 0 ]]; then echo "kept: $E"; else rm -rf "$E"; fi
}

eval_setup() {
  E="$(mktemp -d)"
  trap eval_cleanup EXIT
  cp -R "$RC/tests/fixture-project/." "$E/"
  git -C "$E" init -q && git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm fixture
  "${RC_LINK:-$RC}/apply.sh" --project-dir "$E" --link >/dev/null || { echo "apply.sh --link failed"; exit 1; }
  local f t
  for f in "$E"/.claude/references/*.md; do
    [[ -L "$f" ]] || continue
    t="$(cd "$(dirname "$f")" && cd "$(dirname "$(readlink "$f")")" && pwd -P)/$(basename "$(readlink "$f")")"
    rm "$f" && cp "$t" "$f"
  done
  git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "linked + seeded" >/dev/null
  RC_BEFORE="$(git -C "$RC" status --porcelain | grep -E "$LINKED_DIRS_RE" || true)"
  MCP_CFG="$E/mcp.json"; echo '{"mcpServers": {}}' >"$MCP_CFG"
  LOG="$E/eval.stream.jsonl"; ERR="$E/mock.calls.log"; : >"$ERR"
}

eval_mock() {
  cat >"$MCP_CFG" <<JSON
{"mcpServers": {"zotpilot": {"type": "stdio", "command": "python3", "args": ["$RC/tests/mock_zotpilot.py"], "env": {"MOCK_ZOTPILOT_LOG": "$ERR"}}}}
JSON
}

eval_run() {  # eval_run <prompt> <logfile> <allowed-tool>...
  local prompt="$1" log="$2"; shift 2
  command -v claude >/dev/null 2>&1 || { echo "claude not on PATH"; exit 1; }
  ( cd "$E" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "${EVAL_TIMEOUT:-0}" \
      claude -p "$prompt" --permission-mode acceptEdits \
      --mcp-config "$MCP_CFG" --strict-mcp-config --allowedTools "$@" \
      --output-format stream-json --verbose ) >"$log" 2>"$log.stderr"
  local rc=$?
  echo "claude exit $rc · $(basename "$log"): $(wc -l <"$log" | tr -d ' ') lines · mock log $(grep -c '^CALL' "$ERR") calls, $(grep -c '^WRITE' "$ERR") writes"
  [[ $rc -eq 142 ]] && echo "  (killed by the opt-in EVAL_TIMEOUT=${EVAL_TIMEOUT:-0}s watchdog)"
  grep -qi 'Unknown command:' "$log" && { echo "claude did not recognise the command"; exit 1; }
  return 0
}

eval_finish() {  # eval_finish <checker-basename> <arg>...
  local checker="$1"; shift
  local rc_after; rc_after="$(git -C "$RC" status --porcelain | grep -E "$LINKED_DIRS_RE" || true)"
  if [[ "$rc_after" != "$RC_BEFORE" ]]; then
    echo "FAIL the run modified the research-claude checkout through a link:"
    git -C "$RC" status --porcelain | sed 's/^/    /'; status=1; exit 1
  fi
  python3 "$RC/tests/evals/$checker" "$@"; status=$?
  exit $status
}
