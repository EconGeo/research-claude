"""Option gates (audit 2026-09-15 §3 P4).

A gate is a wait the user can answer with a pick from a ranked list, and that `--yes` answers
with rank 1. It lives in exactly one rule file; every gated skill mode names that rule and
carries the `**Option gate**` marker, so a gate that is described but never wired is visible
here. GATED grows one row per task in docs/plans/2026-09-24-option-gates-subagent-routing-evals.md
Part A; nothing is removed from it.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULE = ROOT / "rules" / "option-gates.md"
MARKER = "**Option gate**"

# (skill, mode-heading regex, minimum options the gate must offer)
GATED = [
    ("strategize", r"Identification Strategy", 5),  # Task A2
    ("discover", r"Research Interview", 5),  # Task A3
    ("discover", r"Data Discovery", 5),
    ("discover", r"Research Ideation", 5),
    ("lit-position", r"frontier_map", 5),  # Task A4
    ("lit-position", r"positioning", 5),
    ("lit-position", r"Dispatch `lit-critic`", 3),
    ("submit", r"Journal Targeting", 5),  # Task A5
    ("review", r"Full Peer Review", 5),  # Task A6
    ("revise", r"Classify severity", 5),  # Task A7
    ("talk", r"Create Quarto RevealJS Talk", 5),  # Task A8
    ("write", r"Draft Paper Section", 5),  # Task A9
    ("pipeline", r"run \[", 5),  # Task A10
    ("analyze", r"Pre-Code Report", 2),  # Task A11
    # Task A12 — ztp-data-tag
]


def mode_body(text: str, heading_re: str):
    """Text from the matching `##`/`###`/`####` heading to the next heading of the same depth."""
    m = re.search(r"^(#{2,4}) [^\n]*" + heading_re + r"[^\n]*$", text, flags=re.M)
    if not m:
        return None
    depth = m.group(1)
    rest = text[m.end():]
    n = re.search(r"^" + depth + r" ", rest, flags=re.M)
    return rest[: n.start()] if n else rest


class TestTheRuleExists(unittest.TestCase):
    def test_rule_file_defines_the_marker_and_yes(self):
        self.assertTrue(RULE.exists(), "rules/option-gates.md missing")
        s = RULE.read_text()
        self.assertIn(MARKER, s)
        self.assertRegex(s, r"--yes[^\n]*rank 1|rank 1[^\n]*--yes")
        self.assertRegex(s, r"5.{0,3}8|five to eight", "the rule states the 5–8 band")

    def test_agents_rule_points_here(self):
        self.assertIn(".claude/rules/option-gates.md", (ROOT / "rules" / "agents.md").read_text())


class TestEveryGateIsWired(unittest.TestCase):
    def test_gated_modes_carry_the_marker_and_name_the_rule(self):
        problems = []
        for skill, heading_re, minimum in GATED:
            text = (ROOT / "skills" / skill / "SKILL.md").read_text()
            body = mode_body(text, heading_re)
            if body is None:
                problems.append(f"{skill}: no mode heading matching /{heading_re}/")
                continue
            if MARKER not in body:
                problems.append(f"{skill} /{heading_re}/: no {MARKER}")
            if ".claude/rules/option-gates.md" not in body:
                problems.append(f"{skill} /{heading_re}/: does not name the rule")
            if not re.search(rf"\b{minimum}\b", body):
                problems.append(f"{skill} /{heading_re}/: does not state the minimum ({minimum})")
            front = text.split("---")[1]
            if "--yes" not in front:
                problems.append(f"{skill}: argument-hint does not advertise --yes")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
