"""The improvement loop (audit 2026-09-15 §3 P6; plan 2026-09-25).

One rule, in meta-governance.md, says what happens when the user corrects a shared skill,
agent or rule. The three places that used to carry the 3+ bar onto corrections point at it.
No SKILL.md carries a self-improvement closing block: that per-invocation tax was declined on
2026-09-16 and stays declined.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULE = (ROOT / "rules" / "meta-governance.md").read_text()


class TestTheRule(unittest.TestCase):
    def test_user_corrections_section_states_both_paths_and_the_threshold(self):
        i = RULE.index("## User corrections")
        s = RULE[i:]
        for phrase in ("ask once", "at the moment of the correction", "/promote",
                       "scripts/ledger.py", "2 distinct projects", "never silently"):
            self.assertIn(phrase, s, phrase)

    def test_the_three_plus_bar_is_scoped_to_log_inferred_learnings(self):
        i = RULE.index("## Learning promotion")
        j = RULE.index("## User corrections")
        self.assertIn("3+ projects", RULE[i:j])
        self.assertRegex(RULE[i:j], r"dispatch log|state file")
        self.assertNotIn("3+", RULE[j:], "the corrections section must not restate the 3+ bar")


class TestPointers(unittest.TestCase):
    def test_checkpoint_tools_learn_and_logging_point_at_the_rule_and_the_ledger(self):
        for rel in ("skills/checkpoint/SKILL.md", "skills/tools/SKILL.md", "rules/logging.md"):
            t = (ROOT / rel).read_text()
            self.assertIn("meta-governance.md", t, rel)
            self.assertIn("ledger.py", t, rel)
            # Scoped (final-review Minor 9b): the 3+ bar is fine elsewhere in these files
            # (it still governs log-inferred learnings); it must not land back on a sentence
            # about corrections, which is what carrying it onto corrections looked like.
            for sentence in t.split("."):
                if "correction" in sentence.lower():
                    self.assertNotIn("3+", sentence,
                                      f"{rel}: a sentence about corrections still carries the 3+ bar: {sentence!r}")

    def test_promote_reads_the_ledger(self):
        t = (ROOT / "skills" / "promote" / "SKILL.md").read_text()
        self.assertIn("ledger.py show --open", t)
        self.assertIn("ledger.py mark", t)
        self.assertIn("REPEATED", t)


class TestNoClosingBlocks(unittest.TestCase):
    def test_no_skill_carries_a_self_improvement_closing_step(self):
        bad = []
        for p in (ROOT / "skills").glob("*/SKILL.md"):
            if re.search(r"skill-improvement\.md|Apply .*improvement rule", p.read_text()):
                bad.append(p.parent.name)
        self.assertEqual([], bad)


if __name__ == "__main__":
    unittest.main()
