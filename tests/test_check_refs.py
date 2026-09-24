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


class TestPromoteRegisterCheck(unittest.TestCase):
    """Phase 4.3: D-2, D-3 and D-18 were all a mechanism correctly retired or introduced whose
    purpose nobody re-homed, found only because an audit went looking three months later.
    `/promote` is the moment a change lands upstream for everyone; it must prompt the promoting
    session to check the clo-author divergence register, not just document that it exists."""

    def _run(self, text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "skills" / "promote").mkdir(parents=True)
            (root / "skills" / "promote" / "SKILL.md").write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_promote_register_check(root)

    def test_no_mention_of_the_register_fails(self):
        self.assertEqual(self._run("Review pipeline changes and land them upstream.\n"), 1)

    def test_register_named_but_no_divergence_step_fails(self):
        """Naming the file in passing (e.g. a cross-reference elsewhere) is not a checklist step."""
        self.assertEqual(self._run("See docs/decisions/clo-author-divergences.md for history.\n"), 1)

    def test_register_and_divergence_step_passes(self):
        self.assertEqual(self._run(
            "Before committing, ask whether this change is a divergence from clo-author and "
            "add an entry to docs/decisions/clo-author-divergences.md if so.\n"), 0)

    def test_missing_file_reported(self):
        with tempfile.TemporaryDirectory() as t:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cr.crit_promote_register_check(pathlib.Path(t)), 1)

    def test_the_shipped_skill_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_promote_register_check(ROOT), 0)


class TestHooksReadme(unittest.TestCase):
    """closeout handoff §4.2 item 2: 'every shipped hook is either wired or explicitly exempt.'
    A hook file with no README row was invisible to both hooks criteria — hooks-readme had
    nothing to contradict, hooks-wired-source had nothing to check wiring for — so a hook could
    ship fully undocumented. crit_hooks_readme now also walks hooks/*.py and hooks/*.sh."""

    def _run(self, extra_files=()):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "hooks").mkdir()
            (root / "hooks" / "probe.py").write_text("#!/usr/bin/env python3\n# Hook Event: PreToolUse\n")
            (root / "hooks" / "README.md").write_text(
                "| Hook | Event | What it does |\n|---|---|---|\n"
                "| `probe.py` | PreToolUse | does a thing |\n")
            for name, text in extra_files:
                (root / "hooks" / name).write_text(text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_hooks_readme(root)

    def test_fully_documented_hooks_pass(self):
        self.assertEqual(self._run(), 0)

    def test_undocumented_hook_file_flagged(self):
        self.assertEqual(self._run(
            extra_files=[("unlisted.py", "#!/usr/bin/env python3\n# Hook Event: PostToolUse\n")]), 1)

    def test_the_shipped_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_hooks_readme(ROOT), 0)


class TestHooksWiredSource(unittest.TestCase):
    """hooks/README.md documents which hooks are wired directly vs. invoked indirectly (an
    Event cell containing 'via'). A directly-documented hook that seeds/settings.json never
    mentions is exactly the R-7/session-guard.py shape hooks/README.md's own 'not a dormant
    feature' section describes — this makes it a gate instead of a paragraph."""

    def _run(self, event_cell: str, settings_text: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "hooks").mkdir()
            (root / "hooks" / "probe.sh").write_text("#!/bin/bash\n# does a thing\n")
            (root / "hooks" / "README.md").write_text(
                "| Hook | Event | What it does |\n|---|---|---|\n"
                f"| `probe.sh` | {event_cell} | does a thing |\n")
            (root / "seeds").mkdir()
            (root / "seeds" / "settings.json").write_text(settings_text)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_hooks_wired_source(root)

    def test_directly_wired_hook_missing_from_settings_flagged(self):
        self.assertEqual(self._run("PreToolUse", "{}"), 1)

    def test_directly_wired_hook_present_in_settings_passes(self):
        self.assertEqual(self._run("PreToolUse", '{"cmd": "hooks/probe.sh"}'), 0)

    def test_indirectly_invoked_hook_not_required_in_settings(self):
        self.assertEqual(self._run("PostToolUse (via other.sh)", "{}"), 0)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_hooks_wired_source(ROOT), 0)


