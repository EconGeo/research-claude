"""check_single_manuscript.py — core rule 1 in the shipped tree: no `source(` and no
`readRDS(` of a results/output file in any shipped R code, including `r` fences in markdown."""
import pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_single_manuscript.py"

class TestCheckSingleManuscript(unittest.TestCase):
    def run_on(self, rel, text):
        with tempfile.TemporaryDirectory() as t:
            f = pathlib.Path(t) / rel; f.parent.mkdir(parents=True); f.write_text(text)
            return subprocess.run([sys.executable, str(SCRIPT), "--root", t], capture_output=True, text=True)

    def test_source_in_r_fence_fails(self):
        r = self.run_on("skills/x/SKILL.md", '```r\nsource("a.R")\n```\n')
        self.assertEqual(r.returncode, 1, r.stdout); self.assertIn("SKILL.md:2", r.stdout)

    def test_source_in_brace_r_fence_fails(self):
        r = self.run_on("rules/x.md", '```{r}\n#| label: a\nsource("a.R")\n```\n')
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_marked_prohibition_passes(self):
        r = self.run_on("skills/x/SKILL.md", '```r\nsource("a.R")  # residue:prohibition\n```\n')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_prose_outside_fence_passes(self):
        r = self.run_on("skills/x/SKILL.md", "Never call `source()` from the manuscript.\n```bash\nsource ~/.zshenv\n```\n")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_readrds_of_results_fails(self):
        r = self.run_on("templates/h.R.txt", 'fit <- readRDS(here("output/fit.rds"))\n')
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_readrds_of_data_passes(self):
        r = self.run_on("templates/h.R", 'raw <- readRDS(here("data/raw/x.rds"))\n')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_qmd_chunk_fails_but_qmd_prose_passes(self):
        self.assertEqual(self.run_on("templates/m.qmd", "We never source() code.\n\n```{r}\nsource('b.R')\n```\n").returncode, 1)
        self.assertEqual(self.run_on("templates/m.qmd", "We never source() code.\n").returncode, 0)

    def test_r_comment_is_not_code(self):
        r = self.run_on("templates/h.R", "# pasted, never source()d\nx <- 1\n")
        self.assertEqual(r.returncode, 0, r.stdout)

if __name__ == "__main__": unittest.main()
