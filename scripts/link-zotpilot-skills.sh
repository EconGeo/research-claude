#!/usr/bin/env bash
# link-zotpilot-skills.sh <dir> — link each vendored ZotPilot skill into <dir>/.claude/skills/.
# For a directory that is not a paper project but hosts sessions (the research root), so it
# loads the same zotpilot-skills/ copy the papers do. A real directory there is left alone.
set -euo pipefail
RC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
DIR="$(cd "${1:?usage: link-zotpilot-skills.sh <dir>}" && pwd -P)"
mkdir -p "$DIR/.claude/skills"
for s in "$RC/zotpilot-skills"/*/; do
  n="$(basename "$s")"; t="$DIR/.claude/skills/$n"
  if [[ -e "$t" && ! -L "$t" ]]; then echo "  ⤷ $n is a real directory — left alone"; continue; fi
  ln -sfn "$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "${s%/}" "$DIR/.claude/skills")" "$t"
  echo "  $n -> zotpilot-skills/$n"
done
