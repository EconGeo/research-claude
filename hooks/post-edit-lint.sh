#!/bin/bash
# post-edit-lint.sh — PostToolUse hook that auto-lints R/Python/Julia files
# after Edit or Write operations. Advisory only (exit 0).
#
# Input arrives as JSON on STDIN, not in the environment. This hook previously
# read $CLAUDE_TOOL_ARG_FILE_PATH, which Claude Code does not set and never has —
# so the variable was always empty and the hook exited at line 1 without ever
# linting anything, in every project that wired it. The only env vars a hook
# receives are CLAUDE_PROJECT_DIR and friends; the tool's arguments are in the
# stdin payload under .tool_input. See https://code.claude.com/docs/en/hooks.

# Fail open if jq is missing — linting is advisory, matching notify.sh.
command -v jq >/dev/null 2>&1 || exit 0

FILE="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[[ -z "$FILE" ]] && exit 0

# Only run on R/Python/Julia scripts
case "$FILE" in
  *.R|*.py|*.jl) ;;
  *) exit 0 ;;
esac

# Skip files inside .claude/ (hooks, agents, etc.)
case "$FILE" in
  */.claude/*) exit 0 ;;
esac

# Run the linter on the single file
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/lint-scripts.sh" "$FILE" 2>/dev/null

exit 0
