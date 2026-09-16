#!/usr/bin/env bash
# sync-zotpilot-skills.sh — refresh the vendored ZotPilot skills.
#
# TWO SOURCES, on purpose (see zotpilot-skills/VENDORED.md):
#
#   * ztp-profile / ztp-research / ztp-review / ztp-setup / ztp-tutor come from the
#     UPSTREAM release tag's packaged skills (src/zotpilot/skills/*.md). That is what
#     `zotpilot setup` deploys into ~/.claude/skills, so it is the version users actually
#     run, and it is ahead of the fork.
#   * seed-papers comes from the EconGeo FORK's claude-skills/ — it does not exist upstream.
#
# The fork's claude-skills/ copies of the ztp-* skills are a v0.5.0-era snapshot and are
# DELIBERATELY NOT USED here: syncing from them downgrades the skills (that is exactly what
# happened before 2026-09-15). If the fork ever starts carrying fork-specific edits to a
# ztp-* skill, this script must become a real three-way merge rather than an overlay.
#
# Both fetches are blobless + sparse, so no 224 MB connector toolchain is pulled.
#
# Usage:  ./scripts/sync-zotpilot-skills.sh [upstream-tag] [fork-ref]
#   upstream-tag defaults to UPSTREAM_TAG below; fork-ref defaults to the fork's default branch.

set -euo pipefail

UPSTREAM_URL="https://github.com/xunhe730/ZotPilot.git"
FORK_URL="https://github.com/EconGeo/ZotPilot.git"
UPSTREAM_TAG="${1:-v0.5.3}"
FORK_REF="${2:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/zotpilot-skills"

# Skills taken from upstream's packaged skills/, and the fork-only ones kept from the fork.
UPSTREAM_SKILLS=(ztp-profile ztp-research ztp-review ztp-setup ztp-tutor)
FORK_ONLY_SKILLS=(seed-papers)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

sparse_clone() {  # url ref dir sparse-path
  git clone --quiet --filter=blob:none --no-checkout --depth 1 \
    ${2:+--branch "$2"} "$1" "$3"
  git -C "$3" sparse-checkout set --no-cone "$4" >/dev/null
  git -C "$3" checkout --quiet
}

echo "→ Fetching upstream packaged skills from $UPSTREAM_URL @ $UPSTREAM_TAG (sparse, blobless)..."
sparse_clone "$UPSTREAM_URL" "$UPSTREAM_TAG" "$TMP/up" "src/zotpilot/skills"
UP_SRC="$TMP/up/src/zotpilot/skills"
[[ -d "$UP_SRC" ]] || { echo "Error: src/zotpilot/skills/ not found at $UPSTREAM_TAG" >&2; exit 1; }

echo "→ Fetching fork-only skills from $FORK_URL (sparse, blobless — no connector)..."
sparse_clone "$FORK_URL" "$FORK_REF" "$TMP/zp" "claude-skills"
FORK_SRC="$TMP/zp/claude-skills"
[[ -d "$FORK_SRC" ]] || { echo "Error: claude-skills/ not found in the fork checkout" >&2; exit 1; }

UP_COMMIT="$(git -C "$TMP/up" rev-parse --short HEAD)"
FORK_COMMIT="$(git -C "$TMP/zp" rev-parse --short HEAD)"

# Stage the new tree, then swap it in — VENDORED.md is ours and survives.
STAGE="$TMP/stage"
mkdir -p "$STAGE"
for s in "${UPSTREAM_SKILLS[@]}"; do
  [[ -f "$UP_SRC/$s.md" ]] || { echo "Error: upstream $UPSTREAM_TAG has no skills/$s.md" >&2; exit 1; }
  mkdir -p "$STAGE/$s"
  cp "$UP_SRC/$s.md" "$STAGE/$s/SKILL.md"
done
for s in "${FORK_ONLY_SKILLS[@]}"; do
  [[ -d "$FORK_SRC/$s" ]] || { echo "Error: fork has no claude-skills/$s" >&2; exit 1; }
  cp -r "$FORK_SRC/$s" "$STAGE/$s"
done

if [[ -f "$DEST/VENDORED.md" ]]; then cp "$DEST/VENDORED.md" "$STAGE/VENDORED.md"; fi
rm -rf "$DEST"
mv "$STAGE" "$DEST"

echo "✓ Refreshed zotpilot-skills/"
echo "    ztp-*        ← xunhe730/ZotPilot@${UPSTREAM_TAG} (${UP_COMMIT}), src/zotpilot/skills/"
echo "    seed-papers  ← EconGeo/ZotPilot@${FORK_COMMIT}, claude-skills/"
echo "  Update the provenance lines in zotpilot-skills/VENDORED.md, review the diff, and commit."
