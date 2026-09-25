#!/usr/bin/env bash
# tests/evals/verify-claims.sh — functionality eval for /verify-claims (ai-audit, vendored).
# draft.md carries five claims and a draft-only sentinel; source.md is the ground truth. Run alone.
source "$(dirname "$0")/_lib.sh"
eval_setup
SENTINEL="ORCHID-LANTERN-42"
cat >"$E/source.md" <<'MD'
# Source notes (ground truth)

- Callaway and Sant'Anna (2021, Journal of Econometrics) define the group-time ATT.
- Goodman-Bacon (2021, Journal of Econometrics) decomposes the two-way fixed-effects estimator.
- The fixture panel has N = 40 units observed over 10 years (400 unit-years).
- Sun and Abraham (2021, Journal of Econometrics) propose an interaction-weighted estimator.
MD
cat >"$E/draft.md" <<MD
# Draft

Callaway and Sant'Anna (2021) define the group-time ATT. Goodman-Bacon (2021) decomposes the TWFE estimator.
The fixture panel has N = 4,000 units. Sun and Abraham (2021) propose an interaction-weighted estimator.
Hartwell and Pines (2018, Econometrica) prove the fixture estimator is unbiased under staggered timing.
The draft-only sentinel phrase is $SENTINEL.
MD
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "draft and source" >/dev/null
eval_run '/verify-claims draft.md --source source.md' "$LOG" "Read" "Grep" "Glob" "Agent" "Write"
eval_finish check_verify_claims.py "$LOG" "$E" "$SENTINEL"
