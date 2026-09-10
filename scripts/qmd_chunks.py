#!/usr/bin/env python3
r"""qmd_chunks.py — extract R chunk bodies from a Quarto .qmd file (D-7).

D-7: there is exactly one manuscript, a single .qmd, and all analysis code
lives in its R chunks. `.claude/hooks/lint-scripts.sh` only knows how to grep .R/.py/.jl
files; this script gives it something to grep by pulling the R chunk bodies
out of the .qmd and printing them as if they were a standalone .R file.

The one property that matters: line numbers in the output are IDENTICAL to
line numbers in the source .qmd. Every line of input produces exactly one
line of output — a chunk-body line is printed verbatim, every other line
(prose, fences, non-R chunk bodies) is replaced with a blank line. A linter
finding at line N of the extract is therefore line N of the .qmd; anything
less would make its diagnostics lies.

Chunk options (`#|` lines) are ordinary R comments and need no special
handling — they are already inside the chunk body and pass through verbatim.

Fences matched: open `^```{r` (covers `{r}`, `{r label}`, `{r, echo=FALSE}`,
...); close: a bare ``` ``` `` line (```` ^```\s*$ ````). A non-R chunk (e.g.
`{python}`) never sets the in-chunk flag, so its fences and body are all
blanked like ordinary prose.

Usage: python3 qmd_chunks.py <file.qmd>
Stdlib only (Python 3.9).
"""
import re
import sys

FENCE_OPEN_R = re.compile(r"^```\{r")
FENCE_CLOSE = re.compile(r"^```\s*$")


def extract(lines):
    """Return one output line per input line: chunk body lines verbatim,
    everything else (prose, fences, non-R chunk bodies) blanked."""
    out = []
    in_r_chunk = False
    for line in lines:
        if not in_r_chunk:
            if FENCE_OPEN_R.match(line):
                in_r_chunk = True
            out.append("")
        else:
            if FENCE_CLOSE.match(line):
                in_r_chunk = False
                out.append("")
            else:
                out.append(line)
    return out


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: qmd_chunks.py <file.qmd>\n")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    # split("\n") preserves the exact line structure (a trailing "\n" yields a
    # trailing "" element). Re-joining with "\n" and NOT appending an extra
    # newline reconstructs that same structure exactly — appending one would
    # add a phantom trailing blank line not present in the source.
    lines = text.split("\n")
    out = extract(lines)
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
