import json, os, shutil, subprocess, sys, tempfile, time, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPE = ROOT / "scripts" / "pipeline.py"

def run(*args, root):
    p = subprocess.run([sys.executable, str(PIPE), "--root", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "tests" / "fixture-project", self.t, dirs_exist_ok=True)
        (self.t / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
        os.symlink(ROOT / "scripts" / "prose_number_check.py", self.t / ".claude" / "scripts" / "prose_number_check.py")
        (self.t / ".claude" / "rules").mkdir(exist_ok=True)
        os.symlink(ROOT / "rules" / "registry.yaml", self.t / ".claude" / "rules" / "registry.yaml")
    def tearDown(self): shutil.rmtree(self.t)
    def log(self, agent): self.assertEqual(run("log", agent, root=self.t)[0], 0)

class TestManuscript(FixtureCase):
    def test_declared(self):
        rc, out = run("manuscript", root=self.t); self.assertEqual(rc, 0); self.assertIn("manuscript_fixture.qmd", out)
    def test_missing_declaration(self):
        (self.t / "CLAUDE.md").write_text("# no declaration\n")
        rc, out = run("manuscript", root=self.t); self.assertEqual(rc, 1); self.assertIn("manuscript:", out)
    def test_ambiguous(self):
        (self.t / "CLAUDE.md").write_text("manuscript: a.qmd\nmanuscript: b.qmd\n")
        self.assertEqual(run("manuscript", root=self.t)[0], 1)

class TestState(FixtureCase):
    def test_init_validate_roundtrip(self):
        self.assertEqual(run("state", "init", root=self.t)[0], 0)
        self.assertEqual(run("state", "validate", root=self.t)[0], 0)
    def test_legacy_shape_rejected(self):
        run("state", "init", root=self.t)
        (self.t / "quality_reports" / "pipeline_state.json").write_text(json.dumps({"project": "x", "current_phase": "Execution", "phases": {}}))
        rc, out = run("state", "validate", root=self.t); self.assertEqual(rc, 1); self.assertIn("schema_version", out)
    def test_score_range(self):
        run("state", "init", root=self.t)
        self.assertEqual(run("state", "record-score", "code", "101", "--critic", "coder-critic", "--report", "r.md", root=self.t)[0], 1)

class TestPredicates(FixtureCase):
    def test_pre_explorer_green_no_requires(self):
        self.assertEqual(run("pre", "explorer", root=self.t)[0], 0)
    def test_pre_writer_red_then_green(self):
        run("state", "init", root=self.t)
        rc, out = run("pre", "writer", root=self.t); self.assertEqual(rc, 1); self.assertIn("code score", out)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        rc, out = run("pre", "writer", root=self.t); self.assertEqual(rc, 0, out)   # render runs here (fixture renders)
    def test_post_coder_needs_critic(self):
        """`critic-ran` carries both halves of the contract, and reports its three failure
        states distinctly: critic never ran / ran but scored nothing / score predates."""
        run("state", "init", root=self.t)
        self.log("coder")
        rc, out = run("post", "coder", root=self.t)
        self.assertEqual(rc, 1); self.assertIn("has not completed after coder", out)
        time.sleep(0.01); self.log("coder-critic")
        rc, out = run("post", "coder", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("recorded no code score", out)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        rc, out = run("post", "coder", root=self.t); self.assertEqual(rc, 0, out)

    def test_post_coder_rejects_a_score_that_predates_the_creator(self):
        """The staleness hole: a `code` score recorded BEFORE coder ran reviewed earlier work.
        Sequence: init → record-score → log coder → log coder-critic → post coder."""
        run("state", "init", root=self.t)
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        time.sleep(0.01); self.log("coder")
        time.sleep(0.01); self.log("coder-critic")
        rc, out = run("post", "coder", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("from an earlier round", out)
        # re-scoring after the creator's completion closes the round
        run("state", "record-score", "code", "85", "--critic", "coder-critic", "--report", "r.md", root=self.t)
        rc, out = run("post", "coder", root=self.t); self.assertEqual(rc, 0, out)

    def test_component_none_skips_the_score_half(self):
        """storyteller has a critic but `component: none`. The skip is keyed on the COMPONENT,
        so a future creator without a component inherits it; `critic-ran` still binds the log."""
        run("state", "init", root=self.t)
        self.log("storyteller"); time.sleep(0.01); self.log("storyteller-critic")
        rc, out = run("post", "storyteller", root=self.t)      # fails on talks/*, not on the score
        self.assertIn("ok      critic-ran: storyteller-critic after storyteller (component none", out)

    def test_section_only_draft_names_the_sections_case(self):
        """A section-scoped score lands in state['sections'], so `post writer` fails — but it
        must not read as 'the critic never ran'."""
        run("state", "init", root=self.t)
        run("state", "record-score", "manuscript", "88", "--critic", "writer-critic", "--report", "r.md",
            "--scope", "section:Introduction", root=self.t)
        self.log("writer"); time.sleep(0.01); self.log("writer-critic")
        rc, out = run("post", "writer", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("`sections`", out); self.assertIn("does not close the writer stage", out)
    def test_post_strategist_sections(self):
        d = self.t / "quality_reports" / "strategy" / "fixture"; d.mkdir(parents=True)
        (d / "strategy_memo.md").write_text("# Memo\n## Estimand\n## Specification\n## Assumptions\n")
        rc, out = run("post", "strategist", root=self.t); self.assertEqual(rc, 1); self.assertIn("MISSING heading 'Robustness Plan'", out)
    def test_fresh_stale_after_data_touch(self):
        subprocess.run(["quarto", "render", "manuscript_fixture.qmd"], cwd=self.t, capture_output=True)
        self.assertEqual(run("fresh", root=self.t)[0], 0)
        time.sleep(1.1); (self.t / "data" / "raw" / "panel.csv").touch()
        self.assertEqual(run("fresh", root=self.t)[0], 1)

class TestScoreIfScored(FixtureCase):
    """`score-if-scored`: a component that HAS been scored must clear `min`; one never
    scored is ignored. `pre strategist` carries two of them (literature, data)."""
    def discovery_input(self):   # satisfies strategist's any_of, so only the scores decide
        d = self.t / "quality_reports" / "literature" / "fixture"; d.mkdir(parents=True)
        (d / "positioning.md").write_text("# Positioning\n")
    def record(self, comp, score):
        rc, out = run("state", "record-score", comp, str(score), "--critic", _scorer(comp), "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)

    def test_scored_below_min_blocks(self):
        self.discovery_input(); run("state", "init", root=self.t); self.record("literature", 40)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("literature score", out); self.assertIn("40", out)
    def test_scored_at_min_passes(self):
        self.discovery_input(); run("state", "init", root=self.t); self.record("literature", 80)
        rc, out = run("pre", "strategist", root=self.t); self.assertEqual(rc, 0, out)
    def test_never_scored_passes(self):
        self.discovery_input(); run("state", "init", root=self.t)
        rc, out = run("pre", "strategist", root=self.t); self.assertEqual(rc, 0, out)
    def test_mixed_scored_low_and_high_blocks(self):
        self.discovery_input(); run("state", "init", root=self.t)
        self.record("literature", 40); self.record("data", 90)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("literature score", out); self.assertIn("data score", out)
    def test_missing_state_file_fails(self):
        """H1: no state file must NOT read as 'never scored' — that would be fail-open."""
        self.discovery_input()
        self.assertFalse((self.t / "quality_reports" / "pipeline_state.json").exists())
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("no pipeline_state.json", out)
    def test_zero_score_blocks(self):
        """H2: 0.0 is a recorded score, not an absent one — truthiness would let it through."""
        self.discovery_input(); run("state", "init", root=self.t); self.record("literature", 0)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("literature score", out); self.assertIn("have 0.0", out)

# record-score now refuses a --critic that is not the component's declared `scored_by`
# (a creator could otherwise score itself and close its own stage). Tests must therefore
# name the real critic; read it from the registry so this can never drift.
def _scorer(comp):
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    import registry_lib as _rl
    return _rl.load_registry(ROOT)["components"][comp]["scored_by"]

class TestFreshnessAcrossFormats(FixtureCase):
    """`fresh` must consider EVERY rendered output, not whichever is newest.

    A live run surfaced this in a real project: a stray .html sat beside the .docx
    deliverable, rendered_output() returned the newer .html, and `post verifier`
    reported `ok render` without rendering — a stale deliverable certified by a
    file of a format the project does not publish.
    """
    def _touch(self, path, when):
        path.write_text("x")
        os.utime(path, (when, when))

    def test_stale_docx_is_not_saved_by_a_newer_html(self):
        run("state", "init", root=self.t)
        ms = self.t / "manuscript_fixture.qmd"
        base = ms.stat().st_mtime
        self._touch(ms.with_suffix(".docx"), base - 100)   # stale deliverable
        self._touch(ms.with_suffix(".html"), base + 100)   # newer, different format
        rc, out = run("fresh", root=self.t)
        self.assertNotEqual(rc, 0, f"a stale .docx must not pass: {out}")
        self.assertIn("manuscript_fixture.docx", out)

    def test_all_outputs_fresh_passes(self):
        run("state", "init", root=self.t)
        ms = self.t / "manuscript_fixture.qmd"
        base = ms.stat().st_mtime
        # newest input includes everything under data/raw/, not just the .qmd
        future = time.time() + 10_000
        self._touch(ms.with_suffix(".docx"), future)
        self._touch(ms.with_suffix(".html"), future)
        rc, out = run("fresh", root=self.t)
        self.assertEqual(rc, 0, out)


class TestScoredByEnforced(FixtureCase):
    """`record-score` honours the registry's `scored_by`.

    Without this, `record-score code 100 --critic coder` was accepted and `post coder`
    then passed on a creator that had scored itself — the invariant
    .claude/rules/agents.md states as "Creators never self-score"."""
    def test_creator_cannot_score_itself(self):
        run("state", "init", root=self.t)
        rc, out = run("state", "record-score", "code", "100", "--critic", "coder",
                      "--report", "r.md", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("scored by coder-critic", out)

    def test_declared_critic_is_accepted(self):
        run("state", "init", root=self.t)
        rc, out = run("state", "record-score", "code", "85", "--critic", "coder-critic",
                      "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)

    def test_every_component_scorer_is_accepted(self):
        run("state", "init", root=self.t)
        for comp in ["literature", "data", "strategy", "theory", "code",
                     "manuscript", "referees", "replication"]:
            rc, out = run("state", "record-score", comp, "85", "--critic", _scorer(comp),
                          "--report", "r.md", root=self.t)
            self.assertEqual(rc, 0, f"{comp}: {out}")

class TestScore(FixtureCase):
    def test_weighted_and_renormalised(self):
        run("state", "init", root=self.t)
        for c, s in [("literature", 90), ("data", 80), ("strategy", 90), ("code", 85), ("manuscript", 88), ("referees", 85), ("replication", 100)]:
            run("state", "record-score", c, str(s), "--critic", _scorer(c), "--report", "r.md", root=self.t)
        rc, out = run("score", root=self.t); self.assertIn("overall=87.3", out)
        run("state", "record-score", "theory", "92", "--critic", "theorist-critic", "--report", "r.md", root=self.t)
        rc, out = run("score", root=self.t); self.assertIn("overall=88.08", out)
        self.assertEqual(run("score", "--gate", "submission", root=self.t)[0], 1)
    def test_conflicts(self):
        self.assertEqual(run("conflicts", "coder", "writer", root=self.t)[0], 1)
        self.assertEqual(run("conflicts", "explorer", "coder", root=self.t)[0], 0)

class TestRegistryCheck(unittest.TestCase):
    def test_runs(self):
        rc, out = run("registry", "check", root=ROOT)
        for c in ["registry-complete", "registry-authority", "registry-rendered", "weights-sum", "registry-parse-agree"]:
            self.assertIn(f"[{c}]", out)

class TestProducerHint(FixtureCase):
    """A failing predicate must name the skill that produces it — `pipeline/SKILL.md` promises
    `status` reports "what is missing AND which skill produces it". The `producer` key is
    declared per predicate, including on predicates nested inside an `any_of`, so the
    composition must carry those hints out rather than swallow them."""
    def positioning(self):
        d = self.t / "quality_reports" / "literature" / "fixture"; d.mkdir(parents=True)
        (d / "positioning.md").write_text("# Positioning\n")

    def test_any_of_branches_name_their_producers(self):
        """The red: strategist's any_of declares a producer on BOTH branches."""
        run("state", "init", root=self.t)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out)
        self.assertIn("run `/lit-position`", out)
        self.assertIn("run `/discover data`", out)

    def test_flat_predicate_still_names_its_producer(self):
        """Control: a top-level predicate's hint already worked and must keep working."""
        self.positioning(); run("state", "init", root=self.t)
        run("state", "record-score", "literature", "40", "--critic", "lit-critic", "--report", "r.md", root=self.t)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("run `/lit-position`", out)

    def test_satisfied_any_of_emits_no_hint(self):
        """A hint on a branch of an any_of that is already satisfied would tell the user to
        run a skill they do not need."""
        self.positioning(); run("state", "init", root=self.t)
        rc, out = run("pre", "strategist", root=self.t)
        self.assertEqual(rc, 0, out); self.assertNotIn("run `", out)


class TestNext(FixtureCase):
    """`pipeline.py next` — where the driver starts.

    A component stage is CLOSED when its score postdates every completion its creators have
    in the dispatch log, or when it has a score and no completion at all — the adopted /
    cloned case, where the work was reviewed by the registry's critic but never ran under
    this driver (or ran on another machine, whose gitignored log did not travel). Without
    that rule an in-progress paper reads as unstarted and `run` restarts at literature.
    Stages behind the frontier (the last CLOSED one) that are still open are SKIPPED, not
    suggested; a conditional component is never suggested; `post` stays the in-run gate."""
    def record(self, comp, score):
        rc, out = run("state", "record-score", comp, str(score), "--critic", _scorer(comp), "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)

    def test_no_state_file_names_state_init(self):
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("state init", out)

    def test_fresh_project_starts_at_the_first_component(self):
        run("state", "init", root=self.t)
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 0, out); self.assertIn("next: literature", out)

    def test_a_score_with_no_logged_completion_closes_the_stage(self):
        """Adoption: code scored by coder-critic, coder never in the log. The stage is CLOSED
        (and says why), the stages before it are SKIPPED, and the frontier moves to manuscript
        — whose `pre writer` passes on the fixture (code >= 80, a tbl-* chunk, a render)."""
        run("state", "init", root=self.t); self.record("code", 85)
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"CLOSED\s+code\s.*no creator completion logged")
        self.assertRegex(out, r"SKIPPED\s+literature\s")
        self.assertIn("next: manuscript", out)

    def test_a_creator_completion_after_the_score_reopens_the_stage(self):
        """R-44 again, from the driver's side: coder ran after the last code score, so the
        round is open and the stage is where work is — its critic must score."""
        run("state", "init", root=self.t); self.record("code", 85)
        time.sleep(0.01); self.log("coder")
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"OPEN\s+code\s.*coder completed at .* no code score after it")
        self.assertIn("next: code", out)

    def test_skipped_behind_the_frontier_and_blocked_ahead_of_it(self):
        """manuscript scored, nothing else: everything before it is SKIPPED (never suggested,
        never faked); referees is BLOCKED on the code score; replication is BLOCKED on overall.
        Nothing is ready, so `next` says so and exits 1."""
        run("state", "init", root=self.t); self.record("manuscript", 88)
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 1, out)
        for c in ("literature", "data", "strategy", "code"):
            self.assertRegex(out, r"SKIPPED\s+" + c + r"\s", out)
        self.assertRegex(out, r"BLOCKED\s+referees\s.*code score")
        self.assertRegex(out, r"BLOCKED\s+replication\s.*overall score")
        self.assertIn("next: none", out); self.assertNotIn("next: literature", out)

    def test_a_conditional_component_behind_the_frontier_is_optional_not_skipped(self):
        """theory is conditional: behind a closed stage it is still the user's opt-in, and
        SKIPPED would read as a gap to close (observed on a real adoption, 2026-09-10)."""
        run("state", "init", root=self.t); self.record("code", 85)
        rc, out = run("next", root=self.t)
        self.assertRegex(out, r"OPTIONAL\s+theory\s"); self.assertNotRegex(out, r"SKIPPED\s+theory\s")

    def test_a_conditional_component_is_never_suggested(self):
        """strategy >= 80 makes theorist's `pre` pass, but theory is conditional: the user opts
        in. The suggestion is code (data-engineer / coder), whose `pre` also passes."""
        run("state", "init", root=self.t); self.record("strategy", 85)
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"OPTIONAL\s+theory\s")
        self.assertIn("next: code", out)

    def test_pre_is_evaluated_lazily_past_the_first_ready_stage(self):
        """`pre writer` renders the manuscript. `next` must not pay for stages after the one it
        is going to suggest — a fresh project stops at literature and leaves the rest PENDING."""
        run("state", "init", root=self.t)
        rc, out = run("next", root=self.t)
        self.assertRegex(out, r"PENDING\s+manuscript\s")
        self.assertNotIn("render", out)

    def test_every_stage_closed(self):
        run("state", "init", root=self.t)
        for c in ("literature", "data", "strategy", "code", "manuscript", "referees", "replication"):
            self.record(c, 90)
        rc, out = run("next", root=self.t)
        self.assertEqual(rc, 0, out); self.assertIn("next: none", out); self.assertIn("closed", out)


class TestDeductions(FixtureCase):
    """A floored score carries no ranking. Adoption runs deducted 185, 187, 347 and 817 points
    from critics that start at 100 and floor at 0 — four zeros that say nothing about which
    paper is closer to 80. `--deductions` records the unfloored total beside the score."""
    def rec(self, comp, score, *extra):
        return run("state", "record-score", comp, str(score), "--critic", _scorer(comp),
                   "--report", "r.md", *extra, root=self.t)
    def entry(self, comp):
        return json.loads((self.t / "quality_reports" / "pipeline_state.json").read_text())["components"][comp]

    def test_deductions_are_stored_beside_the_floored_score(self):
        run("state", "init", root=self.t)
        rc, out = self.rec("code", 0, "--deductions", "185"); self.assertEqual(rc, 0, out)
        self.assertEqual(self.entry("code")["deductions"], 185.0)
        self.assertEqual(run("state", "validate", root=self.t)[0], 0)

    def test_score_shows_the_deductions_behind_a_floor(self):
        run("state", "init", root=self.t)
        self.rec("code", 0, "--deductions", "185"); self.rec("manuscript", 0, "--deductions", "347")
        rc, out = run("score", root=self.t)
        self.assertRegex(out, r"code\s.*floored.*185 deducted")
        self.assertRegex(out, r"manuscript\s.*floored.*347 deducted")

    def test_a_floor_without_deductions_says_so(self):
        """Fail toward noticing: a 0 with no total is exactly the lost ranking."""
        run("state", "init", root=self.t); self.rec("code", 0)
        rc, out = run("score", root=self.t)
        self.assertRegex(out, r"code\s.*floored.*deductions not recorded")

    def test_an_unfloored_score_is_not_labelled(self):
        run("state", "init", root=self.t); self.rec("strategy", 61, "--deductions", "39")
        rc, out = run("score", root=self.t)
        self.assertNotIn("floored", out); self.assertIn("39 deducted", out)

    def test_score_and_deductions_must_agree(self):
        """A score that is not max(0, 100 - deductions) is a transcription error, not a score."""
        run("state", "init", root=self.t)
        rc, out = self.rec("code", 50, "--deductions", "185")
        self.assertEqual(rc, 1, out); self.assertIn("does not match", out)
        self.assertNotIn("code", json.loads((self.t / "quality_reports" / "pipeline_state.json").read_text())["components"])

    def test_negative_deductions_rejected(self):
        run("state", "init", root=self.t)
        rc, out = self.rec("code", 100, "--deductions", "-5"); self.assertEqual(rc, 1, out)

    def test_next_reports_the_deductions_of_a_closed_stage(self):
        run("state", "init", root=self.t); self.rec("code", 0, "--deductions", "187")
        rc, out = run("next", root=self.t)
        self.assertRegex(out, r"CLOSED\s+code\s.*187 deducted")

    def test_validate_rejects_a_malformed_deductions_field(self):
        run("state", "init", root=self.t); self.rec("code", 85)
        sp = self.t / "quality_reports" / "pipeline_state.json"; st = json.loads(sp.read_text())
        st["components"]["code"]["deductions"] = "lots"; sp.write_text(json.dumps(st))
        rc, out = run("state", "validate", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("deductions", out)


if __name__ == "__main__": unittest.main()
