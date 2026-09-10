import contextlib, io, sys, tempfile, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_refs as cr

class TestDeletedThingsAbsentSkill(unittest.TestCase):
    """R-fix-round-1: ABSENT_SKILLS' `new-project` entry must flag the retired `/new-project`
    skill without also flagging the live `/new-project-ztp` skill, whose name has the retired
    one as a hyphenated prefix. Regression for the `\\b`-after-hyphen false positive fixed in
    check_refs.py (`\\b` matches between `t` and `-`; a lookahead `(?![A-Za-z0-9_-])` does not)."""

    def _run(self, text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_deleted_things(root)

    def test_retired_new_project_still_flagged(self):
        self.assertEqual(self._run("the retired /new-project skill\n"), 1)

    def test_bare_new_project_with_trailing_punctuation_still_flagged(self):
        self.assertEqual(self._run("see /new-project.\n"), 1)

    def test_live_new_project_ztp_not_flagged(self):
        self.assertEqual(self._run("run /new-project-ztp when needed\n"), 0)

    def test_live_new_project_ztp_backticked_not_flagged(self):
        self.assertEqual(self._run("invoke `/new-project-ztp`\n"), 0)

if __name__ == "__main__": unittest.main()
