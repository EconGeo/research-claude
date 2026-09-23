#!/usr/bin/env python3
"""quarto_structure_check.py — enforce NATIVE Quarto structure (INV-25).

The number gate (prose_number_check.py, INV-11) asks whether every number in
prose came from code. This asks the structural twin: whether every exhibit
number and cross-reference comes from the RENDERER rather than from a human
retyping it.

Why it exists. A manuscript can pass the render, the quality score and the
number gate while its prose says "Table 4" about an exhibit the renderer numbers
7. One project shipped 158 typed table references, zero `@tbl-`, and a rendered exhibit
order of 1, 2, 3, 4C, 4D, 4, 5, 6, 7, 5C, 5D, 5E, 5B, 8..11, 4B -- ten positions
disagreeing with the number their own caption claimed. Nothing detected it: a
render cannot fail on a typed "Table 4", because typed text is valid prose, and
the number gate saw only digits it had been told to allow.

tested: on Quarto 1.9.37 / flextable 0.9.11, `#| label: tbl-x` + `#| tbl-cap:`
gives captions, auto-numbering and working `@tbl-` in docx. The
`knitr::opts_knit$set(quarto.version = 0)` workaround that blocks all three is
obsolete, and is checked for here.

Exit 0 = clean. Exit 1 = findings. Exit 2 = usage error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# A chunk's label may be brace-form ```{r label} or option-form #| label: x.
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
BRACE_LABEL_RE = re.compile(r"^\{[a-zA-Z0-9_]+[ ,]+([A-Za-z0-9._-]+)")
OPT_LABEL_RE = re.compile(r"^#\|\s*label:\s*['\"]?([A-Za-z0-9._-]+)")
OPT_CAP_RE = re.compile(r"^#\|\s*(tbl-cap|fig-cap):")
INLINE_RE = re.compile(r"`r\s.*?`|`\{r[^}]*\}[^`]*`", re.DOTALL)

# Captions set in R rather than in a chunk option: two sources of truth for one
# caption, and the R one wins or loses depending on a global knitr flag.
R_CAPTION_RE = re.compile(r"\bset_caption\s*\(|\bmake_ft\s*\([^)]*\bcaption\s*=|"
                          r"\bmodelsummary\s*\([^)]*\btitle\s*=|^\s*fig\.cap\s*=", re.M)
QUARTO_VERSION_HACK_RE = re.compile(r"opts_knit\s*\$\s*set\s*\(\s*quarto\.version")

# Typed exhibit / section references that should be @refs.
TYPED_REF_RE = re.compile(
    r"\b(?:Appendix\s+)?(Table|Figure|Section|Exhibit)\s+"
    r"(?:[A-Z]?\d+[A-Za-z]?)\b")
# "Panel A" names part of a table, not an exhibit — reported separately, never a failure.
PANEL_RE = re.compile(r"\bPanel\s+[A-Z]\b")


def zones(text: str):
    """Yield (kind, lineno, line) with kind in {'prose','chunk-header','code','yaml'}."""
    lines = text.splitlines()
    in_yaml = False
    in_chunk = False
    fence = ""
    header_zone = False
    for i, line in enumerate(lines, 1):
        if i == 1 and line.strip() == "---":
            in_yaml = True
            yield "yaml", i, line
            continue
        if in_yaml:
            yield "yaml", i, line
            if line.strip() == "---":
                in_yaml = False
            continue
        m = FENCE_RE.match(line)
        if m and not in_chunk and m.group(3).strip().startswith("{"):
            in_chunk, fence, header_zone = True, m.group(2), True
            yield "chunk-open", i, m.group(3).strip()
            continue
        if in_chunk:
            if m and m.group(2).startswith(fence[0]) and len(m.group(2)) >= len(fence) \
               and not m.group(3).strip():
                in_chunk, header_zone = False, False
                yield "chunk-close", i, line
                continue
            if header_zone and line.lstrip().startswith("#|"):
                yield "chunk-header", i, line
                continue
            header_zone = False
            yield "code", i, line
            continue
        yield "prose", i, line


def check(path: Path) -> list[tuple[str, int, str]]:
    text = path.read_text(encoding="utf-8")
    findings: list[tuple[str, int, str]] = []

    labels: dict[str, int] = {}          # label -> line
    label_kind: dict[str, str] = {}      # label -> 'tbl'|'fig'|'other'
    has_cap_opt: set[str] = set()
    cur_label: str | None = None
    code_lines: list[tuple[int, str]] = []
    prose_lines: list[tuple[int, str]] = []

    for kind, ln, line in zones(text):
        if kind == "chunk-open":
            cur_label = None
            m = BRACE_LABEL_RE.match(line)
            if m:
                cur_label = m.group(1)
        elif kind == "chunk-header":
            m = OPT_LABEL_RE.match(line.strip())
            if m:
                cur_label = m.group(1)
            if OPT_CAP_RE.match(line.strip()) and cur_label:
                has_cap_opt.add(cur_label)
        elif kind == "code":
            code_lines.append((ln, line))
            if cur_label and cur_label not in labels:
                labels[cur_label] = ln
        elif kind == "prose":
            prose_lines.append((ln, line))

    for lbl, ln in labels.items():
        label_kind[lbl] = ("tbl" if lbl.startswith(("tbl-", "apptbl-"))
                           else "fig" if lbl.startswith("fig-") else "other")

    # 1. The obsolete workaround.
    for ln, line in code_lines:
        if QUARTO_VERSION_HACK_RE.search(line):
            findings.append(("quarto-version-hack", ln,
                             "opts_knit$set(quarto.version = 0) disables native captions, "
                             "auto-numbering and @tbl- cross-references; it is obsolete on "
                             "Quarto >= 1.9 / flextable >= 0.9.11"))

    # 2. Captions set in R instead of a chunk option.
    for ln, line in code_lines:
        if R_CAPTION_RE.search(line):
            findings.append(("caption-in-r", ln,
                             "caption set in R; the caption belongs in #| tbl-cap: / #| fig-cap: "
                             "so the renderer owns the number: " + line.strip()[:70]))

    # 3. Non-native chunk labels for exhibits.
    for lbl, ln in labels.items():
        if lbl.startswith(("tab-", "table-")):
            findings.append(("label-prefix", ln,
                             f"chunk label '{lbl}' is not a Quarto crossref target; "
                             f"use 'tbl-' (or 'apptbl-' with a custom float)"))

    # 4. Typed exhibit and section references in prose.
    prose_typed = 0
    for ln, line in prose_lines:
        bare = INLINE_RE.sub(" ", line)
        for m in TYPED_REF_RE.finditer(bare):
            prose_typed += 1
            findings.append(("typed-ref", ln,
                             f"typed '{m.group(0)}' in prose; use a @tbl-/@fig-/@sec- "
                             f"reference so the number comes from the renderer"))

    # 5. Exhibit labels nothing references (the orphan-figure class).
    body = "\n".join(l for _, l in prose_lines)
    for lbl, ln in labels.items():
        if label_kind[lbl] in ("tbl", "fig") and f"@{lbl}" not in body:
            findings.append(("orphan-label", ln,
                             f"'{lbl}' is labelled but never referenced; it will render with a "
                             f"number no text points at"))

    # 6. A reference with no matching label.
    for ln, line in prose_lines:
        # A trailing '.' or '-' is sentence punctuation, not part of the label:
        # "@apptbl-second." must not be read as the label 'apptbl-second.'.
        for m in re.finditer(r"@((?:tbl|fig|sec|apptbl)-[A-Za-z0-9._-]*[A-Za-z0-9_])", line):
            if m.group(1) not in labels and f"{{#{m.group(1)}}}" not in text:
                findings.append(("dangling-ref", ln,
                                 f"@{m.group(1)} has no matching label or anchor"))

    # 7. Unresolved crossrefs left in a rendered artifact.
    for ext in (".docx", ".pdf", ".html"):
        art = path.with_suffix(ext)
        if art.exists() and ext == ".html":
            if "?@" in art.read_text(encoding="utf-8", errors="ignore"):
                findings.append(("unresolved-render", 0,
                                 f"{art.name} contains '?@' — an unresolved cross-reference"))

    findings.sort(key=lambda f: (f[1], f[0]))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("manuscript", type=Path)
    ap.add_argument("--summary", action="store_true",
                    help="counts per finding kind only")
    a = ap.parse_args()
    if not a.manuscript.is_file():
        print(f"error: no such file: {a.manuscript}", file=sys.stderr)
        return 2

    findings = check(a.manuscript)
    if not findings:
        print(f"quarto_structure_check: PASS ({a.manuscript.name} is native Quarto)")
        return 0

    kinds: dict[str, int] = {}
    for k, _, _ in findings:
        kinds[k] = kinds.get(k, 0) + 1
    if not a.summary:
        for k, ln, msg in findings:
            print(f"{a.manuscript}:{ln}: [{k}] {msg}")
    print(f"\nquarto_structure_check: FAIL — {len(findings)} finding(s)")
    for k in sorted(kinds, key=lambda x: -kinds[x]):
        print(f"  {kinds[k]:5d}  {k}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
