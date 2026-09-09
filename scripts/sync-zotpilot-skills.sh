#!/usr/bin/env bash
# sync-zotpilot-skills.sh — refresh the vendored ZotPilot skills from the fork.
#
# research-claude vendors only the ~68 KB claude-skills/ from EconGeo/ZotPilot (see
# zotpilot-skills/VENDORED.md) rather than carrying the whole fork (224 MB connector) as a
# submodule. This script re-pulls just that directory — blobless + sparse, so no connector,
# no pdf.js — and overwrites zotpilot-skills/ in place.
#
# Usage:  ./scripts/sync-zotpilot-skills.sh [git-ref]
#   git-ref defaults to the fork's default branch.

set -euo pipefail

FORK_URL="https://github.com/EconGeo/ZotPilot.git"
REF="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/zotpilot-skills"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Fetching claude-skills/ from $FORK_URL (sparse, blobless — no connector)..."
git clone --quiet --filter=blob:none --no-checkout --depth 1 \
  ${REF:+--branch "$REF"} "$FORK_URL" "$TMP/zp"
git -C "$TMP/zp" sparse-checkout set --no-cone claude-skills >/dev/null
git -C "$TMP/zp" checkout --quiet

if [[ ! -d "$TMP/zp/claude-skills" ]]; then
  echo "Error: claude-skills/ not found in the fork checkout" >&2
  exit 1
fi

SRC_COMMIT="$(git -C "$TMP/zp" rev-parse --short HEAD)"

# Preserve our local VENDORED.md, refresh everything else.
[[ -f "$DEST/VENDORED.md" ]] && cp "$DEST/VENDORED.md" "$TMP/VENDORED.md"
rm -rf "$DEST"
cp -r "$TMP/zp/claude-skills" "$DEST"
[[ -f "$TMP/VENDORED.md" ]] && cp "$TMP/VENDORED.md" "$DEST/VENDORED.md"

echo "✓ Refreshed zotpilot-skills/ from EconGeo/ZotPilot@${SRC_COMMIT}"
echo "  Update the 'Vendored from commit' line in zotpilot-skills/VENDORED.md to ${SRC_COMMIT},"
echo "  review the diff, and commit."
