"""Renders of the source-comments feature: the Lua filter, the seed wiring and `pipeline.py sources docx`.

Each render is slow, so setUpClass builds one tiny fixture project and renders it once per output;
the tests only read the files those renders left behind.
"""
import csv
import html
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
# Characters markdown, TeX, HTML or citeproc would act on, all of which must reach Word as written.
ODD_PARAGRAPH = (r"Costs *not* $5 or $x$ at C:\path\file, 2^10^ and ~sub~ for @smith2020 <b>x</b>"
                 r" `code` \textbf{y} [z]{.u} -- \"q\". The odd sentence is here. Tail <i> & ends.")
ODD_SENTENCE = "The odd sentence is here."
ODD_CLAIM = "Paper wording of the odd rule."
MANUSCRIPT = f"""---
title: Fixture
format:
  docx: default
  pdf: default
---

Opening text. [{OK_CLAIM}]{{.src ref="ok" id="c1"}} Middle text.
[{BAD_CLAIM}]{{.src ref="bad" id="c2"}} Closing text.
[{ODD_CLAIM}]{{.src ref="odd" id="c3"}} End.
[Dup one.]{{.src ref="ok" id="c4"}} and [Dup two.]{{.src ref="ok" id="c4"}} again.
"""
REGISTRY_ROWS = [
    {"id": "ok", "file": "sources/a.txt", "label": "Lbl", "page": "3", "sentence": SENTENCE,
     "cleanup": "", "ocr": "FALSE"},
    {"id": "bad", "file": "sources/a.txt", "label": "Lbl", "page": "3",
     "sentence": "This sentence is absent from the file.", "cleanup": "", "ocr": "FALSE"},
    {"id": "odd", "file": "sources/odd.txt", "label": "Odd", "page": "1", "sentence": ODD_SENTENCE,
     "cleanup": "", "ocr": "FALSE"},
]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def make_project(root, scripts_link=True, manuscript="paper.qmd"):
    """A paper project: the seed _quarto.yml, CLAUDE.md, manuscript, two sources, the registry."""
    shutil.copy(ROOT / "seeds" / "_quarto.yml", root / "_quarto.yml")
    (root / "CLAUDE.md").write_text(f"manuscript: {manuscript}\n")
    (root / manuscript).parent.mkdir(parents=True, exist_ok=True)
    (root / manuscript).write_text(MANUSCRIPT)
    (root / "sources").mkdir()
    (root / "sources" / "a.txt").write_text(SOURCE_TEXT)
    (root / "sources" / "odd.txt").write_text("Intro line.\n\n" + ODD_PARAGRAPH + "\n")
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


def filter_args(root):
    """The filter as `pipeline.py sources docx` supplies it; the seed `_quarto.yml` never names it."""
    return ["--lua-filter", str(root / ".claude" / "scripts" / "source_comments.lua")]


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
        text = run_text(raw)
        found.append((author, text, raw))
    return found


def run_text(xml):
    return html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)))


def underlined_text(raw):
    runs = re.findall(r"<w:r>(?:(?!</w:r>).)*<w:u w:val=\"single\" />(?:(?!</w:r>).)*</w:r>", raw, re.S)
    return "".join(run_text(r) for r in runs)


