#!/usr/bin/env bash
# bootstrap-pipeline.sh — materialize this project's Claude pipeline.
#
#   ./bootstrap-pipeline.sh          coauthor / archival: pinned commit, project-local checkout
#   ./bootstrap-pipeline.sh --tip    maintainer: shared checkout on main, edits flow everywhere
#
# The two modes deliberately use different checkouts. Pinning the SHARED
# checkout would silently pin every other project on this machine to this
# paper's locked commit.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LOCK="$PROJECT_DIR/.claude/pipeline.lock"
[[ -f "$LOCK" ]] || { echo "missing $LOCK"; exit 1; }

repo="$(sed -n 's/^repo=//p'     "$LOCK")"
commit="$(sed -n 's/^commit=//p' "$LOCK")"
TIP=false; [[ "${1:-}" == "--tip" ]] && TIP=true

if [[ "$TIP" == true ]]; then
  RC="${RESEARCH_CLAUDE_HOME:-$HOME/Academic/research-claude}"
else
  RC="$PROJECT_DIR/.pipeline/research-claude"
fi

if [[ ! -d "$RC/.git" ]]; then
  echo "→ cloning $repo → $RC"
  git clone "$repo" "$RC"
fi
git -C "$RC" fetch --quiet origin

if [[ "$TIP" == true ]]; then
  if ! git -C "$RC" symbolic-ref -q HEAD >/dev/null; then
    echo "⚠️  $RC is in detached HEAD — returning it to main"
  fi
  git -C "$RC" checkout --quiet main
  git -C "$RC" pull --quiet --ff-only
  echo "→ pipeline: $RC @ main ($(git -C "$RC" rev-parse --short HEAD))"
else
  echo "→ pipeline: pinned $commit (project-local)"
  git -C "$RC" checkout --quiet "$commit"
fi

APPLY_ARGS=(--project-dir "$PROJECT_DIR" --link)
[[ "$TIP" == true ]] && APPLY_ARGS+=(--tip)
exec "$RC/apply.sh" "${APPLY_ARGS[@]}"
