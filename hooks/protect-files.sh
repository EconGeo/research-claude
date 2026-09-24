#!/bin/bash
# Wired by default via seeds/settings.json (Phase 4.1, 2026-09-24 — supersedes the
# 2026-09-08 opt-in ruling, design spec R-7: that default left every generated evidence
# file unprotected in all six repos, and `/review` already had to bolt on its own
# `git status --porcelain` check after "a project gate restamped two committed reports").
# Block accidental edits to protected files
# Extend PROTECTED_PATTERNS below for a project's own extra artifacts
# Hook Event: PreToolUse
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
FILE=""

# Extract file path based on tool type
if [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ]; then
  FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
fi

# No file path = not a file operation, allow
if [ -z "$FILE" ]; then
  exit 0
fi

# ============================================================
# Quarto-native defaults — the pipeline's own config and generated evidence.
# CUSTOMIZE: append patterns for a project's own extra artifacts.
# Uses basename matching — add full paths for more precision.
# ============================================================
PROTECTED_PATTERNS=(
  "settings.json"
  "pipeline_state.json"
  "*-critic_*.md"
  "civilize_*_report.md"
  "verify_claims_*.md"
  "verification_report.md"
  "strategy_memo.md"
  "desk_review.md"
  "referee_domain.md"
  "referee_methods.md"
)

BASENAME=$(basename "$FILE")
for PATTERN in "${PROTECTED_PATTERNS[@]}"; do
  # PATTERN must be unquoted here: quoting it inside [[ ]] turns off glob matching and
  # makes every wildcard pattern compare as a literal string, so it never matches anything.
  # This was true of every pattern shipped before 2026-09-24, including the original
  # "strategy-memo-*.md" — and went uncaught for as long as the hook was never wired or tested.
  if [[ "$BASENAME" == $PATTERN ]]; then
    echo "Protected file: $BASENAME. Edit manually or remove protection in .claude/hooks/protect-files.sh" >&2
    exit 2
  fi
done

exit 0
