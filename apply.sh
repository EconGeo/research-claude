#!/usr/bin/env bash
#
# apply.sh — install the research-claude pipeline into a paper project.
#
#   ./apply.sh --project-dir /path/to/project --link           link the pipeline
#   ./apply.sh --project-dir /path/to/project --link --tip      (bootstrap passes this)
#   ./apply.sh --project-dir /path/to/project --link --with-digest
#   ./apply.sh --list
#
# HOW THIS WORKS (D8)
#
# The pipeline is LINKED, not copied. `.claude/{skills,agents,rules,hooks}` become
# one relative symlink per item into this checkout. research-claude is the sole
# edit surface: editing a linked skill from any paper edits the canonical copy, and
# `git pull` here updates every project at once. There is no re-import step because
# there is no copy to re-import.
#
# A real (non-symlink) file at a link destination is a deliberate project override
# (D9) and is never touched. Links whose target has been deleted upstream are pruned.
#
# Scaffolding SEEDS are still copied, because they are project-owned and meant to be
# edited: references/ templates, state/ examples, data/raw/data_manifest.md, .gitignore.
#
# See rules/shared-pipeline.md for what a symlinked .claude/ means in practice.

set -euo pipefail

# pwd -P (physical) on both sides, deliberately: relpath below is purely lexical,
# but the kernel resolves the resulting symlink physically. On macOS /tmp is a
# symlink to /private/tmp, so a logical pwd here produces links that are off by a
# directory level and silently dangle.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR=""
UPDATE_MODE=false
WITH_DIGEST=false
LIST_MODE=false
LINK_MODE=true      # link is the only install mode; --link is accepted for explicitness
TIP_MODE=false
LINK_REFERENCES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)     PROJECT_DIR="$2"; shift 2 ;;
    --link)            LINK_MODE=true; shift ;;
    --tip)             TIP_MODE=true; shift ;;
    --update)          UPDATE_MODE=true; shift ;;
    --with-digest)     WITH_DIGEST=true; shift ;;
    --link-references) LINK_REFERENCES="$2"; shift 2 ;;
    --list)            LIST_MODE=true; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ "$LIST_MODE" == true ]]; then
  cat <<EOF
apply.sh links the pipeline into a project (one symlink per item):

  .claude/agents/   -> $SCRIPT_DIR/agents/          ($(ls "$SCRIPT_DIR/agents" 2>/dev/null | wc -l | tr -d ' ') agents)
  .claude/skills/   -> $SCRIPT_DIR/skills/          ($(ls "$SCRIPT_DIR/skills" 2>/dev/null | wc -l | tr -d ' ') skills)
  .claude/rules/    -> $SCRIPT_DIR/rules/           ($(ls "$SCRIPT_DIR/rules" 2>/dev/null | wc -l | tr -d ' ') rules)
  .claude/hooks/    -> $SCRIPT_DIR/hooks/           (linked, NOT auto-wired — see hooks/README.md)
  .claude/scripts/prose_number_check.py                 (INV-11 enforcer)

  plus, from live submodules and vendored trees:
  .claude/skills/, .claude/agents/, .claude/rules/  <- submodules/ai-audit
  .claude/skills/ztp-*                              <- zotpilot-skills/ (vendored)

