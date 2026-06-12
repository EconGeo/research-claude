#!/usr/bin/env bash
# apply.sh — install research-claude skills and agents into a target project
#
# Usage:
#   ./apply.sh --project-dir /path/to/your/project    # first install
#   ./apply.sh --project-dir /path/to/your/project --update  # pull latest + reinstall
#   ./apply.sh --project-dir /path/to/your/project --with-digest  # also installs journal-digest
#   ./apply.sh --list  # show what would be installed
#
# What this installs:
#   From clo-author:   .claude/agents/*.md, .claude/skills/, .claude/rules/,
#                      .claude/state/obsidian-config.md.example (opt-in Obsidian integration template)
#   From ai-audit:     .claude/skills/humanize/, .claude/skills/verify-claims/,
#                      .claude/agents/humanize-auditor.md, .claude/agents/claim-verifier.md
#                      .claude/rules/ai-disclosure.md
#   From zotpilot:     .claude/skills/ztp-*/, .claude/skills/seed-papers/
#   From research-claude (own skills/):
#                      .claude/skills/new-project-ztp/
#                      .claude/skills/ztp-data-tag/
#   From research-claude (own rules/):
#                      .claude/rules/quarto-empirical.md         (required pipeline for new projects)
#                      .claude/rules/data-manifest.md            (raw-data provenance audit trail)
#                      .claude/rules/quarto-pdf.md               (PDF output format reference for manuscript.qmd)
#                      .claude/rules/quarto-word.md              (Word docx output format reference)
#                      .claude/rules/registry-verification-gate.md (legacy: registry-pattern projects)
#
# What this does NOT install:
#   ZotPilot Python env (requires user judgment about paths — see Step 7 in README)
#   journal-digest Python env (same reason; install manually per README)
#   Any LaunchAgent plists (macOS scheduling — opt-in)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR=""
UPDATE_MODE=false
WITH_DIGEST=false
LIST_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --update)      UPDATE_MODE=true; shift ;;
    --with-digest) WITH_DIGEST=true; shift ;;
    --list)        LIST_MODE=true; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ "$LIST_MODE" == true ]]; then
  echo "apply.sh would install:"
  echo ""
  echo "From clo-author (submodules/clo-author):"
  echo "  .claude/agents/ — all research pipeline agents"
  echo "  .claude/skills/ — all research skills (strategize, write, review-paper, etc.)"
  echo "  .claude/rules/  — working-paper-format, quarto rules, etc."
  echo "  .claude/state/obsidian-config.md.example — opt-in Obsidian integration template"
  echo ""
  echo "From ai-audit (submodules/ai-audit):"
  echo "  .claude/skills/humanize/"
  echo "  .claude/skills/verify-claims/"
  echo "  .claude/agents/humanize-auditor.md"
  echo "  .claude/agents/claim-verifier.md"
  echo "  .claude/rules/ai-disclosure.md"
  echo ""
  echo "From zotpilot (submodules/zotpilot/claude-skills/):"
  echo "  .claude/skills/ztp-research/"
  echo "  .claude/skills/ztp-review/"
  echo "  .claude/skills/ztp-setup/"
  echo "  .claude/skills/ztp-profile/"
  echo "  .claude/skills/ztp-tutor/"
  echo "  .claude/skills/seed-papers/  — pre-search Zotero before /discover lit"
  echo ""
  echo "From research-claude (own skills/):"
  echo "  .claude/skills/new-project-ztp/  — ZotPilot setup after /new-project"
  echo "  .claude/skills/ztp-data-tag/     — backfill dataset/variable tags+notes across the Zotero library"
  echo ""
  echo "From research-claude (own rules/):"
  echo "  .claude/rules/quarto-empirical.md            — required pipeline: single .qmd, cached, PDF primary"
  echo "  .claude/rules/data-manifest.md               — raw-data provenance audit trail (data/raw/data_manifest.md)"
  echo "  .claude/rules/quarto-pdf.md                  — PDF output format reference (pdf: block, kableExtra, XeLaTeX)"
  echo "  .claude/rules/quarto-word.md                 — Word output format reference (docx: block, flextable, APA CSL)"
  echo "  .claude/rules/registry-verification-gate.md  — legacy: registry-pattern projects only"
  echo ""
  if [[ "$WITH_DIGEST" == true ]]; then
    echo "With --with-digest:"
    echo "  journal-digest/ (full Python module, requires 'micromamba create -n journal-digest')"
  fi
  exit 0
fi

if [[ -z "$PROJECT_DIR" ]]; then
  echo "Error: --project-dir is required"
  echo "Usage: ./apply.sh --project-dir /path/to/your/project"
  exit 1
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Error: project directory not found: $PROJECT_DIR"
  exit 1
fi

echo "→ Installing research-claude into: $PROJECT_DIR"
echo ""

