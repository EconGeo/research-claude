#!/usr/bin/env bash
# tests/evals/promote.sh — functionality eval for /promote against a SCRATCH CLONE of this
# checkout, so the skill's `git -C $RC commit` can never land in the real repo. Plants the audit's
# three inputs. The clone is kept with $E on FAIL. Run alone.
source "$(dirname "$0")/_lib.sh"
: "${EVAL_TIMEOUT:=900}"
C="$(mktemp -d)/research-claude"
git clone -q "$RC" "$C" || { echo "clone failed"; exit 1; }
ORIG="$(git -C "$C" rev-parse HEAD)"
RC_LINK="$C" eval_setup
trap 'eval_cleanup; [[ "${status:-1}" == 0 && "${KEEP:-0}" != 1 ]] && rm -rf "$(dirname "$C")" || echo "kept clone: $C"' EXIT
printf '\nTarget: Journal of Urban Economics.\n' >>"$C/skills/write/SKILL.md"           # journal name — check_fork must refuse
printf '\n<!-- generic clarification: the writer lists chunk labels before reading -->\n' >>"$C/agents/writer.md"
rm "$E/.claude/rules/quality.md" && cp "$C/rules/quality.md" "$E/.claude/rules/quality.md" && printf '\n<!-- project override: local weight note -->\n' >>"$E/.claude/rules/quality.md"
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "override" >/dev/null
eval_run '/promote' "$LOG" "Read" "Grep" "Glob" "Bash" "Edit"
python3 "$RC/tests/evals/check_promote.py" "$LOG" "$C" "$ORIG"; status=$?
[[ "$(git -C "$RC" status --porcelain | grep -E "$LINKED_DIRS_RE" || true)" == "$RC_BEFORE" ]] || { echo "FAIL real checkout modified"; status=1; }
exit $status