Copied as project-owned SEEDS (never overwritten if present):
  .claude/references/*.md    voice / domain / journal / coding-standard templates
  .claude/state/*.example    opt-in integration config examples
  data/raw/data_manifest.md  raw-data provenance manifest seed
  .gitignore                 keeps *.qmd + *.bib; ignores render artifacts and the linked dirs

Written every run:
  .claude/pipeline.lock      repo URL + SHA — replication provenance and coauthor bootstrap

Directory skeleton:
  explorations/              one-off models not yet wired into the manuscript
                             (quality_reports/ and manuscript_<project>.qmd are created
                              later by the phase skills)

Flags:
  --link                     link the pipeline (default; accepted for explicitness)
  --tip                      recorded in the lock; the caller chose the shared checkout
  --update                   git submodule update --remote before installing
  --with-digest              also install the journal-digest module
  --link-references <dir>    symlink .claude/references/*.md to a shared voice-profile dir
EOF
  exit 0
fi

[[ -n "$PROJECT_DIR" ]] || { echo "Error: --project-dir is required"; exit 1; }
[[ -d "$PROJECT_DIR" ]] || { echo "Error: project directory not found: $PROJECT_DIR"; exit 1; }
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd -P)"

echo "→ Installing research-claude into: $PROJECT_DIR"
echo ""

if [[ "$UPDATE_MODE" == true ]]; then
  echo "→ Updating submodules..."
  git -C "$SCRIPT_DIR" submodule update --remote
fi

mkdir -p "$PROJECT_DIR/.claude"/{agents,skills,rules,hooks} "$PROJECT_DIR/explorations"

# ── relative path helper (macOS has no realpath --relative-to) ────────────────
relpath() { python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"; }

# ── link_items <src-dir> <dest-dir> [dirs-only] ──────────────────────────────
# One symlink per item. A real (non-symlink) entry at the destination is a
# deliberate project override (D9) and is left untouched.
link_items() {
  local src="$1" dest="$2" dirs_only="${3:-false}" name target item
  [[ -d "$src" ]] || return 0
  mkdir -p "$dest"
  for item in "$src"/*; do
    [[ -e "$item" ]] || continue
    [[ "$dirs_only" == true && ! -d "$item" ]] && continue
    name="$(basename "$item")"
    target="$dest/$name"
    if [[ -e "$target" && ! -L "$target" ]]; then
      echo "    ⤷ $name is a real file here — project override, left alone"
      continue
    fi
    ln -sfn "$(relpath "$item" "$dest")" "$target"
  done
}

# ── prune_dead_links <dest-dir> ──────────────────────────────────────────────
# A link whose target no longer exists means the item was deleted upstream.
prune_dead_links() {
  local dest="$1" dead
  [[ -d "$dest" ]] || return 0
  while IFS= read -r -d '' dead; do
    echo "    ⤷ removing stale link $(basename "$dead")"
    rm "$dead"
  done < <(find "$dest" -maxdepth 1 -type l ! -exec test -e {} \; -print0 2>/dev/null)
}

# ── copy_seed <src-file> <dest-file> ─────────────────────────────────────────
# Project-owned scaffolding. Never overwrites.
copy_seed() {
  # -L as well as -e: a SYMLINK at the destination is deliberate (that is what
  # --link-references creates) and must be left alone even when it dangles.
  # Without the -L test, cp follows the dangling link and aborts the whole run.
  if [[ -e "$2" || -L "$2" ]]; then echo "    ⤷ $(basename "$2") already exists — left untouched"
  else mkdir -p "$(dirname "$2")"; cp "$1" "$2"; fi
}

if [[ "$LINK_MODE" == true ]]; then
  echo "→ Linking pipeline from $SCRIPT_DIR"
  for d in skills agents rules hooks; do
    [[ -d "$SCRIPT_DIR/$d" ]] || continue
    echo "  $d/"
    prune_dead_links "$PROJECT_DIR/.claude/$d"
    link_items "$SCRIPT_DIR/$d" "$PROJECT_DIR/.claude/$d"
  done

  # ai-audit ships two skills and two agents from a live submodule — link those too
  AI="$SCRIPT_DIR/submodules/ai-audit"
  echo "  ai-audit/"
  link_items "$AI/skills" "$PROJECT_DIR/.claude/skills"
  link_items "$AI/agents" "$PROJECT_DIR/.claude/agents"
  link_items "$AI/rules"  "$PROJECT_DIR/.claude/rules"

  # ZotPilot skills are vendored real files here, so linking them is correct too.
  # dirs-only: zotpilot-skills/VENDORED.md is a file, not a skill.
  echo "  zotpilot-skills/"
  link_items "$SCRIPT_DIR/zotpilot-skills" "$PROJECT_DIR/.claude/skills" true

  # INV-11's enforcer must travel with the pipeline. It is the one check a clean
  # quarto render cannot make, so a project that cannot run it cannot verify its
  # own numbers — and a coauthor bootstrapping from a clone has nothing else.
  # Linked, not copied, so a fix to the scanner reaches every project.
  if [[ -f "$SCRIPT_DIR/scripts/prose_number_check.py" ]]; then
    echo "  scripts/"
    mkdir -p "$PROJECT_DIR/.claude/scripts"
    if [[ -e "$PROJECT_DIR/.claude/scripts/prose_number_check.py" && ! -L "$PROJECT_DIR/.claude/scripts/prose_number_check.py" ]]; then
      echo "    ⤷ prose_number_check.py is a real file here — project override, left alone"
    else
      ln -sfn "$(relpath "$SCRIPT_DIR/scripts/prose_number_check.py" "$PROJECT_DIR/.claude/scripts")" \
              "$PROJECT_DIR/.claude/scripts/prose_number_check.py"
    fi
  fi
fi

# ── scaffolding seeds (copies — project-owned, meant to be edited) ────────────
echo "→ Installing project-owned seeds"
if [[ -d "$SCRIPT_DIR/references" ]]; then
  mkdir -p "$PROJECT_DIR/.claude/references"
  for ref in "$SCRIPT_DIR/references"/*.md; do
    [[ -e "$ref" ]] || continue
    copy_seed "$ref" "$PROJECT_DIR/.claude/references/$(basename "$ref")"
  done
fi
if [[ -d "$SCRIPT_DIR/state" ]]; then
  for ex in "$SCRIPT_DIR/state"/*.example; do
    [[ -e "$ex" ]] || continue
    copy_seed "$ex" "$PROJECT_DIR/.claude/state/$(basename "$ex")"
  done
fi
[[ -f "$SCRIPT_DIR/templates/data_manifest.md" ]] && \
  copy_seed "$SCRIPT_DIR/templates/data_manifest.md" "$PROJECT_DIR/data/raw/data_manifest.md"
[[ -f "$SCRIPT_DIR/templates/ai-use-log.md" ]] && \
  copy_seed "$SCRIPT_DIR/templates/ai-use-log.md" "$PROJECT_DIR/templates/ai-use-log.md"
[[ -f "$SCRIPT_DIR/templates/gitignore" ]] && \
  copy_seed "$SCRIPT_DIR/templates/gitignore" "$PROJECT_DIR/.gitignore"
if [[ -f "$SCRIPT_DIR/templates/bootstrap-pipeline.sh" ]]; then
  copy_seed "$SCRIPT_DIR/templates/bootstrap-pipeline.sh" "$PROJECT_DIR/bootstrap-pipeline.sh"

  # A linked hook does nothing until settings.json names it, and settings.json is
  # project-owned and never linked (C4) — so without a seed a new project gets
  # twelve installed hooks and zero firing ones, which is how /freeze and
  # /careful came to be shipped with their enforcement mechanism uninstalled in
  # every project. copy_seed never overwrites, so an existing file is safe.
  copy_seed "$SCRIPT_DIR/templates/settings.json" "$PROJECT_DIR/.claude/settings.json"
  chmod +x "$PROJECT_DIR/bootstrap-pipeline.sh" 2>/dev/null || true
fi

# ── journal-digest (opt-in) ──────────────────────────────────────────────────
if [[ "$WITH_DIGEST" == true ]]; then
  echo "→ Installing journal-digest module..."
  cp -r "$SCRIPT_DIR/submodules/journal-digest" "$PROJECT_DIR/journal-digest"
  echo "  ⚠️  Next: micromamba create -n journal-digest python=3.12 -c conda-forge"
  echo "           micromamba run -n journal-digest pip install -r journal-digest/requirements.txt"
fi

# ── optional: link references to a shared directory ──────────────────────────
if [[ -n "$LINK_REFERENCES" ]]; then
  [[ -d "$LINK_REFERENCES" ]] || { echo "Error: --link-references dir not found: $LINK_REFERENCES"; exit 1; }
  REF_ABS="$(cd "$LINK_REFERENCES" && pwd)"
  echo "→ Linking .claude/references/*.md to shared dir: $REF_ABS"
  mkdir -p "$PROJECT_DIR/.claude/references"
  linked=0
  for ref in "$REF_ABS"/*.md; do
    [[ -e "$ref" ]] || continue
    ln -sfn "$ref" "$PROJECT_DIR/.claude/references/$(basename "$ref")"
    linked=$((linked + 1))
  done
  [[ "$linked" -eq 0 ]] && echo "    ⚠️  no *.md in $REF_ABS — left the installed templates in place"
fi

# ── the lock file ────────────────────────────────────────────────────────────
write_lock() {
  local sha mode
  sha="$(git -C "$SCRIPT_DIR" rev-parse HEAD)"
  mode="pinned"; [[ "$TIP_MODE" == true ]] && mode="tip (shared checkout)"
  cat > "$PROJECT_DIR/.claude/pipeline.lock" <<EOF
# Which research-claude produced this project's pipeline.
# Committed on purpose: it is replication provenance, and it is what
# ./bootstrap-pipeline.sh checks out for a coauthor.
repo=https://github.com/EconGeo/research-claude.git
commit=$sha
generated=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# installed via: $mode
EOF
}
write_lock

echo ""
echo "✓ Pipeline linked into $PROJECT_DIR/.claude/"
echo "  source:  $SCRIPT_DIR"
echo "  commit:  $(git -C "$SCRIPT_DIR" rev-parse --short HEAD)"
echo ""
echo "Editing a linked skill/agent/rule edits EVERY project. See rules/shared-pipeline.md."
echo "Run /promote to land such an edit upstream."
echo ""
echo "Next steps:"
echo "  1. Set up the ZotPilot Python env (see README)"
echo "  2. Register the ZotPilot MCP server in $PROJECT_DIR/.mcp.json"
echo "  3. Run 'zotpilot index' to index your library"
echo "  4. Restart Claude Code"
