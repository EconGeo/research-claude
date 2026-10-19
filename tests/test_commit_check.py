"""Task 12: `pipeline.py commit-check`, `render --cold`, and the git hooks that run them."""
import hashlib, json, os, pathlib, stat, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_pipeline import FixtureCase, run

MS = "manuscript_fixture.qmd"
FP = "quality_reports/render_fingerprint.json"
CR = "quality_reports/cold_render.json"
CHUNK_OLD = "n_years <- n_distinct(panel$year)"
CHUNK_NEW = "n_years <- n_distinct(panel$year) + 0L"


def git(cwd, *a, check=True):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *a],
                       capture_output=True, text=True)
    if check and p.returncode: raise AssertionError(p.stderr + p.stdout)
    return p


class CommitCase(FixtureCase):
    def setUp(self):
        super().setUp()
        git(self.t, "init", "-q", "-b", "main"); git(self.t, "add", "-A"); git(self.t, "commit", "-qm", "base")
        self.assertEqual(run("state", "init", root=self.t)[0], 0)

    def ms(self): return self.t / MS
    def edit(self, old, new): self.ms().write_text(self.ms().read_text().replace(old, new))
    def prose(self, sentence="A further plain sentence."): self.ms().write_text(self.ms().read_text() + "\n" + sentence + "\n")
    def stage(self, *p): git(self.t, "add", *p)
    def commit_plain(self, *p, msg="c"): git(self.t, "add", *p); git(self.t, "commit", "-qm", msg)
    def cc(self): return run("commit-check", root=self.t)
    def fp(self, h, data="d"):
        p = self.t / FP; p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps({"estimates_hash": h, "data_hash": data, "design_hash": "x", "models": {}}))
    def receipt(self, sha=None):
        sha = sha or hashlib.sha256(self.ms().read_bytes()).hexdigest()
        (self.t / CR).write_text(json.dumps({"manuscript_sha256": sha, "at": "now"}))
    def score(self, comp, critic):
        rc, out = run("state", "record-score", comp, "90", "--critic", critic, "--report", "r.md", root=self.t)
        self.assertEqual(rc, 0, out)
    def stale_setup(self):
        """manuscript scored under fingerprint A, fingerprint B committed."""
        self.fp("A"); self.commit_plain(FP); self.score("manuscript", "writer-critic")
        self.fp("B"); self.commit_plain(FP)


class TestCommitCheck(CommitCase):
    def test_no_claude_md(self):
        (self.t / "CLAUDE.md").unlink()
        self.assertEqual(self.cc()[0], 0)

    def test_nothing_relevant_staged(self):
        (self.t / "README.md").write_text("x\n"); self.stage("README.md")
        rc, out = self.cc(); self.assertEqual(rc, 0, out)

    def test_unrelated_staged_file_with_stale_manuscript_passes(self):
        self.stale_setup(); (self.t / "README.md").write_text("x\n"); self.stage("README.md")
        rc, out = self.cc(); self.assertEqual(rc, 0, out)

    def test_header_option_change_needs_cold_render(self):
        self.ms().write_text(self.ms().read_text().replace("```{r}\n#| label: estimate-main", "```{r, cache=FALSE}\n#| label: estimate-main", 1))
        self.stage(MS); rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("cold render", out)

    def test_non_ascii_manuscript_name(self):
        new = self.t / "manuscrit_é.qmd"; new.write_text(self.ms().read_text()); self.ms().unlink()
        (self.t / "CLAUDE.md").write_text("manuscript: manuscrit_é.qmd\n")
        self.commit_plain("-A"); new.write_text(new.read_text() + "\nOne more plain sentence.\nSee @fig-nope.\n")
        self.stage("manuscrit_é.qmd"); rc, out = self.cc(); self.assertEqual(rc, 1, out)

    def test_prose_only_passes(self):
        self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 0, out)

    def test_chunk_change_needs_cold_render(self):
        self.edit(CHUNK_OLD, CHUNK_NEW); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("cold render", out)
        self.receipt("0" * 64)
        self.assertEqual(self.cc()[0], 1)                     # a receipt for other bytes does not count
        self.receipt()
        rc, out = self.cc(); self.assertEqual(rc, 0, out)

    def test_unsigned_design_blocks(self):
        # The fixture carries a design: block; FixtureCase signs it. Without the lock it is unsigned.
        (self.t / "quality_reports" / "design_lock.json").unlink()
        self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 1, out); self.assertIn("design: UNSIGNED", out)

    def test_typed_literal_in_prose(self):
        self.prose("The effect is 0.4372 percent."); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("prose", out)

    def test_stale_prose_only_blocks(self):
        self.stale_setup(); self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("STALE", out)
        self.score("manuscript", "writer-critic")
        rc, out = self.cc(); self.assertEqual(rc, 0, out)

    def test_stale_reestimation_commit_warns(self):
        self.fp("A"); self.commit_plain(FP); self.score("manuscript", "writer-critic")
        self.edit(CHUNK_OLD, CHUNK_NEW); self.receipt(); self.fp("B"); self.stage(MS, FP)
        rc, out = self.cc(); self.assertEqual(rc, 0, out); self.assertIn("WARN re-estimation commit", out)

    def test_data_only_reestimation_warns(self):
        self.fp("A", "d1"); self.commit_plain(FP); self.score("manuscript", "writer-critic")
        self.fp("A", "d2"); self.stage(FP); self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 0, out)
        # estimates unchanged, so not stale: no warning needed, but the data change must register as re-estimation
        import importlib; sys.path.insert(0, str(ROOT / "scripts")); import pipeline
        self.assertTrue(pipeline.reestimation(self.t)[0])

    def test_data_only_with_stale_manuscript_warns(self):
        self.stale_setup(); self.fp("B", "d2"); self.stage(FP); self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 0, out); self.assertIn("WARN re-estimation commit", out)

    def test_stale_strategy_only_warns(self):
        self.fp("A"); self.commit_plain(FP); self.score("strategy", "strategist-critic")
        self.fp("B"); self.commit_plain(FP); self.score("manuscript", "writer-critic")
        self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 0, out); self.assertIn("WARN stale: strategy", out)

    def test_unstaged_fingerprint(self):
        self.fp("A"); self.commit_plain(FP)
        self.prose(); self.stage(MS); self.fp("B")
        rc, out = self.cc(); self.assertEqual(rc, 1)
        self.assertIn("stage quality_reports/render_fingerprint.json", out)

    def test_unstaged_manuscript(self):
        self.prose(); self.stage(MS); self.prose("Another one.")
        rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("stage " + MS, out)

    def test_amendments_need_table_chunk(self):
        (self.t / "quality_reports" / "design_amendments.csv").write_text(
            "date,field,old,new,reason\n2026-01-01,cluster,a,b,why\n")
        self.commit_plain("quality_reports/design_amendments.csv")
        self.prose(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 1); self.assertIn("tbl-design-changes", out)
        self.ms().write_text(self.ms().read_text() + "\nSee @tbl-design-changes.\n\n```{r}\n#| label: tbl-design-changes\nx <- 1\n```\n")
        self.receipt(); self.stage(MS)
        rc, out = self.cc(); self.assertEqual(rc, 0, out)


