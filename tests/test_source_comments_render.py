"""Renders of the source-comments feature: the Lua filter, the seed wiring and `pipeline.py sources docx`.

Each render is slow, so setUpClass builds one tiny fixture project and renders it once per output;
the tests only read the files those renders left behind.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_TOOLS = shutil.which("quarto") is not None and shutil.which("pdftotext") is not None

SOURCE_TEXT = (
    "Intro line.\n\n"
    "Before the sentence. The Firm shall disclose the fee in writing. After it.\n\n"
    "Closing line.\n"
)
SENTENCE = "The Firm shall disclose the fee in writing."
OK_CLAIM = "Paper wording of the disclosure rule."
BAD_CLAIM = "A claim the source does not support."
MANUSCRIPT = f"""---
title: Fixture
format:
  docx: default
  pdf: default
---

Opening text. [{OK_CLAIM}]{{.src ref="ok" id="c1"}} Middle text.
[{BAD_CLAIM}]{{.src ref="bad" id="c2"}} Closing text.
"""
REGISTRY_ROWS = [
    {"id": "ok", "file": "sources/a.txt", "label": "Lbl", "page": "3", "sentence": SENTENCE,
     "cleanup": "", "ocr": "FALSE"},
    {"id": "bad", "file": "sources/a.txt", "label": "Lbl", "page": "3",
     "sentence": "This sentence is absent from the file.", "cleanup": "", "ocr": "FALSE"},
]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def make_project(root, scripts_link=True):
    """A paper project: the seed _quarto.yml, CLAUDE.md, manuscript, one source, the registry."""
    shutil.copy(ROOT / "seeds" / "_quarto.yml", root / "_quarto.yml")
    (root / "CLAUDE.md").write_text("manuscript: paper.qmd\n")
    (root / "paper.qmd").write_text(MANUSCRIPT)
    (root / "sources").mkdir()
    (root / "sources" / "a.txt").write_text(SOURCE_TEXT)
    (root / "quality_reports").mkdir()
    with open(root / "quality_reports" / "sources.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(REGISTRY_ROWS[0]))
        writer.writeheader()
        writer.writerows(REGISTRY_ROWS)
    (root / ".claude").mkdir()
    if scripts_link:
        (root / ".claude" / "scripts").symlink_to(ROOT / "scripts")


def make_fake_check_project(root, check_output):
    """A project whose source_check.py is replaced by one that prints check_output."""
    make_project(root, scripts_link=False)
    scripts = root / ".claude" / "scripts"
    scripts.mkdir()
    for name in ("source_comments.lua", "fix_docx_floats.py"):
        (scripts / name).symlink_to(ROOT / "scripts" / name)
    fake = "import sys\nsys.stdout.write(" + repr(check_output) + ")\n"
    (scripts / "source_check.py").write_text(fake)


def quarto(root, *args):
    return subprocess.run(["quarto", "render", "paper.qmd", *args], cwd=root,
                          capture_output=True, text=True)


def docx_part(path, part):
    with zipfile.ZipFile(path) as zf:
        return zf.read(part).decode("utf-8")


def comments(path):
    """Each Word comment as (author, plain text, raw XML)."""
    xml = docx_part(path, "word/comments.xml")
    found = []
    for match in re.finditer(r"<w:comment [^>]*>.*?</w:comment>", xml, re.S):
        raw = match.group(0)
        author = re.search(r'w:author="([^"]*)"', raw).group(1)
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", raw))
        found.append((author, text, raw))
    return found


def document_text(path):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", docx_part(path, "word/document.xml")))


@unittest.skipUnless(HAVE_TOOLS, "quarto or pdftotext missing")
class SourceCommentsRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.root = base / "paper"
        cls.root.mkdir()
        make_project(cls.root)

        cls.plain = quarto(cls.root, "--to", "docx")
        cls.plain_docx = cls.root / "paper.docx"
        cls.plain_mtime = cls.plain_docx.stat().st_mtime_ns if cls.plain_docx.exists() else None
        time.sleep(1.1)  # so a rewrite of the plain .docx would show in its mtime
        cls.sourced = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pipeline.py"), "--root", str(cls.root),
             "sources", "docx"], capture_output=True, text=True)
        cls.sourced_docx = cls.root / "paper_sourced.docx"

        cls.pdf = quarto(cls.root, "--to", "pdf")
        cls.pdf_file = cls.root / "paper.pdf"

        cls.broken_root = base / "broken"
        cls.broken_root.mkdir()
        make_fake_check_project(cls.broken_root, "source-check: internal error: boom\n")
        cls.broken = quarto(cls.broken_root, "--to", "docx", "-M", "source-comments:true",
                            "--output", "paper_sourced.docx")

        cls.partial_root = base / "partial"
        cls.partial_root.mkdir()
        partial_json = ('{"c1": {"state": "UNREVIEWED", "label": "Lbl", "page": "3", "ocr": true,'
                        ' "paragraph": "Text [' + SENTENCE + ']{.underline} more.", "reason": "x"},'
                        ' "design": {"state": "APPROVED", "label": "Act", "page": "9", "ocr": false,'
                        ' "paragraph": "The [treatment quote]{.underline} here.", "reason": ""}}')
        make_fake_check_project(cls.partial_root, partial_json)
        with open(cls.partial_root / "paper.qmd", "a") as fh:
            fh.write("\nThe [treatment definition]{.src-design} is stated here.\n")
        cls.partial = quarto(cls.partial_root, "--to", "docx", "-M", "source-comments:true",
                             "--output", "paper_sourced.docx")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def comment_for(self, path, marker):
        hits = [c for c in comments(path) if marker in c[1]]
        self.assertEqual(len(hits), 1, f"comments: {[c[1] for c in comments(path)]}")
        return hits[0]

    def test_sourced_docx_has_comment(self):
        self.assertEqual(self.sourced.returncode, 0, self.sourced.stdout + self.sourced.stderr)
        self.assertTrue(self.sourced_docx.exists())
        author, text, raw = self.comment_for(self.sourced_docx, "Lbl, p. 3.")
        self.assertEqual(author, "Source check")
        self.assertIn("UNREVIEWED: ", text)
        self.assertIn("Before the sentence. " + SENTENCE + " After it.", text)
        underlined = re.findall(r"<w:r>(?:(?!</w:r>).)*<w:u w:val=\"single\" />(?:(?!</w:r>).)*</w:r>",
                                raw, re.S)
        underlined_text = "".join("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r)) for r in underlined)
        self.assertEqual(underlined_text, SENTENCE)
        body = docx_part(self.sourced_docx, "word/document.xml")
        self.assertRegex(body, r"commentRangeStart w:id=\"(\d+)\".*" + re.escape(OK_CLAIM)
                         + r".*commentRangeEnd w:id=\"\1\"")

    def test_sourced_build_prints_warnings_and_path(self):
        out = self.sourced.stdout
        self.assertIn("source-check: FAILED c2 (bad)", out)
        self.assertIn("source-check: 1 claims not yet reviewed", out)
        self.assertEqual(out.strip().splitlines()[-1], str(self.sourced_docx.resolve()))

    def test_failed_claim_comment_has_no_source_text(self):
        author, text, _ = self.comment_for(self.sourced_docx, "SOURCE CHECK")
        self.assertEqual(author, "Source check")
        self.assertTrue(text.startswith("SOURCE CHECK FAILED"), text)
        for source_words in ("Intro line", "Before the sentence", "shall disclose", "After it",
                             "Closing line"):
            self.assertNotIn(source_words, text)
        self.assertIn(BAD_CLAIM, document_text(self.sourced_docx))

    def test_plain_docx_unchanged(self):
        # Pandoc always writes word/comments.xml (empty for a document without comments; tested
        # 2026-10-26, pandoc 3.8.3), so "no comments" means no <w:comment> element in it.
        self.assertEqual(self.plain.returncode, 0, self.plain.stderr)
        self.assertEqual(comments(self.plain_docx), [])
        body = docx_part(self.plain_docx, "word/document.xml")
        self.assertNotIn("commentRangeStart", body)
        text = document_text(self.plain_docx)
        self.assertIn(OK_CLAIM, text)
        self.assertIn(BAD_CLAIM, text)

    def test_pdf_render_ignores_tags(self):
        self.assertEqual(self.pdf.returncode, 0, self.pdf.stderr[-2000:])
        text = subprocess.run(["pdftotext", str(self.pdf_file), "-"], capture_output=True,
                              text=True).stdout
        self.assertIn(OK_CLAIM, " ".join(text.split()))

    def test_sourced_does_not_overwrite_plain(self):
        self.assertIsNotNone(self.plain_mtime)
        self.assertEqual(self.plain_docx.stat().st_mtime_ns, self.plain_mtime)
        self.assertTrue(self.sourced_docx.exists())

    def test_unavailable_check_never_errors_and_shows_no_source(self):
        self.assertEqual(self.broken.returncode, 0, self.broken.stderr)
        found = comments(self.broken_root / "paper_sourced.docx")
        self.assertEqual(len(found), 2)
        for author, text, _ in found:
            self.assertEqual(author, "Source check")
            self.assertEqual(text, "SOURCE CHECK FAILED: source check unavailable")

    def test_id_missing_from_results(self):
        self.assertEqual(self.partial.returncode, 0, self.partial.stderr)
        docx = self.partial_root / "paper_sourced.docx"
        _, text, _ = self.comment_for(docx, "no check result")
        self.assertEqual(text, "SOURCE CHECK FAILED: no check result for c2")
        _, text, _ = self.comment_for(docx, "Lbl, p. 3.")
        self.assertTrue(text.startswith("Lbl, p. 3. [OCR] UNREVIEWED: Text "), text)

    def test_design_quote_anchors_on_src_design(self):
        docx = self.partial_root / "paper_sourced.docx"
        _, text, _ = self.comment_for(docx, "Act, p. 9.")
        self.assertEqual(text, "Act, p. 9. The treatment quote here.")
        body = docx_part(docx, "word/document.xml")
        self.assertRegex(body, r"commentRangeStart w:id=\"(\d+)\".*treatment definition"
                         r".*commentRangeEnd w:id=\"\1\"")


if __name__ == "__main__":
    unittest.main()
