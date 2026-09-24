"""`state strike` must have exactly one owner per creator.

pipeline.py's strike is an unconditional increment with no round id, so two call sites firing
in one failing round count two strikes and escalate after two real rounds instead of three.
The mirror failure is worse and quieter: a stage whose skill has no strike line at all never
escalates, so a creator can loop indefinitely.

The rule (rules/agents.md §3): the stage skill owns `state strike <creator>` for its own
creator; the driver reads the count and escalates, it does not add to it.
"""
import pathlib, re, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_lib as rl  # noqa: E402

DRIVER = (ROOT / "skills" / "pipeline" / "SKILL.md").read_text()
REFS = ROOT / "skills" / "pipeline" / "references"

# Stages whose reference file states, in its own Escalation block, that no strike counter
# lives there — read in full 2026-09-24:
#   review.md  — "No new strike counter here. A low score sends the work back to its own
#                creator's stage", which carries that creator's counter.
#   submit.md  — "Creator: none"; verifier is infrastructure with no paired critic, and its
#                escalation is a stop-and-ask, not a three-strikes loop.
# Both have no `**Creator:** <agent>` line naming a registry creator, so they fall out of
# `delegating_stages()` on their own; they are listed here so the exemption is visible.
STATED_EXCEPTIONS = {"review", "submit"}


def delegating_stages():
    """{stage: (skill, [creator agents])} for every reference that delegates to a slash command
    and names at least one registry creator on its **Creator(s):** line."""
    reg = rl.load_registry(ROOT)["agents"]
    creators = {n for n, e in reg.items() if e.get("role") == "creator"}
    out = {}
    for f in sorted(REFS.glob("*.md")):
        text = f.read_text()
        m = re.search(r"\*\*Delegates to:\*\*\s*`?/([a-z-]+)", text)
        c = re.search(r"\*\*Creators?:\*\*(.*?)\*\*Critic", text, re.S)
        if not m or not c:
            continue
        named = sorted({n for n in re.findall(r"[a-z]+(?:-[a-z]+)*", c.group(1)) if n in creators})
        if named:
            out[f.stem] = (m.group(1), named)
    return out


class TestStrikeOwnership(unittest.TestCase):
    def test_the_driver_does_not_issue_a_generic_strike(self):
        """It cannot know whether the stage skill it just invoked already struck."""
        self.assertNotRegex(DRIVER, r"state strike <creator>")
        self.assertIn("strike", DRIVER)  # it still reports and escalates on the count

    def test_every_delegating_stage_skill_strikes_its_own_creator(self):
        stages = delegating_stages()
        self.assertTrue(STATED_EXCEPTIONS.isdisjoint(stages), "an exception now names a creator")
        missing = []
        for stage, (skill, agents) in stages.items():
            text = (ROOT / "skills" / skill / "SKILL.md").read_text()
            for agent in agents:
                if f"state strike {agent}" not in text:
                    missing.append(f"{stage} -> /{skill} never strikes {agent}")
        self.assertEqual([], missing, "stage skills that can never escalate")

    def test_the_ownership_rule_is_written_down_where_a_reader_will_meet_it(self):
        text = (ROOT / "rules" / "agents.md").read_text()
        self.assertIn("state strike", text)
        self.assertRegex(text, r"(?i)stage skill owns")


if __name__ == "__main__":
    unittest.main()
