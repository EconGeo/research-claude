#!/usr/bin/env bash
# check_fork.sh — executable gate for the Quarto-native fork.
# Implements the spec's success criteria 1, 3, 6, 7, 8 and the D1 deletions.
# Exit 0 = fork is complete and clean.
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

# Directories that ship into a project. zotpilot-skills/ is vendored verbatim and exempt (D5).
SHIP=(agents skills rules references hooks templates)

scan() {  # scan <label> <extended-regex>
  local label="$1" pat="$2" hits present=()
  local d; for d in "${SHIP[@]}"; do [[ -d "$RC/$d" ]] && present+=("$d"); done
  if [[ ${#present[@]} -eq 0 ]]; then echo "SKIP [$label] (no ship dirs yet)"; return; fi
  hits="$(cd "$RC" && grep -rInE "$pat" "${present[@]}" 2>/dev/null)"
  if [[ -n "$hits" ]]; then
    echo "FAIL [$label]"; printf '%s\n' "$hits" | sed 's/^/    /'; fail=1
  else
    echo "PASS [$label]"
  fi
}

absent() {  # absent <label> <path>
  if [[ -e "$RC/$2" ]]; then echo "FAIL [$1] $2 still present"; fail=1
  else echo "PASS [$1] $2 gone"; fi
}

contains() {  # contains <label> <file> <pattern>
  if [[ -f "$RC/$2" ]] && grep -q "$3" "$RC/$2"; then echo "PASS [$1]"
  else echo "FAIL [$1] $2 missing /$3/"; fail=1; fi
}

echo "── criterion 6: no LaTeX / multi-file pipeline residue ──"
scan latex-residue 'latexmk|\\doublespacing|threeparttable|paper/main\.tex|paper/sections|Emory'

echo "── criterion 7: no project nouns, no non-standard manuscript filename ──"
scan project-nouns 'POGM|JREPM|JRER|CoStar|SFPP|zoning|WRLURI|NAR|manuscript_quarto_word'

echo "── criteria 1-3: the fork is structural ──"
absent clo-author-submodule submodules/clo-author
absent pipeline-precedence  rules/pipeline-precedence.md
if grep -q 'clo-author' "$RC/.gitmodules" 2>/dev/null; then
  echo "FAIL [gitmodules] .gitmodules still names clo-author"; fail=1
else echo "PASS [gitmodules]"; fi
if grep -q 'CLO_SKIP_SKILLS' "$RC/apply.sh" 2>/dev/null; then
  echo "FAIL [apply.sh] still references CLO_SKIP_SKILLS"; fail=1
else echo "PASS [apply.sh]"; fi

echo "── criterion 8: the coder-critic merge kept both halves ──"
contains cc-zoning-half  agents/coder-critic.md 'Correctness Layer'
contains cc-pogm-half    agents/coder-critic.md 'INV-23'

echo "── D1: the orchestration graph is gone ──"
for gone in agents/orchestrator.md agents/guide-writer.md agents/librarian.md \
            agents/librarian-critic.md rules/permissions.md rules/lifecycle.md \
            rules/workflow.md rules/working-paper-format.md rules/meta-governance.md \
            root-skills; do
  absent d1-deletions "$gone"
done

echo "── C1: no ~/Courses domain leak ──"
scan course-leak 'academic course materials|Beamer slides|TikZ Freshness'

[[ $fail -eq 0 ]] && echo "✓ check_fork: PASS" || echo "✗ check_fork: FAIL"
exit $fail
