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


class TestArtifactPaths(unittest.TestCase):
    """R-112: a `quality_reports/` path named in a shipped file must match a registry glob, be a
    directory prefix of one, or be an allow-listed unregistered artifact. The produces-path audit
    found OMITTED paths; this finds CONTRADICTING ones — a skill naming a save path its own
    agent's registry entry does not declare (R-108, R-111, and the theory-review template)."""

    def _run(self, text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "registry.yaml").write_text((ROOT / "rules" / "registry.yaml").read_text())
            (root / "skills" / "probe").mkdir(parents=True)
            (root / "skills" / "probe" / "SKILL.md").write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_artifact_paths(root)

    def test_contradicting_strategy_memo_path_flagged(self):
        """The R-111 shape: the memo saved flat instead of under strategy/<project>/."""
        self.assertEqual(self._run("Save to `quality_reports/strategy_memo_[topic].md`\n"), 1)

    def test_theory_review_template_shape_flagged(self):
        self.assertEqual(self._run("Save to `quality_reports/[FILENAME]_theory_review.md`:\n"), 1)

    def test_placeholder_form_of_a_registry_glob_passes(self):
        self.assertEqual(self._run("Save to `quality_reports/strategy/<project>/strategy_memo.md`\n"), 0)
        self.assertEqual(self._run("`quality_reports/reviews/claim_evidence_<project>_<date>.md`\n"), 0)

    def test_directory_prefix_of_a_registry_glob_passes(self):
        self.assertEqual(self._run("Save all outputs to `quality_reports/peer_review_<manuscript-stem>/`\n"), 0)

    def test_allow_listed_infrastructure_passes(self):
        self.assertEqual(self._run("reads `quality_reports/pipeline_state.json` and `quality_reports/agent_dispatch.jsonl`\n"), 0)

    def test_brace_group_expands_and_each_member_is_checked(self):
        self.assertEqual(self._run("`quality_reports/literature/<project>/{annotated_bibliography,frontier_map,positioning}.md`\n"), 0)
        self.assertEqual(self._run("`quality_reports/literature/<project>/{positioning,summary}.md`\n"), 1)

    def test_residue_marker_exempts_the_line(self):
        self.assertEqual(self._run("never `quality_reports/strategy_memo_[topic].md` <!-- residue:prohibition -->\n"), 0)


class TestPromoteVendorWarn(unittest.TestCase):
    """Phase 3.2: `/promote`'s Step 2 pathspec never lists a vendored tree, so an edit made
    through a project's link into one is invisible to it, and the matching `sync-*.sh`'s
    `rm -rf` destroys it with no warning. Every entry in `check_refs.VENDORED` needs its own
    warning line in skills/promote/SKILL.md, not just one of them."""

    def _run(self, text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "skills" / "promote").mkdir(parents=True)
            (root / "skills" / "promote" / "SKILL.md").write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_promote_vendor_warn(root)

    def test_warning_for_only_one_vendored_tree_still_fails(self):
        """The pre-fix shape: zotpilot-skills/ named, ai-audit/ not mentioned at all."""
        self.assertEqual(self._run("Does not edit anything under `zotpilot-skills/`, vendored verbatim.\n"), 1)

    def test_warning_for_both_vendored_trees_passes(self):
        self.assertEqual(self._run(
            "`zotpilot-skills/` and `ai-audit/` are vendored verbatim and never edited in place.\n"), 0)

    def test_bare_mention_with_no_vendor_context_does_not_count(self):
        """Naming the directory in an unrelated sentence (e.g. a file listing) is not a warning."""
        self.assertEqual(self._run("See ai-audit/README.md and zotpilot-skills/README.md for details.\n"), 1)

    def test_missing_file_reported(self):
        with tempfile.TemporaryDirectory() as t:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cr.crit_promote_vendor_warn(pathlib.Path(t)), 1)

    def test_the_shipped_skill_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_promote_vendor_warn(ROOT), 0)

if __name__ == "__main__": unittest.main()
