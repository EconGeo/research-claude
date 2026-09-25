"""scripts/validate_bib.py — `/tools validate-bib` as a shipped, testable script.

Audit 2026-09-15 P5 (tools row): the subcommand was an inline shell pipeline writing to
shared /tmp paths, which no test could exercise. The script takes the manuscript from
`pipeline.py manuscript` (or --manuscript), reads the .bib name from the YAML
`bibliography:` field, and exits non-zero on MISSING or DUPLICATE keys. UNUSED is
informational only (Zotero is the source of truth for what has been read).
"""
import pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_bib.py"
SKILL = (ROOT / "skills" / "tools" / "SKILL.md").read_text()


def run(root, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class Case(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "tests" / "fixture-project", self.t, dirs_exist_ok=True)
        self.ms = self.t / "manuscript_fixture.qmd"
        self.bib = self.t / "references.bib"
    def tearDown(self): shutil.rmtree(self.t)


class TestValidateBib(Case):
    def test_shipped(self):
        self.assertIn("validate_bib.py", (ROOT / "scripts" / "SHIPPED").read_text().split())

    def test_fixture_as_shipped_passes(self):
        # The fixture's only `@` outside a citation is an e-mail address (`fixture@example.edu`);
        # the script must not read it as a key.
        rc, out = run(self.t)
        self.assertEqual(rc, 0, out); self.assertNotIn("example.edu", out)

    def test_missing_key_fails(self):
        self.ms.write_text(self.ms.read_text() + "\nAs shown by @ghost2020 [-@ghost2020; @fixture2026].\n")
        rc, out = run(self.t)
        self.assertEqual(rc, 1, out); self.assertIn("MISSING", out); self.assertIn("ghost2020", out)

    def test_clean_passes_and_crossref_prefixes_are_not_citations(self):
        rc, out = run(self.t)
        self.assertEqual(rc, 0, out)
        for pref in ("eq-twfe", "tbl-main", "fig-trends"):
            self.assertNotIn(pref, out)

    def test_duplicate_key_fails(self):
        self.bib.write_text(self.bib.read_text() + "\n@misc{fixture2026,\n  title = {dup}\n}\n")
        rc, out = run(self.t)
        self.assertEqual(rc, 1, out); self.assertIn("DUPLICATE", out); self.assertIn("fixture2026", out)

    def test_unused_is_reported_but_not_a_failure(self):
        self.bib.write_text(self.bib.read_text() + "\n@misc{never2026,\n  title = {unused}\n}\n")
        rc, out = run(self.t)
        self.assertEqual(rc, 0, out); self.assertIn("UNUSED", out); self.assertIn("never2026", out)

    def test_bib_name_comes_from_the_yaml_field(self):
        self.ms.write_text(self.ms.read_text().replace('bibliography: "references.bib"', 'bibliography: "lit.bib"'))
        self.bib.rename(self.t / "lit.bib")
        rc, out = run(self.t)
        self.assertEqual(rc, 0, out); self.assertIn("lit.bib", out)

    def test_missing_bib_file_is_an_error(self):
        self.bib.unlink()
        rc, out = run(self.t)
        self.assertEqual(rc, 2, out); self.assertIn("references.bib", out)

    def test_email_addresses_are_not_citations(self):
        self.ms.write_text(self.ms.read_text() + "\nContact ada@example.org for data.\n")
        rc, out = run(self.t)
        self.assertEqual(rc, 0, out); self.assertNotIn("example.org", out)


class TestSkillCallsTheScript(unittest.TestCase):
    def test_validate_bib_section_runs_the_shipped_script_not_an_inline_pipeline(self):
        i = SKILL.index("### `/tools validate-bib")
        j = SKILL.index("\n### ", i + 1)
        s = SKILL[i:j]
        self.assertIn(".claude/scripts/validate_bib.py", s)
        self.assertNotIn("/tmp/", s)
        self.assertNotIn("comm -", s)


if __name__ == "__main__":
    unittest.main()
