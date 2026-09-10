import contextlib, io, sys, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_paths as cp

class TestPathReTruncatedStem(unittest.TestCase):
    """R-125: PATH_RE's tail class [A-Za-z0-9_./-]* cannot consume "{" or "*" and must end
    on a word char, so a placeholder ("coding-standards-{lang}.md") or a glob
    ("coding-standards-*.md") used to backtrack to a stem that names no file
    ("coding-standards"), reported as a false UNRESOLVED — R-21 class, but the reference
    was correct as written (references/coding-standards-r.md and friends exist). The fix
    is a trailing negative lookahead that refuses to let the match end at a position from
    which a run of path-charset characters leads into "{" or "*": the placeholder/glob
    reference is suppressed outright (no row at all) rather than mis-resolved."""

    def _rows(self, text: str):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "skills").mkdir()
            (root / "skills" / "probe.md").write_text(text)
            (root / "rules").mkdir()
            (root / "rules" / "registry.yaml").write_text("# real file\n")
            with contextlib.redirect_stdout(io.StringIO()):
                return cp.check(root, ["skills", "rules"])

    def test_placeholder_path_suppressed_not_unresolved(self):
        rows = self._rows("loaded from .claude/references/coding-standards-{lang}.md\n")
        self.assertEqual(rows, [])

    def test_glob_path_suppressed_not_unresolved(self):
        rows = self._rows("drawn from `.claude/references/coding-standards-*.md`\n")
        self.assertEqual(rows, [])

    def test_real_path_with_placeholder_sibling_still_resolves(self):
        # The placeholder must not swallow a genuine, resolvable reference on the same line.
        rows = self._rows(
            "see .claude/rules/registry.yaml, or .claude/references/coding-standards-{lang}.md\n"
        )
        self.assertEqual([(r[2], r[3]) for r in rows], [(".claude/rules/registry.yaml", "ok")])

    def test_real_path_still_resolves_unrelated_to_glob(self):
        rows = self._rows("see .claude/rules/registry.yaml for details\n")
        self.assertEqual([(r[2], r[3]) for r in rows], [(".claude/rules/registry.yaml", "ok")])

    def test_real_path_followed_by_spaced_markdown_emphasis_not_suppressed(self):
        # A "*" elsewhere on the line (markdown emphasis, separated by a backtick/space)
        # must not be mistaken for a glob touching the path.
        rows = self._rows("see `.claude/rules/registry.yaml`, and *emphasis* follows\n")
        self.assertEqual([(r[2], r[3]) for r in rows], [(".claude/rules/registry.yaml", "ok")])

if __name__ == "__main__": unittest.main()