class TestWritesTools(unittest.TestCase):
    """Phase 2.1 of docs/plans/2026-09-23_pipeline-repair.md fixed nine agents by hand (no
    Write/Edit tool + no 'do not write' disclaimer meant a declared writes: path was silently
    never produced). This is the check that should have existed to catch it, and to stop it
    recurring: an agent with writes: in registry.yaml must EITHER carry a write-capable tool
    OR carry the disclaimer establishing the dispatching skill writes on its behalf."""

    def _run(self, agent_md_body: str) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "registry.yaml").write_text((ROOT / "rules" / "registry.yaml").read_text())
            (root / "agents").mkdir()
            # coder-critic already declares writes: in the real registry.yaml copied above;
            # only its own .md file's content varies per test.
            (root / "agents" / "coder-critic.md").write_text(agent_md_body)
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_writes_tools(root)

    def test_no_write_tool_no_disclaimer_flagged(self):
        self.assertEqual(self._run("---\ntools: Read, Grep, Glob\n---\nReview things.\n"), 1)

    def test_no_write_tool_with_disclaimer_passes(self):
        self.assertEqual(self._run(
            "---\ntools: Read, Grep, Glob\n---\n"
            "Return as your final response. Do NOT write any files yourself.\n"), 0)

    def test_write_tool_present_passes_without_disclaimer(self):
        self.assertEqual(self._run("---\ntools: Read, Write, Grep\n---\nWrite the report directly.\n"), 0)

    def test_creator_role_prose_does_not_count_as_a_disclaimer(self):
        """'Do not write the paper (that's the Writer)' names a deliverable, not a tool
        capability — it must not exempt an agent that lost its Write/Edit tool."""
        self.assertEqual(self._run(
            "---\ntools: Read, Grep\n---\n"
            "Do not write the paper (that's the Writer).\n"), 1)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_writes_tools(ROOT), 0)


class TestScriptRefs(unittest.TestCase):
    """R-fix, closeout handoff §4.2 item 4: a script path named in prose (a rule, a skill, an
    agent) that does not exist on disk. quarto_structure_check.py/INV-25 was cited before it
    existed once; this is the check that stops the next one. For the `.claude/scripts/` form
    specifically, also requires the script to be in scripts/SHIPPED — only what apply.sh
    actually installs into a project's `.claude/scripts/` resolves there for real."""

    def _run(self, text: str, create=(), shipped=None) -> int:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            (root / "rules").mkdir()
            (root / "rules" / "probe.md").write_text(text)
            for rel in create:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("")
            if shipped is not None:
                (root / "scripts").mkdir(exist_ok=True)
                (root / "scripts" / "SHIPPED").write_text("\n".join(shipped) + "\n")
            with contextlib.redirect_stdout(io.StringIO()):
                return cr.crit_script_refs(root)

    def test_nonexistent_script_flagged(self):
        self.assertEqual(self._run("Run `scripts/does_not_exist.py` first.\n"), 1)

    def test_existing_script_passes(self):
        self.assertEqual(self._run("Run `scripts/check_fork.sh` first.\n",
                                    create=["scripts/check_fork.sh"]), 0)

    def test_acquire_scripts_exempt(self):
        self.assertEqual(self._run("Run `scripts/acquire/clean_raw.py` (project-specific).\n"), 0)

    def test_claude_scripts_nonexistent_flagged(self):
        self.assertEqual(self._run("Run `python3 .claude/scripts/does_not_exist.py`.\n"), 1)

    def test_claude_scripts_existing_passes(self):
        """The script exists on disk AND is listed in scripts/SHIPPED — the only combination
        that actually resolves at .claude/scripts/ in an installed project."""
        self.assertEqual(self._run("Run `python3 .claude/scripts/check_fork.sh`.\n",
                                    create=["scripts/check_fork.sh"],
                                    shipped=["check_fork.sh"]), 0)

    def test_claude_scripts_existing_but_not_shipped_flagged(self):
        """check_refs.py itself exists in scripts/ but is a repo-maintenance gate, never
        installed into a project's .claude/scripts/ — apply.sh/scripts/SHIPPED never ships it.
        A `.claude/scripts/check_refs.py` citation is dead the moment it is installed."""
        self.assertEqual(self._run("Run `python3 .claude/scripts/foo.py`.\n",
                                    create=["scripts/foo.py"],
                                    shipped=["some_other_script.py"]), 1)

    def test_real_tree_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cr.crit_script_refs(ROOT), 0)

if __name__ == "__main__": unittest.main()
