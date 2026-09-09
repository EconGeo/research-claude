#!/usr/bin/env bash
# sync-ai-audit.sh — refresh the vendored ai-audit agents/skills from upstream.
#
# research-claude vendors only agents/, skills/ and README.md from EconGeo/ai-audit (see
# ai-audit/VENDORED.md) rather than carrying it as a submodule — a submodule needs
# `git submodule update --init` and silently yields an EMPTY directory when a clone skips
# that step. This script re-pulls just those paths — blobless + sparse — and overwrites
# ai-audit/ in place. It deliberately does NOT touch ai-audit/'s absence of rules/: the
# submodule's rules/ai-disclosure.md had drifted from the canonical rules/ai-disclosure.md
# at repo root (see ai-audit/VENDORED.md), and that copy is retired for good.
#
# Usage:  ./scripts/sync-ai-audit.sh [git-ref]
#   git-ref defaults to the upstream repo's default branch.

set -euo pipefail

UPSTREAM_URL="https://github.com/EconGeo/ai-audit.git"
REF="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/ai-audit"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "→ Fetching agents/, skills/, README.md from $UPSTREAM_URL (sparse, blobless)..."
git clone --quiet --filter=blob:none --no-checkout --depth 1 \
  ${REF:+--branch "$REF"} "$UPSTREAM_URL" "$TMP/aa"
git -C "$TMP/aa" sparse-checkout set --no-cone agents skills README.md >/dev/null
git -C "$TMP/aa" checkout --quiet

if [[ ! -d "$TMP/aa/agents" || ! -d "$TMP/aa/skills" ]]; then
  echo "Error: agents/ or skills/ not found in the upstream checkout" >&2
  exit 1
fi

SRC_COMMIT="$(git -C "$TMP/aa" rev-parse --short HEAD)"

# Preserve our local VENDORED.md, refresh everything else. rules/ is never pulled in —
# see the header comment and ai-audit/VENDORED.md for why.
[[ -f "$DEST/VENDORED.md" ]] && cp "$DEST/VENDORED.md" "$TMP/VENDORED.md"
rm -rf "$DEST/agents" "$DEST/skills" "$DEST/README.md"
cp -r "$TMP/aa/agents" "$DEST/agents"
cp -r "$TMP/aa/skills" "$DEST/skills"
cp "$TMP/aa/README.md" "$DEST/README.md"
[[ -f "$TMP/VENDORED.md" ]] && cp "$TMP/VENDORED.md" "$DEST/VENDORED.md"

echo "✓ Refreshed ai-audit/ from EconGeo/ai-audit@${SRC_COMMIT}"
echo "  Update the 'Vendored from commit' line in ai-audit/VENDORED.md to ${SRC_COMMIT},"
echo "  re-check rules/ai-disclosure.md by hand for drift, review the diff, and commit."
