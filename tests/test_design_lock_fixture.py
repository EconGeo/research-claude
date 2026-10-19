"""Task 15: the fixture manuscript follows the design-lock and prose-binding contract.

Each test copies tests/fixture-project to a temp dir (FixtureCase signs its design block with a
test token), plants one defect and asserts that the check built for it fails; the clean copy
passes every check. Tests marked (render) run quarto and skip without quarto or Rscript.
"""
import json, os, pathlib, shutil, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scripts"))
from test_pipeline import FixtureCase, run
import author_token as tok
import design_block as dsb

MS = "manuscript_fixture.qmd"
FP = pathlib.Path("quality_reports") / "render_fingerprint.json"
PANEL = pathlib.Path("data") / "raw" / "panel.csv"
CHECK = ROOT / "scripts" / "prose_number_check.py"
RESULTS_END = "@fig-trends plots the raw means."
LEGEND = "* p ≤ 0.10, ** p ≤ 0.05, *** p ≤ 0.01"
render_test = unittest.skipUnless(shutil.which("quarto") and shutil.which("Rscript"),
                                  "(render) quarto or Rscript not installed")


def git(cwd, *a):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *a],
                       capture_output=True, text=True)
    if p.returncode: raise AssertionError(p.stderr + p.stdout)
    return p.stdout


class DefectCase(FixtureCase):
    def setUp(self):
        super().setUp()
        self.ms = self.t / MS

    def plant(self, old, new):
        text = self.ms.read_text()
        self.assertIn(old, text, "the fixture no longer carries the anchor this defect is planted at")
        self.ms.write_text(text.replace(old, new, 1))

    def add_results_sentence(self, sentence):
        self.plant(RESULTS_END, RESULTS_END + "\n" + sentence)

    def prose(self):
        p = subprocess.run([sys.executable, str(CHECK), str(self.ms)], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def render(self):
        p = subprocess.run(["quarto", "render", MS], cwd=self.t, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def fingerprint(self):
        return json.loads((self.t / FP).read_text())

    def scale_outcome(self, factor):
        """Multiply the outcome column of data/raw/panel.csv (unit, year, treated, outcome)."""
        path = self.t / PANEL
        header, *rows = path.read_text().splitlines()
        self.assertEqual(header, '"unit","year","treated","outcome"')
        scaled = []
        for row in rows:
            unit, year, treated, outcome = row.split(",")
            scaled.append(f"{unit},{year},{treated},{round(float(outcome) * factor, 4)}")
        path.write_text("\n".join([header, *scaled]) + "\n")

    def init_git(self):
        git(self.t, "init", "-q", "-b", "main"); git(self.t, "add", "-A"); git(self.t, "commit", "-qm", "base")

    def issue(self, op, reason=None):
        tok.issue(self.t, op, reason, dsb.design_hash(self.ms.read_text()))


class TestCleanFixture(DefectCase):
    def test_clean_copy_passes_the_source_checks(self):
        rc, out = self.prose(); self.assertEqual(rc, 0, out)
        self.assertIn("ceiling 0 (default, retrofitted)", out)
        rc, out = run("design", "status", root=self.t); self.assertEqual(rc, 0, out); self.assertIn("SIGNED", out)
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "quarto_structure_check.py"), MS],
                           cwd=self.t, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @render_test
    def test_clean_copy_renders_and_commits(self):
        """(render) Exit 0, the fingerprint names m_main, the PDF prints the star legend with the ≤
        glyph, and commit-check passes the first commit once a cold render covers these bytes."""
        rc, out = run("render", "--cold", root=self.t); self.assertEqual(rc, 0, out)
        fp = self.fingerprint()
        self.assertEqual(fp["models"], ["m_main"]); self.assertNotEqual(fp["estimates_hash"], "fixture")
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_render.py"),
                            str(self.t / "manuscript_fixture.pdf"), "--expect", LEGEND], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        git(self.t, "init", "-q", "-b", "main"); git(self.t, "add", "-A")
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 0, out)


