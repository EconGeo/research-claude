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
(rows, tests, classes, columns, cells, designs, exhibits, tables, figures,
markets). Scanning every number word would flag "the one that does" and
"two-agent" and train the reader to skip the output, which is worse than not
checking. Word hits are allowlisted in the same CSV and by the same rule: give a
reason or make it an inline expression.

PROVENANCE. Written for a settlement-study project (quality_reports/w_prose_number_check.py,
2026-09-05) and promoted here unchanged in logic, with the manuscript and
allowlist paths parameterized so every project under ~/Research can use it. The
project-local copy remains the reference implementation.

WHY THIS IS RESEARCH-WIDE. One project carried 24 hardcoded values in prose while
scoring 100/100 on its own quality gate, four of them provably wrong and each
contradicted by a table on the same page, because that project had no equivalent
check and its scorer tested hardcoded *paths* rather than *numbers*. A rule that
lives only in prose is not enforced; this file is the enforcement.

Usage
-----
    python3 ~/Research/scripts/prose_number_check.py MANUSCRIPT.qmd [ALLOWLIST.csv]

The allowlist defaults to quality_reports/prose_number_allowlist.csv relative to
the manuscript. Exit codes: 0 clean, 1 unexplained literals, 2 usage error.
"""
import re, csv, sys, os, collections


def load_prose(qmd):
    """Prose = outside fenced chunks, YAML front matter, and HTML comments.

    HTML comments are excluded because they do not appear in the rendered
    document: a number inside one cannot make a false claim to a reader, and
    scanning them buries the real hits under build notes (one project documents its
    QCEW field codes -- own_code=5, agglvl=73 -- that way).
    """
    lines, in_chunk, in_yaml, in_comment = [], False, False, False
    for i, line in enumerate(open(qmd, encoding="utf-8"), 1):
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        stripped_line = line.strip()
        if stripped_line.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        if i == 1 and line.strip() == "---":
            in_yaml = True
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            continue
        if line.startswith("```"):
            in_chunk = not in_chunk
            continue
        if not in_chunk:
            lines.append((i, line))
    return lines


INLINE = re.compile(r"`r [^`]*`")
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$", re.S)
NUM = re.compile(r"(?<![\w`])(\d[\d,]*(?:\.\d+)?)")

# Spelled-out cardinals, but only when they count the structure of an exhibit.
# The noun list is the scope limiter -- see SPELLED-OUT COUNTS above.
_CARD = ("one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
         "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty")
# Deliberately NARROW. Widening this is not free: adding "markets?" during the
# promotion immediately produced three false hits in one project's manuscript ("the two
# markets were moving in step") and would have trained a reader to skip the
# output. Extend it per project via PROSE_NUMBER_NOUNS in the environment, never
# by editing this shared default.
_NOUN = ("rows?|tests?|classes|class|columns?|cells?|designs?|exhibits?|"
         "tables?|figures?")
_EXTRA = os.environ.get("PROSE_NUMBER_NOUNS", "").strip()
if _EXTRA:
    _NOUN = _NOUN + "|" + _EXTRA
WORDNUM = re.compile(rf"\b({_CARD})[\s-]+({_NOUN})\b", re.I)


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(__doc__)
        return 2
    qmd = argv[1]
    if not os.path.exists(qmd):
        print(f"error: manuscript not found: {qmd}")
        return 2
    allow_path = argv[2] if len(argv) == 3 else os.path.join(
        os.path.dirname(os.path.abspath(qmd)),
        "quality_reports", "prose_number_allowlist.csv")

    allow = {}
    if os.path.exists(allow_path):
        for r in csv.DictReader(open(allow_path, encoding="utf-8")):
            allow.setdefault(r["literal"], r["reason"])

    hits = collections.OrderedDict()
    for lineno, line in load_prose(qmd):
        clean = MATH.sub(" ", INLINE.sub(" ", line))
        for m in NUM.finditer(clean):
            ctx = clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(1), []).append((lineno, ctx))
        for m in WORDNUM.finditer(clean):
            ctx = clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(0).lower(), []).append((lineno, ctx))

    unexplained = {k: v for k, v in hits.items() if k not in allow}
    stale = [k for k in allow if k not in hits]

    if unexplained:
        print("PROSE NUMBER CHECK FAILED —", len(unexplained), "unexplained literals")
        print(f"  manuscript: {qmd}")
        print(f"  allowlist:  {allow_path}")
        print("  Make each an inline `r` expression, or add it to the allowlist "
              "with a reason.\n")
        for lit, occ in unexplained.items():
            print(f"  {lit!r}  ({len(occ)}x)  first at line {occ[0][0]}: ...{occ[0][1]}...")
        return 1

    print(f"Prose number check PASSED: {len(hits)} distinct literals, all allowlisted "
          f"with a reason; {sum(len(v) for v in hits.values())} occurrences.")
    if stale:
        print("  note: allowlist entries no longer present in the prose:",
              ", ".join(sorted(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