class TestRenderCold(CommitCase):
    def test_cold_removes_cache_and_writes_receipt(self):
        bindir = self.t / "mockbin"; bindir.mkdir()
        q = bindir / "quarto"; q.write_text("#!/bin/sh\nexit 0\n"); q.chmod(0o755)
        cache = self.t / "manuscript_fixture_cache"; (cache / "html").mkdir(parents=True); (cache / "html" / "x").write_text("c")
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline.py"), "--root", str(self.t), "render", "--cold"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(cache.exists())
        rec = json.loads((self.t / CR).read_text())
        self.assertEqual(rec["manuscript_sha256"], hashlib.sha256(self.ms().read_bytes()).hexdigest())
        self.assertIn("at", rec)

    def test_failed_render_writes_no_receipt(self):
        bindir = self.t / "mockbin"; bindir.mkdir()
        q = bindir / "quarto"; q.write_text("#!/bin/sh\nexit 3\n"); q.chmod(0o755)
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline.py"), "--root", str(self.t), "render", "--cold"],
                           capture_output=True, text=True, env=env)
        self.assertNotEqual(p.returncode, 0); self.assertFalse((self.t / CR).exists())


class TestGitHooks(CommitCase):
    def install(self):
        (self.t / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        os.symlink(ROOT / "hooks" / "git", self.t / ".claude" / "hooks" / "git")
        os.symlink(ROOT / "scripts" / "pipeline.py", self.t / ".claude" / "scripts" / "pipeline.py")
        for m in ("registry_lib", "design_block", "author_token", "findings_ledger", "qmd_chunks"):
            f = self.t / ".claude" / "scripts" / f"{m}.py"
            if not f.exists(): os.symlink(ROOT / "scripts" / f"{m}.py", f)
        git(self.t, "config", "core.hooksPath", ".claude/hooks/git")

    def test_hooks_are_executable(self):
        for h in ("pre-commit", "post-commit"):
            self.assertTrue(os.access(ROOT / "hooks" / "git" / h, os.X_OK), h)

    def test_hook_exits_0_when_pipeline_not_linked(self):
        (self.t / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        os.symlink(ROOT / "hooks" / "git", self.t / ".claude" / "hooks" / "git")
        git(self.t, "config", "core.hooksPath", ".claude/hooks/git")
        (self.t / ".claude" / "scripts" / "x").write_text("")           # keep scripts dir; pipeline.py absent
        self.prose(); git(self.t, "add", MS)
        self.assertEqual(git(self.t, "commit", "-qm", "p", check=False).returncode, 0)

    def test_stale_commit_refused_then_settled(self):
        self.stale_setup(); self.install()
        rc, out = run("ledger", "add", "--creator", "writer-critic", "--report", "r.md",
                      "--location", "s1", "--finding", "fix it", root=self.t); self.assertEqual(rc, 0, out)
        fid = out.split("added")[1].strip()
        rc, out = run("ledger", "close", fid, "--pending", root=self.t); self.assertEqual(rc, 0, out)
        self.prose(); git(self.t, "add", MS)
        p = git(self.t, "commit", "-qm", "stale", check=False)
        self.assertNotEqual(p.returncode, 0); self.assertIn("STALE", p.stdout + p.stderr)
        self.score("manuscript", "writer-critic")
        p = git(self.t, "commit", "-qm", "rescored", check=False)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        sha = git(self.t, "rev-parse", "--short=7", "HEAD").stdout.strip()
        rc, out = run("ledger", "show", root=self.t)
        self.assertIn("closed " + sha, out)


if __name__ == "__main__": unittest.main()