class TestResultWords(DefectCase):
    def test_typed_verdict_word_needs_a_guard(self):
        self.add_results_sentence("Adoption has a significant effect of `r rc_num(beta_hat, 3)`.")
        rc, out = self.prose(); self.assertEqual(rc, 1, out); self.assertIn("significant", out)

    def test_typed_verdict_word_with_a_guard_passes(self):
        self.add_results_sentence('Adoption has a significant effect of `r rc_num(beta_hat, 3)`'
                                  '`r local({stopifnot("significant at the 10% level" = p_hat <= 0.10); ""})`.')
        rc, out = self.prose(); self.assertEqual(rc, 0, out)

    def test_direction_verb_without_a_guard_fails(self):
        self.add_results_sentence("After adoption the outcome rose by `r rc_num(beta_hat, 3)`.")
        rc, out = self.prose(); self.assertEqual(rc, 1, out); self.assertIn("rose", out)

    @render_test
    def test_direction_verb_guard_stops_the_render_against_the_sign(self):
        """(render) The guard binds the word to the sign: with the outcome negated, beta_hat < 0 and
        the render stops on the sentence that still says "rose"."""
        self.add_results_sentence('After adoption the outcome rose by `r rc_num(beta_hat, 3)`'
                                  '`r local({stopifnot("rose" = beta_hat > 0); ""})`.')
        rc, out = self.prose(); self.assertEqual(rc, 0, out)
        self.scale_outcome(-1)
        rc, out = self.render(); self.assertNotEqual(rc, 0, out); self.assertIn("rose", out)

    @render_test
    def test_na_estimate_stops_the_render(self):
        """(render) H1's estimate set to NA: the helper refuses to print a word or a number for it."""
        self.plant("```{r}\n#| label: tbl-main",
                   "```{r}\n#| label: planted-na\n#| cache: false\nbeta_hat <- NA_real_\n```\n\n"
                   "```{r}\n#| label: tbl-main")
        rc, out = self.render(); self.assertNotEqual(rc, 0, out); self.assertIn("not one finite number", out)


class TestSurfaces(DefectCase):
    def test_pipeline_jargon_in_prose(self):
        self.add_results_sentence("We report the governing p for this estimate.")
        rc, out = self.prose(); self.assertEqual(rc, 1, out); self.assertIn("PIPELINE JARGON", out)

    def test_typed_number_in_a_table_note(self):
        self.plant("Synthetic data.\",", "Synthetic data on 40 units.\",")
        rc, out = self.prose(); self.assertEqual(rc, 1, out); self.assertIn("'40'", out)

    def test_typed_number_in_the_abstract(self):
        self.plant("with a staggered treatment.", "with a staggered treatment and 400 observations.")
        rc, out = self.prose(); self.assertEqual(rc, 1, out); self.assertIn("'400'", out)


class TestDesignLock(DefectCase):
    def test_design_edit_without_unlock(self):
        """design-guard denies the agent edit; the same edit written straight to disk fails commit-check."""
        self.init_git()
        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(self.ms),
                   "old_string": "cluster: unit", "new_string": "cluster: year"}}
        p = subprocess.run([sys.executable, str(ROOT / "hooks" / "design-guard.py")], input=json.dumps(payload),
                           capture_output=True, text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.t)))
        self.assertIn('"permissionDecision": "deny"', p.stdout, p.stdout + p.stderr)
        self.plant("cluster: unit", "cluster: year"); git(self.t, "add", MS)
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 1, out); self.assertIn("CHANGED", out)

    def test_sign_without_an_author_token(self):
        (self.t / dsb.LOCK_REL).unlink(); (self.t / tok.TOKEN_REL).unlink()
        rc, out = run("design", "sign", "--signer", "fixture", root=self.t)
        self.assertEqual(rc, 1, out); self.assertIn("no author token", out)

    def amend_sample(self):
        """Unlock, narrow the sample, record the re-run explorations, and sign again, each step on its
        own token. On this balanced panel the re-run returns the same numbers; `rerun:` records it."""
        reason = "restrict the sample to the balanced panel"
        self.issue("unlock", reason)
        rc, out = run("design", "unlock", "--reason", reason, root=self.t); self.assertEqual(rc, 0, out)
        self.plant('sample: ["every unit-year in data/raw/panel.csv"]',
                   'sample: ["every unit-year in data/raw/panel.csv", "units observed in every year"]')
        self.plant("draws: 200, file:", "draws: 200, rerun: balanced, file:")
        self.plant("reps: 200, file:", "reps: 200, rerun: balanced, file:")
        self.issue("sign")
        rc, out = run("design", "sign", "--signer", "fixture", root=self.t); self.assertEqual(rc, 0, out)
        self.assertIn("amendment row(s) recorded", out)

    def test_amendment_without_the_design_changes_table(self):
        self.init_git(); self.amend_sample(); git(self.t, "add", "-A")
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 1, out); self.assertIn("tbl-design-changes", out)

    @render_test
    def test_amendment_with_the_design_changes_table(self):
        """(render) Adding the chunk changes chunk code, so the commit needs a cold render too."""
        self.init_git(); self.amend_sample()
        self.plant("# Conclusion", "@tbl-design-changes lists the changes to the research design.\n\n"
                   "```{r}\n#| label: tbl-design-changes\n#| cache: false\n#| tbl-cap: \"Changes to the research design\"\n"
                   "design_changes <- read.csv(here(\"quality_reports/design_amendments.csv\"), stringsAsFactors = FALSE)\n"
                   "knitr::kable(design_changes, col.names = c(\"Date\", \"Field\", \"Before\", \"After\", \"Reason\"))\n"
                   "```\n\n# Conclusion")
        rc, out = run("render", "--cold", root=self.t); self.assertEqual(rc, 0, out)
        git(self.t, "add", "-A")
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 0, out)


