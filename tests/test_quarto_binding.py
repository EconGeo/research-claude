"""The Quarto authoring reference is bound where .qmd is written (ledger L-001..L-003).

The reference existed for three weeks with no shipped file naming it; two projects corrected
the same silent failures. Binding means: named in the step or protocol that writes the file,
not in a resources table (tests/test_skill_contracts.py has the same standard).
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ".claude/references/quarto-authoring.md"
BOUND = [
    ("agents/writer.md", r"## Artifact Reading Protocol"),
    ("agents/coder.md", r"### Stage 3"),
    ("skills/write/SKILL.md", r"## Quarto Conventions"),
    ("skills/talk/SKILL.md", r"### `/talk create"),
    ("rules/quarto-empirical.md", r"## Relation to Other Rules"),
]


def section(text, heading_re):
    # NOTE (deviation from the task-6 brief, flagged in task-6-report.md "Concerns"):
    # heading_re already embeds its own "#"/"##"/"###" level marker (see BOUND below), so
    # matching it as `r"^(#{2,4}) [^\n]*" + heading_re` demanded the marker appear twice on
    # one line and never matched any real heading; confirmed by direct execution against
    # every BOUND file before this fix. Matching heading_re at line start directly, and
    # deriving the same-level boundary from its own leading hashes, preserves the original
    # intent (locate the section, bound it at the next heading of the same level) without
    # weakening any assertion.
    m = re.search(r"^" + heading_re, text, flags=re.M)
    assert m, heading_re
    level = re.match(r"#+", heading_re).group(0)
    rest = text[m.end():]
    n = re.search(r"^" + level + r" ", rest, flags=re.M)
    return rest[: n.start()] if n else rest


class TestReferenceShips(unittest.TestCase):
    def test_reference_is_in_the_shipped_tree_and_generic(self):
        p = ROOT / "references" / "quarto-authoring.md"
        self.assertTrue(p.exists())
        t = p.read_text()
        self.assertIn("## The gotchas ledger", t)
        self.assertNotRegex(t, r"\bNAR\b|zoning2026|POGM", "project noun in a shipped reference")  # <!-- residue:prohibition -->


class TestBinding(unittest.TestCase):
    def test_every_qmd_writer_names_the_reference_in_its_writing_step(self):
        missing = [f"{rel} /{h}/" for rel, h in BOUND
                   if REF not in section((ROOT / rel).read_text(), h)]
        self.assertEqual([], missing)


class TestGate(unittest.TestCase):
    def test_write_gate_has_item_4_and_render_runs_it(self):
        rule = (ROOT / "rules" / "quarto-empirical.md").read_text()
        self.assertRegex(rule, r"\[ \] 4\. .*check_render\.py")
        tools = (ROOT / "skills" / "tools" / "SKILL.md").read_text()
        # NOTE (deviation from the task-7 brief, per Task 7's controller ruling): section()
        # (see above) matches heading_re at line start and derives the section-boundary level
        # from heading_re's OWN leading "#" markers. The brief calls
        # section(tools, r"`/tools render") — no leading hashes — which does not match the
        # actual line ("### `/tools render [file]` — Quarto Render") and would crash on
        # `re.match(r"#+", heading_re).group(0)` (None has no .group). Passing the heading
        # with its real "### " prefix keeps the same section located and the same assertion.
        self.assertIn("check_render.py", section(tools, r"### `/tools render"))
        coder = (ROOT / "agents" / "coder.md").read_text()
        self.assertIn("check_render.py", section(coder, r"### Stage 3"))


if __name__ == "__main__":
    unittest.main()
