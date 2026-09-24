#!/usr/bin/env bash
# tests/evals/lit-position.sh — functionality eval for /lit-position against the ZotPilot mock.
#
# Builds a throwaway project (the fixture, linked to this checkout), registers
# tests/mock_zotpilot.py as the `zotpilot` MCP server for that run only, invokes
# /lit-position --yes through `claude -p`, then runs check_lit_position.py over the transcript
# and the mock's stderr (local-first as a transcript property). Asserts mechanism, not outcome. Run alone — never in
# parallel with another eval (audit 2026-09-15 §3 P7 rule 4).
#
#   tests/evals/lit-position.sh            # EVAL_TIMEOUT (s, default 1800) bounds the run
set -u
RC="$(cd "$(dirname "$0")/../.." && pwd)"
E="$(mktemp -d)"
# Kept on a failed check (or KEEP=1) so the transcript can be read; removed on PASS.
cleanup() { if [[ "${KEEP:-0}" == 1 || "${status:-1}" != 0 ]]; then echo "kept: $E"; else rm -rf "$E"; fi; }
trap cleanup EXIT
cp -R "$RC/tests/fixture-project/." "$E/"
git -C "$E" init -q && git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm fixture
"$RC/apply.sh" --project-dir "$E" --link >/dev/null || { echo "apply.sh --link failed"; exit 1; }

MCP_CFG="$E/mock-mcp.json"; ERR="$E/mock.calls.log"
# The client does not forward a server's stderr, so the mock logs to a file named in its env.
cat >"$MCP_CFG" <<JSON
{"mcpServers": {"zotpilot": {"type": "stdio", "command": "python3", "args": ["$RC/tests/mock_zotpilot.py"], "env": {"MOCK_ZOTPILOT_LOG": "$ERR"}}}}
JSON
LOG="$E/eval.stream.jsonl"; : >"$ERR"
command -v claude >/dev/null 2>&1 || { echo "claude not on PATH"; exit 1; }
# The transcript goes to stdout; claude's own stderr is kept beside it.
( cd "$E" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "${EVAL_TIMEOUT:-1800}" \
    claude -p '/lit-position "staggered adoption and local housing prices" --yes' --permission-mode acceptEdits \
    --mcp-config "$MCP_CFG" --strict-mcp-config \
    --allowedTools "mcp__zotpilot__*" "Agent" "Read" "Write" "Bash" "Skill" \
    --output-format stream-json --verbose ) >"$LOG" 2>"$E/claude.stderr.log"
rc=$?
echo "claude exit $rc · transcript $(wc -l <"$LOG" | tr -d ' ') lines · mock log $(grep -c '^CALL' "$ERR") calls, $(grep -c '^WRITE' "$ERR") writes"
grep -qi 'Unknown command:' "$LOG" && { echo "claude did not recognise /lit-position"; exit 1; }
python3 "$RC/tests/evals/check_lit_position.py" "$LOG" "$ERR"; status=$?
exit $status
