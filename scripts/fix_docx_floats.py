#!/usr/bin/env python3
"""Repair two schema defects in Quarto's docx float output so Word opens it cleanly.

Run by Quarto as a `post-render` step: the project's `_quarto.yml` (seeded by apply.sh from
seeds/_quarto.yml) names `.claude/scripts/fix_docx_floats.py`. It rewrites each rendered
.docx in place. Without it Word reports "unreadable content" and offers to recover.

Quarto (1.9) wraps every cross-referenced float in a one-cell layout table. Two
defects in that wrapper break the WordprocessingML schema:

1. When the float holds a flextable, the wrapper cell ends with the inner <w:tbl>.
   A <w:tc> must end with a <w:p>, so an empty paragraph is appended.
2. The caption paragraph carries two <w:pPr> blocks: pandoc's own (the cell's
   centre alignment) followed by Quarto's raw caption pPr (ImageCaption style,
   left, spacing). Only the last is kept, as Word would render it, with
   <w:pStyle> moved to first position as the schema requires.

Verified 2026-10-04 in Word: a docx with both repairs opens in Word without the prompt;
either repair alone does not. Idempotent: a repaired file passes through unchanged.
"""
import os
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOC = "word/document.xml"


def repair(root):
    """Apply both repairs to the document tree; return (cells fixed, paragraphs fixed)."""
    n_cells = 0
    for tc in root.iter(W + "tc"):
        blocks = [k for k in tc if k.tag in (W + "p", W + "tbl")]
        if blocks and blocks[-1].tag == W + "tbl":
            tc.append(etree.Element(W + "p"))
            n_cells += 1
    n_paras = 0
    for p in root.iter(W + "p"):
        pprs = p.findall(W + "pPr")
        if len(pprs) > 1:
            for extra in pprs[:-1]:
                p.remove(extra)
            kept = pprs[-1]
            style = kept.find(W + "pStyle")
            if style is not None and kept[0] is not style:
                kept.remove(style)
                kept.insert(0, style)
            n_paras += 1
    return n_cells, n_paras


def fix_docx(path):
    path = Path(path)
    with zipfile.ZipFile(path) as zin:
        root = etree.fromstring(zin.read(DOC))
        n_cells, n_paras = repair(root)
        if not (n_cells or n_paras):
            print(f"fix_docx_floats: {path.name} already clean")
            return
        tmp = path.with_name(path.name + ".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == DOC:
                    data = etree.tostring(root, xml_declaration=True,
                                          encoding="UTF-8", standalone=True)
                zout.writestr(info, data)
    tmp.replace(path)
    print(f"fix_docx_floats: {path.name}: {n_cells} table cells, {n_paras} captions repaired")


def main(argv):
    # Explicit paths win; otherwise the files Quarto just rendered.
    targets = argv or os.environ.get("QUARTO_PROJECT_OUTPUT_FILES", "").split("\n")
    for t in targets:
        if t.strip().endswith(".docx"):
            fix_docx(t.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
