#!/bin/bash
# post-edit-lint.sh — PostToolUse hook that auto-lints R/Python/Julia files
# after Edit or Write operations. Advisory only (exit 0).
#
# Hook Event: PostToolUse
#
# Input arrives as JSON on STDIN, not in the environment. This hook previously
# read $CLAUDE_TOOL_ARG_FILE_PATH, which Claude Code does not set and never has —
# so the variable was always empty and the hook exited at line 1 without ever
# linting anything, in every project that wired it. The only env vars a hook
# receives are CLAUDE_PROJECT_DIR and friends; the tool's arguments are in the
# stdin payload under .tool_input. See https://code.claude.com/docs/en/hooks.
#
# Output contract: PostToolUse cannot block (the tool already ran). The
# linter's findings go out as JSON on stdout — `systemMessage` (user-visible)
# and `hookSpecificOutput.additionalContext` (Claude-visible) — instead of
# plain stdout, which would reach Claude but not the user.

# Fail open if jq is missing — linting is advisory, matching notify.sh.
command -v jq >/dev/null 2>&1 || exit 0

FILE="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[[ -z "$FILE" ]] && exit 0

# Only run on R/Python/Julia/Quarto scripts
case "$FILE" in
  *.R|*.py|*.jl|*.qmd) ;;
  *) exit 0 ;;
esac

# Skip files inside .claude/ (hooks, agents, etc.)
case "$FILE" in
  */.claude/*) exit 0 ;;
esac

# Run the linter on the single file and surface findings on the documented
# JSON channel — a clean run stays silent (exit 0, no output).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
out="$("$SCRIPT_DIR/lint-scripts.sh" "$FILE" 2>/dev/null)"
grep -q 'Status: CLEAN' <<<"$out" && exit 0
jq -n --arg m "$out" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m},systemMessage:"lint: issues found (see context)"}'

exit 0
