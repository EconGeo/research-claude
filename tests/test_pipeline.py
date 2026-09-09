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
        rc, out = run("state", "record-score", comp, str(score), "--critic", "x", "--report", "r.md", root=self.t)
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

class TestScore(FixtureCase):
    def test_weighted_and_renormalised(self):
        run("state", "init", root=self.t)
        for c, s in [("literature", 90), ("data", 80), ("strategy", 90), ("code", 85), ("manuscript", 88), ("referees", 85), ("replication", 100)]:
            run("state", "record-score", c, str(s), "--critic", "x", "--report", "r.md", root=self.t)
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

if __name__ == "__main__": unittest.main()
