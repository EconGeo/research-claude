#!/usr/bin/env bash
# tests/evals/civilize.sh — functionality eval for /civilize (ai-audit, vendored). Plants an
# AI-voiced paragraph so the auditor has something to find; asserts dispatch scope and no edits.
# Run alone.
source "$(dirname "$0")/_lib.sh"
eval_setup
python3 - "$E/manuscript_fixture.qmd" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("# Conclusion\n", "# Conclusion\n\nMoreover, it is important to note that this important contribution sheds light on the rich tapestry of staggered adoption. Furthermore, our novel approach might potentially be argued to play a crucial role. In conclusion, we delve into the complexities.\n", 1)
p.write_text(s)
PY
git -C "$E" add -A && git -C "$E" -c user.name=fx -c user.email=fx@x commit -qm "plant AI voice" >/dev/null
eval_run '/civilize manuscript_fixture.qmd --severity high' "$LOG" "Read" "Grep" "Glob" "Write" "Agent"
eval_finish check_civilize.py "$LOG" "$E"