def document_text(path):
    return run_text(docx_part(path, "word/document.xml"))


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
                            "--output", "paper_sourced.docx", *filter_args(cls.broken_root))

        cls.partial_root = base / "partial"
        cls.partial_root.mkdir()
        partial_json = ('{"c1": {"state": "UNREVIEWED", "label": "Lbl", "page": "3", "ocr": true,'
                        ' "paragraph": "Text [' + SENTENCE + ']{.underline} more.", "reason": "x",'
                        ' "before": "Text ", "sentence": "' + SENTENCE + '", "after": " more."},'
                        ' "design": {"state": "APPROVED", "label": "Act", "page": "9", "ocr": false,'
                        ' "paragraph": "The [treatment quote]{.underline} here.", "reason": "",'
                        ' "before": "The ", "sentence": "treatment quote", "after": " here."}}')
        make_fake_check_project(cls.partial_root, partial_json)
        with open(cls.partial_root / "paper.qmd", "a") as fh:
            fh.write("\nThe [treatment definition]{.src-design} is stated here.\n")
            fh.write("\n[Reserved claim.]{.src ref=\"ok\" id=\"design\"} uses the reserved id.\n")
        cls.partial = quarto(cls.partial_root, "--to", "docx", "-M", "source-comments:true",
                             "--output", "paper_sourced.docx", *filter_args(cls.partial_root))

        # A manuscript in a subdirectory, as two real papers declare it; pandoc's working
        # directory is then paper/, not the project.
        cls.sub_root = base / "subdir"
        cls.sub_root.mkdir()
        make_project(cls.sub_root, manuscript="paper/manuscript.qmd")
        cls.sub_plain = subprocess.run(["quarto", "render", "paper/manuscript.qmd", "--to", "docx"],
                                       cwd=cls.sub_root, capture_output=True, text=True)
        cls.sub_plain_docx = cls.sub_root / "paper" / "manuscript.docx"
        cls.sub_plain_mtime = (cls.sub_plain_docx.stat().st_mtime_ns
                               if cls.sub_plain_docx.exists() else None)
        time.sleep(1.1)
        cls.sub_sourced = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pipeline.py"), "--root", str(cls.sub_root),
             "sources", "docx"], capture_output=True, text=True)
        cls.sub_sourced_docx = cls.sub_root / "paper" / "manuscript_sourced.docx"

        # A .qmd that is not the declared manuscript: its tags are checked from its own text.
        (cls.sub_root / "other.qmd").write_text(
            f"---\ntitle: Other\n---\n\nSee [{OK_CLAIM}]{{.src ref=\"ok\" id=\"c9\"}} here.\n")
        cls.other = subprocess.run(["quarto", "render", "other.qmd", "--to", "docx", "-M",
                                    "source-comments:true", *filter_args(cls.sub_root)],
                                   cwd=cls.sub_root, capture_output=True, text=True)

        # Final review finding 6: the seed `_quarto.yml` with none of this feature's scripts linked
        # (a paper on an old link set): the plain render must still succeed.
        cls.bare_root = base / "bare"
        cls.bare_root.mkdir()
        make_project(cls.bare_root, scripts_link=False)
        (cls.bare_root / ".claude" / "scripts").mkdir()
        (cls.bare_root / ".claude" / "scripts" / "fix_docx_floats.py").symlink_to(
            ROOT / "scripts" / "fix_docx_floats.py")
        cls.bare = quarto(cls.bare_root, "--to", "docx")

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
        self.assertEqual(underlined_text(raw), SENTENCE)
        body = docx_part(self.sourced_docx, "word/document.xml")
        self.assertRegex(body, r"commentRangeStart w:id=\"(\d+)\".*" + re.escape(OK_CLAIM)
                         + r".*commentRangeEnd w:id=\"\1\"")

    def test_sourced_build_prints_warnings_and_path(self):
        out = self.sourced.stdout
        self.assertIn("source-check: FAILED c2 (bad)", out)
        self.assertIn("source-check: 2 claims not yet reviewed", out)
        self.assertEqual(out.strip().splitlines()[-1], str(self.sourced_docx.resolve()))

    def test_failed_claim_comment_has_no_source_text(self):
        author, text, _ = self.comment_for(self.sourced_docx, "registry sentence not found")
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
        self.assertEqual(len(found), 5)
        for author, text, _ in found:
            self.assertEqual(author, "Source check")
            self.assertEqual(text, "SOURCE CHECK FAILED: source check unavailable")

    def test_id_missing_from_results(self):
        self.assertEqual(self.partial.returncode, 0, self.partial.stderr)
        docx = self.partial_root / "paper_sourced.docx"
        _, text, _ = self.comment_for(docx, "no check result for c2")
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

    def test_source_text_is_never_parsed_as_markdown(self):
        _, text, raw = self.comment_for(self.sourced_docx, "Odd, p. 1.")
        self.assertEqual(text, "Odd, p. 1. UNREVIEWED: " + ODD_PARAGRAPH)
        self.assertEqual(underlined_text(raw), ODD_SENTENCE)

    def test_subdirectory_manuscript(self):
        self.assertEqual(self.sub_plain.returncode, 0, self.sub_plain.stderr)
        self.assertEqual(self.sub_sourced.returncode, 0, self.sub_sourced.stdout + self.sub_sourced.stderr)
        self.assertTrue(self.sub_sourced_docx.exists())
        self.assertFalse((self.sub_root / "manuscript_sourced.docx").exists())
        self.assertEqual(self.sub_plain_docx.stat().st_mtime_ns, self.sub_plain_mtime)
        self.assertEqual(self.sub_sourced.stdout.strip().splitlines()[-1],
                         str(self.sub_sourced_docx.resolve()))
        _, text, raw = self.comment_for(self.sub_sourced_docx, "Lbl, p. 3.")
        self.assertIn("Before the sentence. " + SENTENCE + " After it.", text)
        self.assertEqual(underlined_text(raw), SENTENCE)
        self.assertNotIn("unavailable", " ".join(c[1] for c in comments(self.sub_sourced_docx)))

    def test_rendered_file_is_checked_not_the_declared_one(self):
        self.assertEqual(self.other.returncode, 0, self.other.stderr)
        found = comments(self.sub_root / "other.docx")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0][1].startswith("Lbl, p. 3. UNREVIEWED: Before the sentence."), found[0][1])

    # Final review finding 4: repeated ids and the reserved id never show another claim's source.
    def test_duplicate_ids_get_failed_comments(self):
        found = [c for c in comments(self.sourced_docx) if "duplicate tag id c4" in c[1]]
        self.assertEqual([c[1] for c in found], ["SOURCE CHECK FAILED: duplicate tag id c4"] * 2)

    def test_src_tag_with_reserved_id_gets_failed_comment(self):
        docx = self.partial_root / "paper_sourced.docx"
        _, text, _ = self.comment_for(docx, "reserved")
        self.assertEqual(text, "SOURCE CHECK FAILED: tag id design is reserved")
        body = docx_part(docx, "word/document.xml")
        self.assertRegex(body, r"commentRangeStart w:id=\"(\d+)\".*Reserved claim\."
                         r".*commentRangeEnd w:id=\"\1\"")

    # Final review finding 6: the plain build never needs the filter or source_check.py.
    def test_seed_names_neither_filter_nor_check(self):
        seed = (ROOT / "seeds" / "_quarto.yml").read_text()
        self.assertNotIn("source_comments", seed)
        self.assertNotIn("source_check", seed)
        self.assertNotIn("filters:", seed)
        self.assertIn("post-render: python3 .claude/scripts/fix_docx_floats.py", seed)

    def test_plain_render_without_feature_scripts(self):
        self.assertEqual(self.bare.returncode, 0, self.bare.stdout + self.bare.stderr)
        self.assertTrue((self.bare_root / "paper.docx").exists())
        self.assertEqual(comments(self.bare_root / "paper.docx"), [])

    def test_plain_render_prints_source_warnings(self):
        log = self.plain.stdout + self.plain.stderr
        self.assertIn("source-check: FAILED c2 (bad)", log)

    # Final review finding 7: a sourced build whose comments went missing says so.
    def test_sourced_build_counts_comments(self):
        self.assertNotIn("comments", self.sourced.stdout.lower().replace("source comments", ""))

    def test_comment_count_mismatch_warns(self):
        import contextlib
        import io
        from unittest import mock
        sys.path.insert(0, str(ROOT / "scripts"))
        import pipeline
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            make_project(proj)
            plain = self.plain_docx

            def fake_run(cmd, cwd=None, **kwargs):
                shutil.copy(plain, Path(cwd) / "paper_sourced.docx")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            buf = io.StringIO()
            with mock.patch.object(pipeline.subprocess, "run", fake_run), contextlib.redirect_stdout(buf):
                rc = pipeline.sources_docx(proj)
        out = buf.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertIn("sources docx: WARNING paper_sourced.docx has 0 comments; expected 5", out)

    def test_failed_quarto_prints_no_path(self):
        env = dict(os.environ, PATH="/nonexistent")
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline.py"), "--root",
                               str(self.root), "sources", "docx"], capture_output=True, text=True,
                              env=env)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stdout.strip(), "sources docx: quarto is not on PATH")


