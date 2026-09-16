#!/usr/bin/env bash
# sync-zotpilot-skills.sh — refresh the vendored ZotPilot skills from the fork.
#
# research-claude vendors only the ~68 KB claude-skills/ from EconGeo/ZotPilot (see
# zotpilot-skills/VENDORED.md) rather than carrying the whole fork (224 MB connector) as a
# submodule. This script re-pulls just that directory — blobless + sparse, so no connector,
# no pdf.js — and overwrites zotpilot-skills/ in place.
#
# THE FORK IS THE ONLY SOURCE. Do not "upgrade" these skills from upstream
# (xunhe730/ZotPilot), however much newer its version number looks. The server we run IS the
# fork: it is pinned to a v0.5.0 base plus ~40 fork commits (Ollama provider, multi-library
# indexing, token-aware chunking), and it deliberately does not track upstream. Upstream's
# skills drive CLI flags the fork does not implement — `zotpilot setup --list-vendors` and
# `--verify` do not exist here (tested 2026-09-15), so upstream's ztp-setup hard-errors.
# A version-number gap between this directory and anything else is EXPECTED, not a bug.
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
if [[ -f "$DEST/VENDORED.md" ]]; then cp "$DEST/VENDORED.md" "$TMP/VENDORED.md"; fi
rm -rf "$DEST"
cp -r "$TMP/zp/claude-skills" "$DEST"
if [[ -f "$TMP/VENDORED.md" ]]; then cp "$TMP/VENDORED.md" "$DEST/VENDORED.md"; fi

echo "✓ Refreshed zotpilot-skills/ from EconGeo/ZotPilot@${SRC_COMMIT}"
echo "  Update the 'Vendored from commit' line in zotpilot-skills/VENDORED.md to ${SRC_COMMIT},"
echo "  review the diff, and commit."
