#!/usr/bin/env python3
"""Research-wide gate: no hardcoded numbers in manuscript prose.

Every quantity in the body must be an inline `r` expression, because a literal
does not update when the analysis changes and is invisible to the render. This
scanner walks the prose of a Quarto manuscript -- everything outside fenced
chunks and outside inline `r ...` spans -- and flags every numeric literal that
remains.

Numbers that are legitimately literal (dates, docket numbers, a design's column
count, an institutional fact, a figure quoted from a cited paper) must be listed
in the project's allowlist CSV with a reason. An unexplained literal fails. The
point is not that literals are forbidden; it is that each one is a decision
somebody made on purpose and can defend.

SPELLED-OUT COUNTS. A digits-only scan has a hole: prose spells small cardinals
out, so "the ledger has three verdict classes" is a claim about an exhibit that
no check can see. It went stale exactly that way -- the ledger had five classes
and the sentence said three for as long as it took someone to read the CSV. So a
number WORD is scanned too, but only where it counts the structure of an exhibit
(rows, tests, classes, columns, cells, designs, exhibits, tables, figures).
Scanning every number word would flag "the one that does" and "two-agent" and
train the reader to skip the output, which is worse than not checking. Word hits
are allowlisted in the same CSV and by the same rule: give a reason or make it an
inline expression.

A project counts its own nouns, though — states, MSAs, outcomes, specifications —
and those counts go stale exactly like the shared ones. Declare them in the
project's CLAUDE.md beside the manuscript declaration:

    prose-number-nouns: states? msas? outcomes? specifications?

Separate them with whitespace, commas or `|`; each is a small regex, and they
EXTEND the shared list rather than replacing it. PROSE_NUMBER_NOUNS in the
environment overrides the declaration for a one-off run. Whatever is in effect is
printed with the result, because a gate scanning a narrower set than its reader
assumes is silently weaker than it looks.

PROVENANCE. Written for one project in 2026-09 and promoted here unchanged in
logic, with the manuscript and allowlist paths parameterized so any project can
use it.

WHY THIS SHIPS. The project it came from carried 24 hardcoded values in prose
while scoring 100/100 on its own quality gate — four of them provably wrong, each
contradicted by a table on the same page — because its scorer tested hardcoded
*paths* rather than *numbers*. A rule that lives only in prose is not enforced;
this file is the enforcement.

Usage
-----
    python3 .claude/scripts/prose_number_check.py MANUSCRIPT.qmd [ALLOWLIST.csv]

The allowlist defaults to quality_reports/prose_number_allowlist.csv at the
PROJECT root -- the nearest directory at or above the manuscript that carries a
.claude directory -- falling back to the manuscript's own directory outside a
project. Exit codes: 0 clean, 1 unexplained literals, 2 usage error.
"""
import re, csv, sys, os, collections


