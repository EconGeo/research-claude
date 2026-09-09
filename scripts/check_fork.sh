#!/usr/bin/env bash
# check_fork.sh — the TEMPLATE gate. Exit 0 = the shipped tree is complete, generic and
# conforms to the one-manuscript contract. Every criterion below was red-tested against
# the tree or the fixture before its green was trusted (docs/audits/2026-09-08_stage0-red.md).
set -uo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
SHIP=(agents skills rules references hooks templates seeds scripts)

scan() {  # scan <label> <ERE> [dir...]
  local label="$1" pat="$2"; shift 2
  local hits present=() dirs=("$@"); [[ ${#dirs[@]} -eq 0 ]] && dirs=("${SHIP[@]}")
  local d; for d in "${dirs[@]}"; do [[ -d "$RC/$d" ]] && present+=("$d"); done
  if [[ ${#present[@]} -eq 0 ]]; then echo "SKIP [$label] (no ship dirs present)"; return; fi
  hits="$(cd "$RC" && grep -rInE "$pat" "${present[@]}" 2>/dev/null | grep -vE 'residue:(historical|prohibition)' )"
  if [[ -n "$hits" ]]; then echo "FAIL [$label]"; printf '%s\n' "$hits" | sed 's/^/    /'; fail=1
  else echo "PASS [$label]"; fi
}
absent()  { if [[ -e "$RC/$2" ]]; then echo "FAIL [$1] $2 still present"; fail=1; else echo "PASS [$1] $2 gone"; fi; }
present() { if [[ -e "$RC/$2" ]]; then echo "PASS [$1] $2 present"; else echo "FAIL [$1] $2 missing"; fail=1; fi; }
contains(){ if [[ -f "$RC/$2" ]] && grep -q "$3" "$RC/$2"; then echo "PASS [$1]"; else echo "FAIL [$1] $2 missing /$3/"; fail=1; fi; }
py() {  # py <script> [args] — run a python criterion, fold its exit into $fail
  if [[ ! -f "$RC/scripts/$1" ]]; then echo "FAIL [$1] scripts/$1 absent"; fail=1; return; fi
  local s="$1"; shift; python3 "$RC/scripts/$s" --root "$RC" "$@" || fail=1
}

echo "── identity: nothing project-specific ships ──"
# Split into two scans (2026-09-08, carried forward from the pre-rewrite gate).
#
# Project IDENTITY must not appear anywhere, references/ included — a project
# name in the shipped tree is the leak D5 exists to stop. It is also scanned
# against tests/, so the shipped fixture stays generic too.
#
# Journal and data-vendor names are different. references/ holds per-user,
# per-discipline TEMPLATES — discipline-cards.md and journal-profiles.md exist
# precisely to name real journals and real data vendors, and ordinary
# land-use terminology is not a leak either. Banning those tokens from
# references/ would make it impossible to ship a discipline card at all,
# which is a worse outcome than the risk it guards against. They remain
# banned everywhere else shipped — agents/, skills/, rules/, hooks/,
# templates/, seeds/ and scripts/ (this file included, which is why this
# paragraph names none of them) — where a journal name IS a project leak.
#
# The `<!-- residue:prohibition -->` marker on the three scan lines below is
# this file's one reserved use of that convention: it exempts a line that
# NAMES a forbidden pattern in order to forbid it, never a line that uses one.
scan project-identity 'POGM|SFPP|WRLURI|zoning2026|NAR_settlement|manuscript_quarto_word' "${SHIP[@]}" tests  # <!-- residue:prohibition -->
scan project-nouns    'JREPM|JRER|CoStar|[^a-z]zoning|WRLURI|[^A-Za-z]NAR[^A-Za-z]' agents skills rules hooks templates seeds scripts  # <!-- residue:prohibition -->
scan course-leak      'academic course materials|Beamer slides|TikZ Freshness'  # <!-- residue:prohibition -->

echo "── structure ──"
absent clo-author-submodule submodules/clo-author
absent pipeline-precedence  rules/pipeline-precedence.md
grep -q 'clo-author' "$RC/.gitmodules" 2>/dev/null && { echo "FAIL [gitmodules]"; fail=1; } || echo "PASS [gitmodules]"
grep -q 'CLO_SKIP_SKILLS' "$RC/apply.sh" 2>/dev/null && { echo "FAIL [apply.sh]"; fail=1; } || echo "PASS [apply.sh]"
contains cc-correctness-half agents/coder-critic.md 'Correctness Layer'
contains cc-invariant-half   agents/coder-critic.md 'INV-23'

echo "── D1 inverted: the registry, lifecycle and governance are back; the agent is not ──"
for p in rules/registry.yaml rules/permissions.md rules/lifecycle.md rules/meta-governance.md \
         agents/lit-critic.md skills/pipeline/SKILL.md scripts/pipeline.py scripts/registry_lib.py \
         hooks/dispatch-log.py hooks/critic-pairing.py tests/run_fixture.sh templates/pipeline-state.json \
         templates/journal-profile-template.md seeds/quarto-preamble.tex scripts/SHIPPED; do present d1-restored "$p"; done
for g in agents/orchestrator.md agents/guide-writer.md agents/librarian.md agents/librarian-critic.md \
         rules/workflow.md rules/working-paper-format.md rules/html-dashboard.md skills/dashboard \
         references/coding-standards-rmd.md references/prompt-formatting-core.md hooks/post-merge.sh \
         skills/analyze/templates/r-script-structure.R skills/analyze/templates/python-script-structure.py \
         skills/analyze/templates/results-summary.md skills/submit/templates/cover-letter.tex root-skills; do absent d1-deletions "$g"; done

echo "── text criteria (scripts/check_refs.py) ──"
for c in latex-residue manuscript-model deleted-things inv-refs skill-refs tool-name hooks-readme; do
  py check_refs.py --criterion "$c"
done

echo "── path layer (scripts/check_paths.py) ──"
py check_paths.py

echo "── registry (scripts/pipeline.py registry check) ──"
py pipeline.py registry check    # prints PASS/FAIL for registry-complete, registry-authority, registry-rendered, weights-sum, registry-parse-agree

echo "── seeds and shipped scripts ──"
if grep -rq 'quarto-preamble\.tex' "$RC/rules" && [[ ! -f "$RC/seeds/quarto-preamble.tex" ]]; then
  echo "FAIL [seeds-complete] rules require seeds/quarto-preamble.tex but seeds/ does not ship it"; fail=1
else echo "PASS [seeds-complete]"; fi
if [[ -f "$RC/scripts/SHIPPED" ]]; then
  manifest_ok=true
  while read -r s; do [[ -z "$s" || -f "$RC/scripts/$s" ]] || { echo "FAIL [scripts-manifest] $s listed but absent"; fail=1; manifest_ok=false; }; done < "$RC/scripts/SHIPPED"
  [[ "$manifest_ok" == true ]] && echo "PASS [scripts-manifest]"
else echo "FAIL [scripts-manifest] scripts/SHIPPED missing"; fail=1; fi

echo "── fixture ──"
if [[ -x "$RC/tests/run_fixture.sh" ]]; then "$RC/tests/run_fixture.sh" >/tmp/run_fixture.$$ 2>&1 && echo "PASS [fixture]" || { echo "FAIL [fixture]"; tail -15 /tmp/run_fixture.$$ | sed 's/^/    /'; fail=1; }; rm -f /tmp/run_fixture.$$
else echo "FAIL [fixture] tests/run_fixture.sh missing"; fail=1; fi

[[ $fail -eq 0 ]] && echo "✓ check_fork: PASS" || echo "✗ check_fork: FAIL"
exit $fail
