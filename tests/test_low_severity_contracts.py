"""Small contracts for the low-severity defects in audit section 4.

Each of these is a documented instruction that does not work: a command missing a required
flag, a test that is always true, an anchor that exists in no shipped file, a reference to a
deleted skill that the reference checker structurally cannot see.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMOTE = (ROOT / "skills" / "promote" / "SKILL.md").read_text()
APPLY = (ROOT / "apply.sh").read_text()
EXAMPLE = (ROOT / "state" / "obsidian-config.md.example").read_text()
REFS = (ROOT / "scripts" / "check_refs.py").read_text()
NPZ = (ROOT / "skills" / "new-project-ztp" / "SKILL.md").read_text()


class TestPromote(unittest.TestCase):
    def test_relink_command_carries_the_required_flag(self):
        self.assertIn("--project-dir is required", APPLY)
        for m in re.finditer(r"apply\.sh[^\n]*--link[^\n]*", PROMOTE):
            self.assertIn("--project-dir", m.group(0))

    def test_the_checkout_test_uses_the_discriminator_that_exists(self):
        """write_lock() writes commit= in BOTH modes; only the trailing comment differs."""
        self.assertIn("installed via", APPLY)
        self.assertIn("installed via", PROMOTE)

    def test_the_relink_claim_is_narrowed_to_new_top_level_items(self):
        self.assertRegex(PROMOTE, r"(?i)top-level")


class TestStateDirIsScanned(unittest.TestCase):
    def test_deleted_skill_is_not_referenced(self):
        self.assertNotIn("obsidian-digest-sync", EXAMPLE)

    def test_check_refs_can_see_this_file_at_all(self):
        ship = re.search(r"SHIP = \[([^\]]*)\]", REFS).group(1)
        self.assertIn('"state"', ship)
        suffix = re.search(r"TEXT_SUFFIX = \{([^}]*)\}", REFS).group(1)
        self.assertIn('".example"', suffix)


class TestNewProjectZtp(unittest.TestCase):
    def test_no_anchor_that_ships_nowhere(self):
        self.assertNotIn("## Current Project State", NPZ)

    def test_index_estimate_matches_the_readme(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("200 papers", readme)
        self.assertIn("200 papers", NPZ)
        self.assertIn("Ollama", NPZ)


if __name__ == "__main__":
    unittest.main()