class TestFingerprint(DefectCase):
    @render_test
    def test_model_cache_does_not_survive_a_data_change(self):
        """(render) The global cache.extra carries the data hash, so a warm cache re-estimates."""
        rc, out = self.render(); self.assertEqual(rc, 0, out); before = self.fingerprint()
        self.assertTrue((self.t / "manuscript_fixture_cache").is_dir())
        self.scale_outcome(2)
        rc, out = self.render(); self.assertEqual(rc, 0, out); after = self.fingerprint()
        self.assertNotEqual(before["estimates_hash"], after["estimates_hash"])
        self.assertNotEqual(before["data_hash"], after["data_hash"])

    @render_test
    def test_robustness_model_named_in_no_hypothesis_is_fingerprinted(self):
        self.plant("```{r}\n#| label: tbl-main",
                   "```{r}\n#| label: estimate-robust\n#| cache: true\n#| dependson: \"build-panel\"\n"
                   "m_robust <- feols(outcome ~ treated | unit + year, data = panel, cluster = ~unit)\n```\n\n"
                   "```{r}\n#| label: tbl-main")
        rc, out = self.render(); self.assertEqual(rc, 0, out); before = self.fingerprint()
        self.assertEqual(before["models"], ["m_main", "m_robust"])
        self.plant("m_robust <- feols(outcome ~ treated | unit + year,", "m_robust <- feols(outcome ~ treated | unit,")
        rc, out = self.render(); self.assertEqual(rc, 0, out); after = self.fingerprint()
        self.assertNotEqual(before["estimates_hash"], after["estimates_hash"])

    @render_test
    def test_stale_writer_score_blocks_a_prose_only_commit(self):
        """(render) The re-estimation commit lands while the score is stale (WARN); the next
        prose-only commit is refused until the manuscript is re-scored."""
        rc, out = run("render", "--cold", root=self.t); self.assertEqual(rc, 0, out)
        self.init_git()
        self.assertEqual(run("state", "init", root=self.t)[0], 0)
        rc, out = run("state", "record-score", "manuscript", "90", "--critic", "writer-critic", "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)
        self.scale_outcome(2)
        rc, out = run("render", "--cold", root=self.t); self.assertEqual(rc, 0, out)
        git(self.t, "add", "-A")
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 0, out); self.assertIn("WARN re-estimation commit", out)
        git(self.t, "commit", "-qm", "re-estimate")
        self.ms.write_text(self.ms.read_text() + "\nA further plain sentence.\n"); git(self.t, "add", MS)
        rc, out = run("commit-check", root=self.t); self.assertEqual(rc, 1, out); self.assertIn("STALE", out)


class TestLedgerAndDispatch(DefectCase):
    def test_open_ledger_row_blocks_post_writer(self):
        rc, out = run("ledger", "add", "--creator", "writer", "--report", "r.md", "--location", "Results",
                      "--finding", "the direction word is typed", root=self.t)
        self.assertEqual(rc, 0, out)
        rc, out = run("post", "writer", root=self.t); self.assertEqual(rc, 1, out); self.assertIn("ledger-closed", out)

    def test_critic_dispatch_on_a_passed_target(self):
        self.assertEqual(run("state", "init", root=self.t)[0], 0)
        rc, out = run("state", "record-score", "manuscript", "90", "--critic", "writer-critic", "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)
        rc, out = run("dispatch-ok", "writer-critic", root=self.t); self.assertEqual(rc, 1, out); self.assertIn("PASSED-UNCHANGED", out)


if __name__ == "__main__":
    unittest.main()