# Update submodules if requested
if [[ "$UPDATE_MODE" == true ]]; then
  echo "→ Updating submodules..."
  git -C "$SCRIPT_DIR" submodule update --remote
fi

# Create .claude/ subdirectories
mkdir -p "$PROJECT_DIR/.claude/agents" \
         "$PROJECT_DIR/.claude/skills" \
         "$PROJECT_DIR/.claude/rules"

# ── 1. clo-author: agents + skills + rules ────────────────────────────────────
CLO="$SCRIPT_DIR/submodules/clo-author"
if [[ -d "$CLO/.claude/agents" ]]; then
  echo "→ Installing clo-author agents..."
  cp "$CLO/.claude/agents/"*.md "$PROJECT_DIR/.claude/agents/" 2>/dev/null || true
fi
if [[ -d "$CLO/.claude/skills" ]]; then
  echo "→ Installing clo-author skills..."
  cp -r "$CLO/.claude/skills/"* "$PROJECT_DIR/.claude/skills/" 2>/dev/null || true
fi
if [[ -d "$CLO/.claude/rules" ]]; then
  echo "→ Installing clo-author rules..."
  cp "$CLO/.claude/rules/"*.md "$PROJECT_DIR/.claude/rules/" 2>/dev/null || true
fi
if [[ -d "$CLO/.claude/state" ]]; then
  echo "→ Installing clo-author state templates (Obsidian config example)..."
  mkdir -p "$PROJECT_DIR/.claude/state"
  cp "$CLO/.claude/state/"*.example "$PROJECT_DIR/.claude/state/" 2>/dev/null || true
fi

# ── 2. ai-audit: humanize, verify-claims, ai-disclosure ──────────────────────
AI="$SCRIPT_DIR/submodules/ai-audit"
if [[ -d "$AI/skills" ]]; then
  echo "→ Installing ai-audit skills..."
  cp -r "$AI/skills/"* "$PROJECT_DIR/.claude/skills/" 2>/dev/null || true
fi
if [[ -d "$AI/agents" ]]; then
  echo "→ Installing ai-audit agents..."
  cp "$AI/agents/"*.md "$PROJECT_DIR/.claude/agents/" 2>/dev/null || true
fi
if [[ -d "$AI/rules" ]]; then
  echo "→ Installing ai-audit rules..."
  cp "$AI/rules/"*.md "$PROJECT_DIR/.claude/rules/" 2>/dev/null || true
fi

# ── 3. ZotPilot: claude-skills (ztp-*) ───────────────────────────────────────
ZTP="$SCRIPT_DIR/submodules/zotpilot"
if [[ -d "$ZTP/claude-skills" ]]; then
  echo "→ Installing ZotPilot claude-skills (ztp-*)..."
  cp -r "$ZTP/claude-skills/"* "$PROJECT_DIR/.claude/skills/" 2>/dev/null || true
fi

# ── 4. journal-digest (opt-in) ───────────────────────────────────────────────
if [[ "$WITH_DIGEST" == true ]]; then
  JD="$SCRIPT_DIR/submodules/journal-digest"
  echo "→ Installing journal-digest module..."
  cp -r "$JD" "$PROJECT_DIR/journal-digest"
  echo ""
  echo "  ⚠️  Next step for journal-digest:"
  echo "    micromamba create -n journal-digest python=3.12 -c conda-forge"
  echo "    micromamba run -n journal-digest pip install -r journal-digest/requirements.txt"
  echo "    Then edit journal-digest/config.py with your Zotero paths and keywords."
fi

# ── 5. research-claude own skills (bridge skills) ────────────────────────────
# Skills that live in research-claude itself — bridge ZotPilot, clo-author, and
# other submodule tools without modifying upstream repos.
RC_SKILLS="$SCRIPT_DIR/skills"
if [[ -d "$RC_SKILLS" ]]; then
  echo "→ Installing research-claude bridge skills (seed-papers, etc.)..."
  cp -r "$RC_SKILLS/"* "$PROJECT_DIR/.claude/skills/" 2>/dev/null || true
fi

# ── 6. research-claude own rules (quarto-pdf, quarto-word) ───────────────────
RC_RULES="$SCRIPT_DIR/rules"
if [[ -d "$RC_RULES" ]]; then
  echo "→ Installing research-claude rules (quarto-empirical, data-manifest, quarto-pdf, quarto-word, registry-verification-gate)..."
  cp "$RC_RULES/"*.md "$PROJECT_DIR/.claude/rules/" 2>/dev/null || true
fi

echo ""
echo "✓ Done. research-claude installed into $PROJECT_DIR/.claude/"
echo ""
echo "Next steps:"
echo "  1. Set up ZotPilot Python env (see README Step 7)"
echo "  2. Register ZotPilot MCP server in $PROJECT_DIR/.mcp.json (see README Step 7)"
echo "  3. Run 'zotpilot index' to index your library"
echo "  4. Restart Claude Code"
