#!/usr/bin/env bash
# check_install.sh — the project-side gate, counterpart to check_fork.sh.
#
#   check_fork.sh     guards the TEMPLATE: nothing project-specific ships.
#   check_install.sh  guards an INSTALL:   the link tree in one paper repo is
#                     complete, current, resolving, and not committed.
#
# Run it from a paper repo, or point it anywhere:
#   ./check_install.sh                       # $PWD
#   ./check_install.sh --project-dir ~/Research/BRI
#   ./check_install.sh --all                 # every project under $RESEARCH_DIR
#
# Exit 0 = this project's pipeline is correctly installed.
#
# Why this exists. Per-item symlinks (D9) propagate EDITS instantly but not
# MEMBERSHIP: a file added upstream gets no link here until apply.sh runs again.
# Nothing surfaced that, and one project silently sat without rules/session-handoff.md
# for a day. Separately, five of six repos had their symlinks committed — gitignore
# does not untrack what is already in the index — which hands a coauthor a clone
# full of dangling machine-specific links. Both are invisible in normal use and
# both are mechanical to detect, which is exactly what belongs in a script.
set -uo pipefail

PROJECT_DIR="$PWD"; ALL=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --all)         ALL=true; shift ;;
    -h|--help)     sed -n '2,17p' "$0"; exit 0 ;;
    *)             echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Linked dirs the pipeline owns. settings.json / references / state are
# project-owned or installed by another mechanism and are not checked here.
LINKED=(skills agents rules hooks scripts templates)

fail=0

# Every symlink under a dir the pipeline owns, one per line. Deliberately not
# all of .claude: references/ is linked by a separate mechanism at a separate
# source, and state/ and logs/ are project-owned.
pipeline_links() {
  local P="$1" d
  for d in "${LINKED[@]}"; do
    [[ -d "$P/.claude/$d" ]] || continue
    find "$P/.claude/$d" -maxdepth 1 -type l 2>/dev/null
  done
}

ok()   { echo "PASS [$1]${2:+ $2}"; }
bad()  { echo "FAIL [$1] $2"; fail=1; }
warn() { echo "WARN [$1] $2"; }