def project_root(qmd):
    """Nearest ancestor of the manuscript carrying a .claude directory.

    quality_reports/ is a PROJECT directory: pipeline_state.json,
    agent_dispatch.jsonl and reviews/ all resolve from the project root, and
    quarto-empirical.md calls this allowlist "per-project". Resolving it beside
    the MANUSCRIPT instead was wrong for any project that keeps its manuscript
    in a subdirectory -- one kept its allowlist in quality_reports/ while this
    scanner looked in paper/quality_reports/, found nothing, and reported all
    41 of its literals as unexplained.

    Falls back to the manuscript's own directory when nothing above it is a
    project, so the script still works on a loose .qmd.
    """
    here = os.path.dirname(os.path.abspath(qmd))
    d = here
    while True:
        if os.path.isdir(os.path.join(d, ".claude")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return here
        d = parent


FENCE = re.compile(r"^(`{3,})(.*?)\s*$")


class FenceError(Exception):
    """A code fence was opened and never closed; args[0] is its line number."""


def load_manuscript(qmd):
    """Split the manuscript into prose lines and caption strings, in one pass.

    Prose = outside fenced chunks, YAML front matter and HTML comments. HTML
    comments are excluded because they do not appear in the rendered document:
    a number inside one cannot make a false claim to a reader.

    Fences follow CommonMark: a fence closes only on a line of at least as many
    backticks with no info string. The old toggle-on-any-``` let a ```{r} line
    close a chunk and let a nested display block desynchronise the scan.

    An unclosed fence raises FenceError. Before, one stray fence silenced the rest
    of the file while the gate still exited on whatever came before it -- a
    partial scan that read as a complete one.
    """
    prose, captions = [], []
    fence, opened = None, 0
    in_yaml = in_comment = False
    for i, line in enumerate(open(qmd, encoding="utf-8"), 1):
        if fence is not None:
            m = FENCE.match(line)
            if m and len(m.group(1)) >= len(fence) and not m.group(2):
                fence = None
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        s = line.strip()
        if s.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        if i == 1 and s == "---":
            in_yaml = True
            continue
        if in_yaml:
            if s == "---":
                in_yaml = False
            continue
        m = FENCE.match(line)
        if m:
            fence, opened = m.group(1), i
            continue
        prose.append((i, line))
    if fence is not None:
        raise FenceError(opened)
    return prose, captions


def load_prose(qmd):
    """Prose lines only."""
    return load_manuscript(qmd)[0]


# `r expr` (knitr) and `{r} expr` (Quarto's native form). Matching only the first
# made the modern syntax a false positive: `{r} round(b, 3)` reported '3'.
INLINE = re.compile(r"`(?:r|\{r\})\s[^`]*`")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$", re.S)
# A literal ends on a digit, so "Table 4," and "Table 4." key as '4'. The old
# \d[\d,]* swallowed a trailing comma, so an allowlist needed a twin row ("4" and
# "4,") for every literal that ever preceded a comma.
NUM = re.compile(r"(?<![\w`])(\d(?:[\d,]*\d)?(?:\.\d+)?)")

# Spelled-out cardinals, but only when they count the structure of an exhibit.
# The noun list is the scope limiter -- see SPELLED-OUT COUNTS above.
_CARD = ("one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
         "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
         # Round tens: "Fifty MSAs that span state boundaries" is as much a count
         # off an exhibit as "twelve MSAs", and stopping at twenty missed it.
         # Verified against five manuscripts: adds nothing under the base nouns.
         "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred")
# Deliberately NARROW. Widening this is not free: adding "markets?" during the
# promotion immediately produced three false hits in one project's manuscript ("the two
# markets were moving in step") and would have trained a reader to skip the
# output. Extend it per project via PROSE_NUMBER_NOUNS in the environment, never
# by editing this shared default.
_NOUN = ("rows?|tests?|classes|class|columns?|cells?|designs?|exhibits?|"
         "tables?|figures?")

DECLARATION = re.compile(r"^prose-number-nouns:\s*(.+?)\s*$", re.M)


def extra_nouns(root):
    """The project's own countable nouns, and where they came from.

    PROSE_NUMBER_NOUNS in the environment is for a one-off run and wins. The
    durable setting is a `prose-number-nouns:` line in the project's CLAUDE.md,
    beside the `manuscript:` declaration it belongs with -- an environment
    variable is not per-project, it is per-invocation, and a gate whose answer
    depends on who ran it is not a gate.
    """
    env = os.environ.get("PROSE_NUMBER_NOUNS", "").strip()
    if env:
        return env, "PROSE_NUMBER_NOUNS"
    claude = os.path.join(root, "CLAUDE.md")
    if os.path.exists(claude):
        hits = DECLARATION.findall(open(claude, encoding="utf-8").read())
        if hits:
            return "|".join(hits), "CLAUDE.md"
    return "", ""


def wordnum(extra):
    """Compile the spelled-out-count scanner, extended by `extra`.

    The lookbehind keeps a cardinal buried inside a hyphenated compound out of
    it: in "leave-one-state-out" the "one" counts nothing, and with `states?`
    declared that method name would otherwise fire six times in one manuscript
    and train the reader to skip the output.
    """
    nouns = _NOUN + ("|" + "|".join(re.split(r"[|,\s]+", extra)) if extra else "")
    return re.compile(rf"(?<![-\w])({_CARD})[\s-]+({nouns})\b", re.I)


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(__doc__)
        return 2
    qmd = argv[1]
    if not os.path.exists(qmd):
        print(f"error: manuscript not found: {qmd}")
        return 2
    named = len(argv) == 3
    allow_path = argv[2] if named else os.path.join(
        project_root(qmd), "quality_reports", "prose_number_allowlist.csv")
    if named and not os.path.exists(allow_path):
        # A path someone typed is a typo, not an empty allowlist.
        print(f"error: allowlist not found: {allow_path}")
        return 2

    extra, source = extra_nouns(project_root(qmd))
    try:
        wordnum_rx = wordnum(extra)
    except re.error as e:
        print(f"error: prose-number-nouns from {source} is not a valid pattern: {e}")
        print(f"       {extra!r}")
        return 2
    note = f"  extra nouns: {extra}  (from {source})" if extra else ""

    allow = {}
    if os.path.exists(allow_path):
        for r in csv.DictReader(open(allow_path, encoding="utf-8")):
            allow.setdefault(r["literal"], r["reason"])

    try:
        prose, captions = load_manuscript(qmd)
    except FenceError as e:
        print(f"error: the code fence opened at line {e.args[0]} of {qmd} is never closed.")
        print("       Nothing after that line could be scanned, so no verdict is given.")
        return 2

    hits = collections.OrderedDict()
    for lineno, line in prose:
        clean = MATH.sub(" ", INLINE.sub(" ", line))
        for m in NUM.finditer(clean):
            ctx = clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(1), []).append((lineno, ctx))
        for m in wordnum_rx.finditer(clean):
            ctx = clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(0).lower(), []).append((lineno, ctx))

    unexplained = {k: v for k, v in hits.items() if k not in allow}
    stale = [k for k in allow if k not in hits]

    if unexplained:
        print("PROSE NUMBER CHECK FAILED —", len(unexplained), "unexplained literals")
        print(f"  manuscript: {qmd}")
        print(f"  allowlist:  {allow_path}")
        if note:
            print(note)
        if not os.path.exists(allow_path):
            # Distinguishing the two is the whole point. One project's 54
            # "unexplained literals" were all adjudicated, with written reasons,
            # in a file this scanner never opened because it was named something
            # else. Reporting a missing allowlist as a wall of unexplained
            # literals states a property that was never tested.
            print("  NOTE: that file does not exist. Every literal below is "
                  "unexplained because there is\n        nothing to explain it "
                  "in -- not because an allowlist was consulted and came up "
                  "short.\n        Create it with the header row "
                  "`literal,reason`.")
        print("  Make each an inline `r` expression, or add it to the allowlist "
              "with a reason.\n")
        for lit, occ in unexplained.items():
            print(f"  {lit!r}  ({len(occ)}x)  first at line {occ[0][0]}: ...{occ[0][1]}...")
        return 1

    print(f"Prose number check PASSED: {len(hits)} distinct literals, all allowlisted "
          f"with a reason; {sum(len(v) for v in hits.values())} occurrences.")
    # Name the file that was read. A green from an allowlist resolved somewhere
    # unexpected is the same defect as a red from one that was never found.
    print(f"  allowlist:  {allow_path}")
    if note:
        print(note)
    if stale:
        print("  note: allowlist entries no longer present in the prose:",
              ", ".join(sorted(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
