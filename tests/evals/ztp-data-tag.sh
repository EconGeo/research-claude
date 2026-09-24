#!/usr/bin/env bash
# tests/evals/ztp-data-tag.sh — functionality eval for /ztp-data-tag against the ZotPilot mock.
#
# Builds a throwaway project (the fixture, linked to this checkout), registers
# tests/mock_zotpilot.py as the `zotpilot` MCP server for that run only, invokes
# `/ztp-data-tag --yes` through `claude -p`, then runs check_ztp_data_tag.py over the
# transcript and the mock's stderr. Asserts mechanism, not outcome. Run alone — never in
# parallel with another eval (audit 2026-09-15 §3 P7 rule 4).
#
#   tests/evals/ztp-data-tag.sh            # EVAL_TIMEOUT (s, default 1800) bounds the run
set -u
RC="$(cd "$(dirname "$0")/../.." && pwd)"
E="$(mktemp -d)"; trap 'rm -rf "$E"' EXIT
cp -R "$RC/tests/fixture-project/." "$E/"
git -C "$E" init -q && git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm fixture
"$RC/apply.sh" --project-dir "$E" --link >/dev/null || { echo "apply.sh --link failed"; exit 1; }

MCP_CFG="$E/mock-mcp.json"
cat >"$MCP_CFG" <<JSON
{"mcpServers": {"zotpilot": {"type": "stdio", "command": "python3", "args": ["$RC/tests/mock_zotpilot.py"]}}}
JSON
LOG="$E/eval.stream.jsonl"; ERR="$E/mock.stderr.log"
command -v claude >/dev/null 2>&1 || { echo "claude not on PATH"; exit 1; }
# The mock's stderr is the server's stderr, which claude forwards to its own stderr; the
# transcript goes to stdout. Both are captured separately.
( cd "$E" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "${EVAL_TIMEOUT:-1800}" \
    claude -p "/ztp-data-tag --yes" --permission-mode acceptEdits \
    --mcp-config "$MCP_CFG" --strict-mcp-config \
    --allowedTools "mcp__zotpilot__*" "Agent" "Read" "Bash" \
    --output-format stream-json --verbose ) >"$LOG" 2>"$ERR"
rc=$?
echo "claude exit $rc · transcript $(wc -l <"$LOG" | tr -d ' ') lines · mock stderr $(grep -c '^WRITE' "$ERR") writes"
grep -qi 'Unknown command:' "$LOG" && { echo "claude did not recognise /ztp-data-tag"; exit 1; }
python3 "$RC/tests/evals/check_ztp_data_tag.py" "$LOG" "$ERR"
