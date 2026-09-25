#!/usr/bin/env bash
# tests/evals/tools-validate-bib.sh — functionality eval for `/tools validate-bib`.
#
# Builds a throwaway project (the fixture, linked to this checkout), invokes
# `/tools validate-bib` through `claude -p`, then runs check_tools_validate_bib.py over the
# transcript. Asserts mechanism (the shipped script ran; nothing was re-implemented inline;
# nothing was written), not outcome. No MCP server is needed, so --strict-mcp-config with an
# empty config keeps the user's own servers out of the run. Run alone — never in parallel
# with another eval (audit 2026-09-15 §3 P7 rule 4).
#
#   tests/evals/tools-validate-bib.sh      # no timeout (EVAL_TIMEOUT=<s> opts in)
set -u
RC="$(cd "$(dirname "$0")/../.." && pwd)"
E="$(mktemp -d)"
# Kept on a failed check (or KEEP=1) so the transcript can be read; removed on PASS.
cleanup() { if [[ "${KEEP:-0}" == 1 || "${status:-1}" != 0 ]]; then echo "kept: $E"; else rm -rf "$E"; fi; }
trap cleanup EXIT
cp -R "$RC/tests/fixture-project/." "$E/"
git -C "$E" init -q && git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm fixture
"$RC/apply.sh" --project-dir "$E" --link >/dev/null || { echo "apply.sh --link failed"; exit 1; }

MCP_CFG="$E/empty-mcp.json"; echo '{"mcpServers": {}}' >"$MCP_CFG"
LOG="$E/eval.stream.jsonl"; ERR="$E/unused.log"; : >"$ERR"
command -v claude >/dev/null 2>&1 || { echo "claude not on PATH"; exit 1; }
( cd "$E" && exec perl -e 'alarm shift @ARGV; exec @ARGV' "${EVAL_TIMEOUT:-0}" \
    claude -p '/tools validate-bib' --permission-mode acceptEdits \
    --mcp-config "$MCP_CFG" --strict-mcp-config \
    --allowedTools "Read" "Bash" "Skill" "Grep" "Glob" \
    --output-format stream-json --verbose ) >"$LOG" 2>"$E/claude.stderr.log"
rc=$?
echo "claude exit $rc · transcript $(wc -l <"$LOG" | tr -d ' ') lines"
grep -qi 'Unknown command:' "$LOG" && { echo "claude did not recognise /tools"; exit 1; }
python3 "$RC/tests/evals/check_tools_validate_bib.py" "$LOG" "$ERR"; status=$?
exit $status
