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

FENCES. A backtick fence follows CommonMark's rule, not "any line of triple
backticks": opener and closer may be indented up to three spaces, and a fence
closes only on a line with at least as many backticks and no info string. The old
toggle-on-any-``` let a nested display block, or a ```{r} closer, desynchronise the
scan. Tilde (~~~) fences are not handled. An unclosed fence, or an unclosed HTML
comment, is exit 2 -- nothing after that line was scanned, so printing a verdict
would state a property that was never tested.

CAPTIONS. A caption renders on the page exactly like prose, so a hardcoded number
in one is the same defect as a typed literal in a paragraph. Only three
constructs are read, and only inside an executable chunk (an opener whose info
string starts with `{`): a fence-line `fig.cap=`/`tbl.cap=` option, a `#|
fig-cap:`/`tbl-cap:`/`*-subcap:` option line (not one computed with `!expr`), and
-- in an R chunk only -- a `caption=`/`title=` string literal. A display fence
(bare ``` , ```r, ````markdown, or Quarto's unexecuted ```{{r}}) is not
executable and yields no captions. Known limits, not read: a multi-line YAML
caption (`#| fig-cap: |`); a YAML list-form `#| fig-subcap:`, whose items sit on
the `#|   - "..."` lines below it; and a table note passed as `notes =` (as
modelsummary takes it), which renders under the table but is not a caption.

SIGN GLUE. A `+`, `-` or minus sign typed immediately before an inline expression
is not a literal to explain, it is a bug: the value already carries its own sign,
so a typed "+" ahead of a negative estimate prints "+-0.634". Exit 1, and not
allowlistable -- there is no reason that makes a doubled sign right. An exponent
is the same case: 10^{-`r k`} is written 10^{`r -k`}. The range idioms
`` `r a`--`r b` `` and `` `r a`-`r b` ``, and a compound like `pre-`r y``, are
spared.

VERDICT WORDS. A typed word describing a result -- "significant", "outperforms",
"rises" -- can go stale exactly like a typed number when the value beside it is
`r`-live and the word is not. Counted per sentence and advisory by default, so a
manuscript already carrying dozens is not red on day one; `prose-verdict-ceiling:
N` in the project's CLAUDE.md makes a count above N fail, and
`prose-verdict-words:` extends the lexicon the same way `prose-number-nouns:`
extends the noun list.

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
project. Exit codes: 0 clean, 1 unexplained literals (also a glued sign, or a
verdict-word count over a declared ceiling), 2 usage error, an unclosed fence or
HTML comment, or a bad declaration: an invalid prose-verdict-words or
prose-number-nouns pattern, or a prose-verdict-ceiling that is not a
non-negative integer or is declared more than once.
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


# Up to three spaces of indent, as CommonMark allows on an opener and a closer
# (and knitr on a chunk's end). Four or more is an indented code line, not a fence.
FENCE = re.compile(r"^ {0,3}(`{3,})(.*?)\s*$")


class Unclosed(Exception):
    """A block opened at line args[0] and never closed: nothing after it was scanned."""
    what = "block"


class FenceError(Unclosed):
    """A code fence was opened and never closed; args[0] is its line number."""
    what = "code fence"


class CommentError(Unclosed):
    """An HTML comment was opened and never closed; args[0] is its line number."""
    what = "HTML comment"


# Caption text is prose the reader sees, by the same logic that excludes HTML
# comments: the test is whether it reaches the rendered page. Three places carry
# it: a fence-line option, a #| option line, and an R string passed as caption=
# or title= (flextable, modelsummary, gt, labs). Only those string literals are
# admitted -- scanning every R string would re-import the code noise that
# excluding chunks exists to avoid.
# Known limits, not read: a multi-line YAML caption (#| fig-cap: |), a YAML
# list-form #| fig-subcap: (items on the lines below), and a table note passed
# as notes = (modelsummary).
#
# SCOPE (controller ruling): captions are read only inside an EXECUTABLE chunk
# -- the opener's info string starts with `{` (`{r}`, `{python}`, ...), never a
# display fence (bare ```, ```r, ````markdown, ```{{r}}). Within an executable chunk,
# FENCE_CAP (the opener option) and OPT_CAP (a #| option line) apply for any
# engine; R_CAP (a caption= or title= R string) applies only when the engine is
# r, since that is R-specific call syntax, not something a python/bash chunk's
# own strings should be read as. A chunk that only *looks* executable because
# it is nested inside a display fence is not: its lines belong to the outer
# fence, which never opened as executable.
FENCE_CAP = re.compile(r"""\b(?:fig|tbl)[.-]cap\s*=\s*(["'])(.*?)(?<!\\)\1""")
OPT_CAP = re.compile(r"^#\|\s*(?:fig|tbl)-(?:cap|subcap)\s*:\s*(.+?)\s*$")
R_CAP = re.compile(r"""\b(?:caption|title)\s*=\s*(["'])(.*?)(?<!\\)\1""")
ENGINE_R = re.compile(r"^\{r[\s,}]")


def fence_engine(info):
    """(is_executable, is_r) for a fence's info string.

    `is_executable` is whether the (left-stripped) info string starts with
    `{`. `is_r` narrows that to the r engine specifically -- `{r}`, `{r
    fig-top, ...}`, `{r,...}` -- so a `{python}`/`{bash}`/... chunk is
    executable but not r. A double brace (`{{r}}`) is Quarto's syntax for a
    chunk DISPLAYED unexecuted, so its option lines never become captions.
    """
    info = info.lstrip()
    if not info.startswith("{") or info.startswith("{{"):
        return False, False
    return True, bool(ENGINE_R.match(info))


def chunk_captions(lineno, line, r_engine):
    """Reader-visible caption text on one line inside an executable chunk."""
    s = line.strip()
    m = OPT_CAP.match(s)
    if m:
        value = m.group(1)
        if value.startswith("!expr"):
            return []      # computed in R: no typed literal to find
        return [(lineno, value.strip("\"'"))]
    if s.startswith("#"):
        return []          # an R comment, or a chunk option that is not a caption
    if not r_engine:
        return []          # caption= and title= are R call syntax, not read in other engines
    return [(lineno, c.group(2)) for c in R_CAP.finditer(line)]


def load_manuscript(qmd):
    """Split the manuscript into prose lines and caption strings, in one pass.

    Prose = outside fenced chunks, YAML front matter and HTML comments. HTML
    comments are excluded because they do not appear in the rendered document:
    a number inside one cannot make a false claim to a reader.

    Captions are the reader-visible exception carved back out of the chunks
    prose otherwise skips: a fence-line `fig.cap=`/`tbl.cap=` option, a `#|`
    chunk-option caption line, and an R string passed as `caption=` or
    `title=`. All of that text renders on the page exactly like prose does, so
    a hardcoded number in it is the same defect as one typed in a paragraph.

    Backtick fences follow CommonMark's closing rule: indented 0-3 spaces, a
    fence closes only on a line of at least as many backticks with no info
    string. The old toggle-on-any-``` let a ```{r} line close a chunk and let a
    nested display block desynchronise the scan. Tilde (~~~) fences are not
    handled.

    An unclosed fence raises FenceError, and an unclosed HTML comment
    CommentError. Before, one stray opener silenced the rest of the file while
    the gate still exited on whatever came before it -- a partial scan that
    read as a complete one.
    """
    prose, captions = [], []
    fence, opened = None, 0
    fence_exec = fence_r = False
    in_yaml = in_comment = False
    comment_at = 0
    for i, line in enumerate(open(qmd, encoding="utf-8"), 1):
        if fence is not None:
            m = FENCE.match(line)
            if m and len(m.group(1)) >= len(fence) and not m.group(2):
                fence = None
            elif fence_exec:
                captions.extend(chunk_captions(i, line, fence_r))
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        s = line.strip()
        if s.startswith("<!--"):
            if "-->" not in line:
                in_comment, comment_at = True, i
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
            fence_exec, fence_r = fence_engine(m.group(2))
            if fence_exec:
                captions.extend((i, c.group(2)) for c in FENCE_CAP.finditer(m.group(2)))
            continue
        prose.append((i, line))
    if fence is not None:
        raise FenceError(opened)
    if in_comment:
        raise CommentError(comment_at)
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

# A sign typed against an inline value. The value carries its own sign, so a
# typed "+" before a negative estimate prints "+-0.634", and the typed sign is
# outside the literal alphabet in both directions. Not allowlistable: there is
# no reason that makes it right. Keep the sign in the expression
# (sprintf("%+.3f", x)). The lookbehind spares the range idioms `r a`--`r b` and
# `r a`-`r b` and compounds like pre-`r y`.
SIGN_GLUE = re.compile(r"(?<![-\w`])[+−-](?=`(?:r|\{r\})\s)")

# Typed verdicts beside a live number. A number can update while the word beside
# it cannot: "outperform (coefficient = -0.634)" is the shipped form of this bug.
# Counted, not failed, unless the project declares a ceiling, because existing
# manuscripts carry dozens and a gate that is red on day one gets waived. A
# ceiling that must not rise is enforceable. The fix is a helper that derives
# the word from the value.
_VERDICT = (r"significant|significantly|insignificant|"
            r"outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|"
            r"positive|negative|rises|rose|falls|fell|"
            r"monotonic(?:ally)?|stronger|weaker|null")
LIVE = "\x00"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def declared(root, key):
    """The values of every `key: value` line in the project's CLAUDE.md, as a list.

    The one CLAUDE.md reader. `[ \\t]*`, not `\\s*`, after the colon: `\\s` crosses
    a newline, so an empty `prose-verdict-ceiling:` line used to take the NEXT
    line as its value. An empty value is treated as absent.
    """
    claude = os.path.join(root, "CLAUDE.md")
    if not os.path.exists(claude):
        return []
    rx = re.compile(rf"^{re.escape(key)}:[ \t]*(.*)$", re.M)
    values = (v.strip() for v in rx.findall(open(claude, encoding="utf-8").read()))
    return [v for v in values if v]


def tokens(extra):
    """Split a declaration on whitespace, commas or `|`, dropping empty tokens.

    An empty token would become an empty regex alternative, which matches at
    every word boundary: `lag,` made every live sentence count, and `states,`
    made "the two markets" a count.
    """
    return [t for t in re.split(r"[|,\s]+", extra) if t]


def verdict_rx(extra):
    words = "|".join([_VERDICT, *tokens(extra)])
    return re.compile(rf"\b(?:{words})\b", re.I)


def paragraphs(prose):
    """Consecutive prose lines joined into paragraphs, with the first line number."""
    para, start, prev = [], 0, None
    for lineno, line in prose:
        s = line.strip()
        broken = prev is not None and lineno != prev + 1
        prev = lineno
        if broken or not s or s.startswith(("#", ":::")):
            if para:
                yield start, " ".join(para)
            para = []
            if not s or s.startswith(("#", ":::")):
                continue
        if not para:
            start = lineno
        para.append(s)
    if para:
        yield start, " ".join(para)


def verdict_hits(prose, rx):
    out = []
    for start, text in paragraphs(prose):
        for sentence in SENTENCE_END.split(INLINE.sub(LIVE, text)):
            if LIVE in sentence:
                shown = sentence.replace(LIVE, "`r …`")[:160]
                out.extend((start, m.group(0).lower(), shown) for m in rx.finditer(sentence))
    return out


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
    hits = declared(root, "prose-number-nouns")
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
    nouns = "|".join([_NOUN, *tokens(extra)])
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
    root = project_root(qmd)
    allow_path = argv[2] if named else os.path.join(
        root, "quality_reports", "prose_number_allowlist.csv")
    if named and not os.path.exists(allow_path):
        # A path someone typed is a typo, not an empty allowlist.
        print(f"error: allowlist not found: {allow_path}")
        return 2

    extra, source = extra_nouns(root)
    try:
        wordnum_rx = wordnum(extra)
    except re.error as e:
        print(f"error: prose-number-nouns from {source} is not a valid pattern: {e}")
        print(f"       {extra!r}")
        return 2
    note = f"  extra nouns: {extra}  (from {source})" if extra else ""

    try:
        v_rx = verdict_rx("|".join(declared(root, "prose-verdict-words")))
    except re.error as e:
        print(f"error: prose-verdict-words in CLAUDE.md is not a valid pattern: {e}")
        return 2
    ceilings = declared(root, "prose-verdict-ceiling")
    if len(ceilings) > 1:
        print("error: prose-verdict-ceiling is declared more than once in CLAUDE.md "
              f"({', '.join(ceilings)}); keep one line.")
        return 2
    ceiling = None
    if ceilings:
        try:
            ceiling = int(ceilings[0])
        except ValueError:
            ceiling = -1
        if ceiling < 0:
            print("error: prose-verdict-ceiling must be a non-negative integer, "
                  f"got {ceilings[0]!r}")
            return 2

    # A key keeps no trailing comma: NUM ends a literal on a digit, so "1999,"
    # could never match, and its bare twin made it look stale. Normalise it and
    # say so, so the file gets cleaned rather than silently reinterpreted.
    allow, comma_keys = {}, []
    if os.path.exists(allow_path):
        for r in csv.DictReader(open(allow_path, encoding="utf-8")):
            key = r["literal"]
            if key.endswith(","):
                comma_keys.append(key)
            allow.setdefault(key.rstrip(","), r["reason"])
    if comma_keys:
        note += ("\n" if note else "") + (
            "  note: allowlist keys with a trailing comma: "
            + ", ".join(repr(k) for k in comma_keys)
            + "\n        A key now matches the bare literal; rename each to the "
              "bare literal or delete the twin.")

    try:
        prose, captions = load_manuscript(qmd)
    except Unclosed as e:
        print(f"error: the {e.what} opened at line {e.args[0]} of {qmd} is never closed.")
        print("       Nothing after that line could be scanned, so no verdict is given.")
        return 2

    hits = collections.OrderedDict()

    def scan(lineno, text, label):
        clean = MATH.sub(" ", INLINE.sub(" ", text))
        for m in NUM.finditer(clean):
            ctx = label + clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(1), []).append((lineno, ctx))
        for m in wordnum_rx.finditer(clean):
            ctx = label + clean[max(0, m.start() - 55):m.end() + 55].strip().replace("\n", " ")
            hits.setdefault(m.group(0).lower(), []).append((lineno, ctx))

    glued = []
    for lineno, line in prose:
        for m in SIGN_GLUE.finditer(line):
            glued.append((lineno, line[max(0, m.start() - 55):m.end() + 55].strip()))
        scan(lineno, line, "")
    for lineno, text in captions:
        scan(lineno, text, "caption: ")

    verdicts = verdict_hits(prose, v_rx)
    over = ceiling is not None and len(verdicts) > ceiling

    unexplained = {k: v for k, v in hits.items() if k not in allow}
    stale = [k for k in allow if k not in hits]

    failed = bool(glued) or bool(unexplained) or over
    mode = f"ceiling {ceiling}" if ceiling is not None else \
        "advisory; declare prose-verdict-ceiling: N in CLAUDE.md to enforce"

    def verdict_count():
        print(f"  verdict words beside live values: {len(verdicts)}  ({mode})")
        if ceiling is not None and len(verdicts) < ceiling:
            print(f"  note: lower prose-verdict-ceiling to {len(verdicts)}")

    if not failed:
        # The headline first: a reader who stops at line one must get the verdict.
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
        verdict_count()
        return 0

    why = []
    if unexplained:
        why.append(f"{len(unexplained)} unexplained literals")
    if glued:
        why.append(f"{len(glued)} signs typed beside a live value")
    if over:
        why.append(f"{len(verdicts)} verdict words over a ceiling of {ceiling}")
    print("PROSE NUMBER CHECK FAILED —", "; ".join(why))
    print(f"  manuscript: {qmd}")
    print(f"  allowlist:  {allow_path}")
    if note:
        print(note)
    if unexplained and not os.path.exists(allow_path):
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
    print()

    if glued:
        print("SIGN TYPED BESIDE A LIVE VALUE —", len(glued), "sites (not allowlistable)")
        print("  The value carries its own sign; put any forced sign inside the "
              "expression, e.g. sprintf('%+.3f', x).\n"
              "  An exponent is the same case: write 10^{`r -k`}, not 10^{-`r k`}.\n")
        for lineno, ctx in glued:
            print(f"  line {lineno}: ...{ctx}...")
        print()

    if unexplained:
        print("UNEXPLAINED LITERALS —", len(unexplained))
        print("  Make each an inline `r` expression, or add it to the allowlist "
              "with a reason.\n")
        for lit, occ in unexplained.items():
            print(f"  {lit!r}  ({len(occ)}x)  first at line {occ[0][0]}: ...{occ[0][1]}...")
        print()

    if over:
        print("VERDICT WORDS ABOVE CEILING —", len(verdicts), ">", ceiling)
        for lineno, word, sentence in verdicts:
            print(f"  line {lineno}: {word} — {sentence}")
        print()

    verdict_count()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