class FixDocxFloatsSourceCheck(unittest.TestCase):
    """Render-time warnings come from fix_docx_floats.py (the seed's one post-render step): it runs
    source_check.py when that is linked beside it, prints its lines, and keeps its own exit code."""

    def run_post_render(self, check_source=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / ".claude" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "fix_docx_floats.py").symlink_to(ROOT / "scripts" / "fix_docx_floats.py")
            if check_source is not None:
                (scripts / "source_check.py").write_text(check_source)
            env = dict(os.environ, QUARTO_PROJECT_OUTPUT_FILES="")
            return subprocess.run([sys.executable, ".claude/scripts/fix_docx_floats.py"], cwd=root,
                                  capture_output=True, text=True, env=env)

    def test_no_source_check_linked(self):
        done = self.run_post_render()
        self.assertEqual((done.returncode, done.stdout), (0, ""), done.stderr)

    def test_warnings_printed(self):
        done = self.run_post_render("print('source-check: FAILED c1 (r): why')\n")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("source-check: FAILED c1 (r): why", done.stdout)

    def test_broken_check_never_changes_exit(self):
        for source in ("import sys\nsys.exit(3)\n", "raise RuntimeError('boom')\n", "this is not python\n"):
            done = self.run_post_render(source)
            self.assertEqual(done.returncode, 0, source + done.stderr)


if __name__ == "__main__":
    unittest.main()