check_project() {
  local P; P="$(cd "$1" 2>/dev/null && pwd -P)" || { echo "no such directory: $1" >&2; return 2; }
  echo "══ $P"

  [[ -d "$P/.claude" ]] || { bad structure ".claude/ does not exist — not a converted project"; return; }

  # ── Resolve the canonical checkout from the links themselves ───────────────
  # The links are the ground truth, not the lock and not an env var: whatever
  # they point at IS what this project loads.
  #
  # Only the dirs the pipeline owns. .claude/references/ is also symlinked, but
  # by --link-references into a shared reference dir that is not a checkout —
  # resolving from one of those lands on .claude itself.
  local RC="" l cand
  while IFS= read -r l; do
    cand="$(cd "$(dirname "$l")" && cd "$(dirname "$(readlink "$l")")/.." 2>/dev/null && pwd -P)" || continue
    [[ -d "$cand/agents" && -d "$cand/skills" ]] || continue
    RC="$cand"; break
  done < <(pipeline_links "$P")
  if [[ -z "$RC" || ! -d "$RC/agents" ]]; then
    bad checkout "cannot resolve the research-claude checkout from any link"; return
  fi
  ok checkout "$RC"

  # ── 0. The shared checkout is on main or a detached lock SHA ─────────────
  # Any `git checkout <branch>` in the shared tree re-points all six papers at once.
  # Set RESEARCH_CLAUDE_ALLOW_BRANCH=1 only while a named canary is deliberately linked
  # to a worktree; that downgrades the FAIL to a named WARN.
  local br_rc; br_rc="$(git -C "$RC" symbolic-ref -q --short HEAD 2>/dev/null || echo DETACHED)"
  if [[ "$br_rc" == "main" ]]; then ok branch "checkout on main"
  elif [[ "$br_rc" == "DETACHED" && "$(git -C "$RC" rev-parse HEAD)" == "$(sed -n 's/^commit=//p' "$P/.claude/pipeline.lock" 2>/dev/null)" ]]; then ok branch "detached at the lock SHA"
  elif [[ "${RESEARCH_CLAUDE_ALLOW_BRANCH:-0}" == "1" ]]; then warn branch "checkout on '$br_rc' — allowed by RESEARCH_CLAUDE_ALLOW_BRANCH=1"
  else bad branch "checkout is on '$br_rc', not main and not the lock SHA"; fi

  # ── 1. No dangling links ──────────────────────────────────────────────────
  local dangling
  dangling="$(find "$P/.claude" -maxdepth 2 -type l ! -exec test -e {} \; -print 2>/dev/null)"
  if [[ -n "$dangling" ]]; then
    bad dangling "links resolve to nothing:"; printf '%s\n' "$dangling" | sed "s|$P/|    |"
  else ok dangling "every link resolves"; fi

  # ── 2. No committed symlinks ──────────────────────────────────────────────
  # Mode 120000 in the index under a linked dir. gitignore cannot untrack these;
  # only `git rm --cached` can. Their targets are machine-specific, so a clone
  # dangles before bootstrap and stays dirty after.
  if git -C "$P" rev-parse --git-dir >/dev/null 2>&1; then
    local br tracked paths=()
    br="$(git -C "$P" rev-parse --abbrev-ref HEAD)"
    local d; for d in "${LINKED[@]}"; do paths+=(".claude/$d"); done
    tracked="$(git -C "$P" ls-tree -r "$br" --format='%(objectmode) %(path)' -- "${paths[@]}" 2>/dev/null \
               | awk '$1=="120000"{print $2}')"
    if [[ -n "$tracked" ]]; then
      bad tracked-links "$(printf '%s\n' "$tracked" | wc -l | tr -d ' ') symlinks are committed — run:"
      echo "    git -C $P rm -r --cached <them>   # see docs; files stay on disk"
      printf '%s\n' "$tracked" | head -5 | sed 's/^/    /'
      [[ $(printf '%s\n' "$tracked" | wc -l) -gt 5 ]] && echo "    …"
    else ok tracked-links "no symlink is committed"; fi
  else
    warn git "not a git repository — skipping index checks"
  fi

  # ── 3. Membership is current ──────────────────────────────────────────────
  # Every item apply.sh would link must be present here, as a link or as a
  # deliberate real override. Anything missing means this project has not been
  # re-linked since that item was added upstream.
  local missing=()
  want() {  # want <src-dir> <dest-subdir> [dirs-only]
    local src="$1" dest="$P/.claude/$2" dirs_only="${3:-false}" item name
    [[ -d "$src" ]] || return 0
    for item in "$src"/*; do
      [[ -e "$item" ]] || continue
      [[ "$dirs_only" == true && ! -d "$item" ]] && continue
      name="$(basename "$item")"
      [[ -e "$dest/$name" || -L "$dest/$name" ]] || missing+=("$2/$name")
    done
  }
  local d; for d in skills agents rules hooks templates; do want "$RC/$d" "$d"; done
  want "$RC/submodules/ai-audit/skills" skills
  want "$RC/submodules/ai-audit/agents" agents
  want "$RC/submodules/ai-audit/rules"  rules
  want "$RC/zotpilot-skills" skills true
  if [[ -f "$RC/scripts/SHIPPED" ]]; then
    while IFS= read -r s; do [[ -z "$s" || ! -f "$RC/scripts/$s" ]] && continue
      [[ -e "$P/.claude/scripts/$s" || -L "$P/.claude/scripts/$s" ]] || missing+=("scripts/$s"); done < "$RC/scripts/SHIPPED"
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    bad membership "${#missing[@]} upstream item(s) never linked here — run ./bootstrap-pipeline.sh --tip"
    printf '    %s\n' "${missing[@]}"
  else ok membership "every upstream item is present"; fi

  # ── 4. Every link points into THIS checkout ───────────────────────────────
  # A link into some other clone would load a different pipeline than the one
  # the lock and /promote name, and edits through it would land nowhere visible.
  local stray=() t
  while IFS= read -r l; do
    t="$(cd "$(dirname "$l")" && cd "$(dirname "$(readlink "$l")")" 2>/dev/null && pwd -P)" || continue
    [[ "$t" == "$RC"/* || "$t" == "$RC" ]] || stray+=("${l#"$P"/} -> $(readlink "$l")")
  done < <(pipeline_links "$P")
  if [[ ${#stray[@]} -gt 0 ]]; then
    bad link-target "${#stray[@]} link(s) point outside $RC"; printf '    %s\n' "${stray[@]}"
  else ok link-target "all links point into the resolved checkout"; fi

  # ── 5. Real overrides survive a clone ─────────────────────────────────────
  # A real file inside a gitignored directory needs an explicit !negation, and
  # the `/*` form to negate into at all. Without it the override is in nobody's
  # clone but this machine's — the failure Task 18 caught in the template.
  if git -C "$P" rev-parse --git-dir >/dev/null 2>&1; then
    local lost=() f
    while IFS= read -r f; do
      git -C "$P" ls-files --error-unmatch "${f#"$P"/}" >/dev/null 2>&1 || lost+=("${f#"$P"/}")
    done < <(for d in "${LINKED[@]}"; do
               [[ -d "$P/.claude/$d" ]] || continue
               # ! -name, not ! -path '*/.*': every path here is under .claude,
               # so a path test excludes the entire tree.
               find "$P/.claude/$d" -maxdepth 2 -type f ! -name '.*' 2>/dev/null
             done)
    if [[ ${#lost[@]} -gt 0 ]]; then
      bad override-tracked "${#lost[@]} real file(s) under a linked dir are untracked — add a !negation to .gitignore"
      printf '    %s\n' "${lost[@]}" | head -8
    else ok override-tracked "every project override is committed"; fi
  fi

  # ── 6. Lock provenance ────────────────────────────────────────────────────
  # In --tip mode the lock is an install-time stamp, so it goes stale as the
  # pipeline advances. That is not an error; it is only wrong at submission,
  # when the lock is supposed to say which pipeline wrote the manuscript.
  local lock="$P/.claude/pipeline.lock"
  if [[ ! -f "$lock" ]]; then
    bad lock "pipeline.lock missing — a coauthor has nothing to bootstrap from"
  else
    local locked head
    locked="$(sed -n 's/^commit=//p' "$lock")"
    head="$(git -C "$RC" rev-parse HEAD 2>/dev/null)"
    if [[ "$locked" == "$head" ]]; then
      ok lock "${locked:0:7} == checkout HEAD"
    else
      local behind; behind="$(git -C "$RC" rev-list --count "$locked..$head" 2>/dev/null)"
      warn lock "records ${locked:0:7}, checkout is at ${head:0:7} (${behind:-?} commits later) — refresh before submission"
    fi
  fi
  # ── 7. Manuscript declared (D-8) ──────────────────────────────────────────
  # Every predicate, hook and skill resolves the manuscript through CLAUDE.md.
  local decl; decl="$(grep -cE '^manuscript:\s*\S+\.qmd\s*$' "$P/CLAUDE.md" 2>/dev/null || true)"; decl="${decl:-0}"
  if [[ "$decl" -eq 1 ]]; then
    local mf; mf="$(sed -nE 's/^manuscript:[[:space:]]*([^[:space:]]+\.qmd)[[:space:]]*$/\1/p' "$P/CLAUDE.md")"
    [[ -f "$P/$mf" ]] && ok manuscript-declared "$mf" || bad manuscript-declared "CLAUDE.md declares $mf but it does not exist"
  elif [[ "$decl" -eq 0 ]]; then
    if [[ -n "$(find "$P" -maxdepth 2 -name '*.qmd' -not -path '*/talks/*' -not -path '*/explorations/*' -print -quit)" ]]; then
      bad manuscript-declared "no 'manuscript: <file>.qmd' line in CLAUDE.md"
    else warn manuscript-declared "no manuscript yet — /pipeline refuses until one is declared"; fi
  else bad manuscript-declared "CLAUDE.md declares $decl manuscripts; exactly one is required"; fi

  # ── 8. gitignore covers the linked dirs ───────────────────────────────────
  local gi_missing=() pat
  for pat in '.claude/skills/*' '.claude/agents/*' '.claude/rules/*' '.claude/hooks/*' '.claude/scripts/*' '.claude/templates/*' 'quality_reports/agent_dispatch.jsonl'; do
    grep -qxF "$pat" "$P/.gitignore" 2>/dev/null || gi_missing+=("$pat")
  done
  [[ ${#gi_missing[@]} -eq 0 ]] && ok gitignore-covers || bad gitignore-covers "missing lines: ${gi_missing[*]}"

  # ── 9. State file is schema-valid when present ────────────────────────────
  if [[ -f "$P/quality_reports/pipeline_state.json" ]]; then
    if python3 "$RC/scripts/pipeline.py" --root "$P" state validate >/dev/null 2>&1; then ok state-valid
    else bad state-valid "quality_reports/pipeline_state.json fails pipeline.py state validate"; fi
  else warn state-valid "no pipeline_state.json yet"; fi

  [[ -f "$P/bootstrap-pipeline.sh" ]] && ok bootstrap || bad bootstrap "bootstrap-pipeline.sh missing"
}

if [[ "$ALL" == true ]]; then
  RESEARCH_DIR="${RESEARCH_DIR:-$HOME/Research}"
  for p in "$RESEARCH_DIR"/*/; do
    [[ -d "$p/.claude" && -f "$p/bootstrap-pipeline.sh" ]] || continue
    check_project "$p"; echo
  done
else
  check_project "$PROJECT_DIR"
fi

[[ $fail -eq 0 ]] && echo "✓ check_install: PASS" || echo "✗ check_install: FAIL"
exit $fail
