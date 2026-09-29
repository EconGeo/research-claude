#!/usr/bin/env bash
# run-hook.sh — launch a pipeline hook, surviving a checkout that lacks the links.
#
#   "$CLAUDE_PROJECT_DIR"/.claude/run-hook.sh <hook-file> [args...]      (stdin is passed through)
#
# WHY THIS EXISTS. .claude/hooks/ is a directory of symlinks into research-claude and is
# gitignored, but .claude/settings.json is tracked. A git worktree (the desktop app makes
# one per session) therefore arrives with settings.json naming hooks that do not exist,
# and a PreToolUse hook that cannot start fails EVERY tool call — the session cannot even
# run the command that would repair it. This file is tracked and real, so it is present in
# every checkout; it resolves the hook in this order and never fails a session over a
# missing one:
#   1. $CLAUDE_PROJECT_DIR/.claude/hooks/<hook>            the normal, linked case
#   2. <main checkout of this repo>/.claude/hooks/<hook>   a worktree; hooks still read
#                                                          $CLAUDE_PROJECT_DIR (the worktree)
#   3. neither: warn on stderr, exit 0 (fail open), and say how to repair.
# Repair a worktree by running research-claude's apply.sh with --project-dir <worktree> --link.
#
# Installed and refreshed by apply.sh. Do not edit per project.
h="${1:?usage: run-hook.sh <hook-file> [args...]}"; shift
d="${CLAUDE_PROJECT_DIR:-$PWD}"
f="$d/.claude/hooks/$h"
if [[ ! -e "$f" ]]; then
  common="$(git -C "$d" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  [[ -n "$common" ]] && f="${common%/.git}/.claude/hooks/$h"
fi
if [[ ! -e "$f" ]]; then
  echo "run-hook: $h not found under $d/.claude/hooks (unlinked worktree?) — skipped. Repair: run research-claude's apply.sh --project-dir $d --link" >&2
  exit 0
fi
case "$h" in
  *.py) exec python3 "$f" "$@" ;;
  *)    exec "$f" "$@" ;;
esac
