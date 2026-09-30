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
# Usage:  ./scripts/sync-zotpilot-skills.sh [--check] [git-ref]
#   git-ref defaults to the fork's default branch.
#   --check  compare only: exit 0 identical, 1 differs (nothing written), other = fetch failed.
#   ZOTPILOT_FORK_URL overrides the fork URL (tests only).

set -euo pipefail

FORK_URL="${ZOTPILOT_FORK_URL:-https://github.com/EconGeo/ZotPilot.git}"
CHECK=false
if [[ "${1:-}" == "--check" ]]; then CHECK=true; shift; fi
REF="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/zotpilot-skills"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Fetching claude-skills/ from $FORK_URL (sparse, blobless — no connector)..."
git clone --quiet --filter=blob:none --no-checkout --depth 1 \
  ${REF:+--branch "$REF"} "$FORK_URL" "$TMP/zp" 2>/dev/null || { echo "Error: could not fetch $FORK_URL" >&2; exit 3; }
git -C "$TMP/zp" sparse-checkout set --no-cone claude-skills >/dev/null
git -C "$TMP/zp" checkout --quiet

if [[ ! -d "$TMP/zp/claude-skills" ]]; then
  echo "Error: claude-skills/ not found in the fork checkout" >&2
  exit 3
fi

SRC_COMMIT="$(git -C "$TMP/zp" rev-parse --short HEAD)"
# Kept as a variable: written inline after a slash, this name reads as a /skill reference to
# check_fork.sh [skill-refs], which fails on it (tested 2026-09-29).
SYNC_SCRIPT="sync-zotpilot-skills"

if [[ "$CHECK" == true ]]; then
  if diff -rq --exclude=VENDORED.md "$TMP/zp/claude-skills" "$DEST" >/dev/null 2>&1; then
    echo "✓ zotpilot-skills/ matches EconGeo/ZotPilot@${SRC_COMMIT}"; exit 0
  fi
  echo "✗ zotpilot-skills/ differs from EconGeo/ZotPilot@${SRC_COMMIT} — run scripts/sync-zotpilot-skills.sh:"
  diff -rq --exclude=VENDORED.md "$TMP/zp/claude-skills" "$DEST" | sed 's/^/    /'
  exit 1
fi

# Preserve our local VENDORED.md, refresh everything else.
if [[ -f "$DEST/VENDORED.md" ]]; then cp "$DEST/VENDORED.md" "$TMP/VENDORED.md"; fi
rm -rf "$DEST"
cp -r "$TMP/zp/claude-skills" "$DEST"
if [[ -f "$TMP/VENDORED.md" ]]; then cp "$TMP/VENDORED.md" "$DEST/VENDORED.md"; fi

if [[ -f "$DEST/VENDORED.md" ]]; then
  perl -pi -e "s/^- Vendored from commit: .*/- Vendored from commit: \`${SRC_COMMIT}\` (synced $(date +%F) by scripts\/${SYNC_SCRIPT}.sh)/" "$DEST/VENDORED.md"
fi
echo "✓ Refreshed zotpilot-skills/ from EconGeo/ZotPilot@${SRC_COMMIT} — review the diff and commit."
