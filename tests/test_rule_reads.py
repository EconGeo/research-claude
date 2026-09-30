"""Rules excluded from startup loading are read at the point of need (plan 2026-09-29).

`claudeMdExcludes` keeps these rules out of every session's startup context, main and
subagent alike (docs/audits/2026-09-29_rule-consumer-audit.md §1). Each consumer the audit
found must therefore carry an explicit read of the rule. A consumer listed here that loses
its read line silently loses the rule.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# (file, rule, minimum number of read lines naming the rule)
READS = [
    # option gates: one read per gated mode (later gates in the same run reuse it)
    ("skills/analyze/SKILL.md", "option-gates", 1),
    ("skills/discover/SKILL.md", "option-gates", 3),
    ("skills/lit-position/SKILL.md", "option-gates", 1),
    ("skills/pipeline/SKILL.md", "option-gates", 1),
    ("skills/review/SKILL.md", "option-gates", 1),
    ("skills/revise/SKILL.md", "option-gates", 1),
    ("skills/strategize/SKILL.md", "option-gates", 1),
    ("skills/submit/SKILL.md", "option-gates", 1),
    ("skills/talk/SKILL.md", "option-gates", 1),
    ("skills/write/SKILL.md", "option-gates", 1),
    ("skills/ztp-data-tag/SKILL.md", "option-gates", 1),
    # skill steps that need a rule's text
    ("skills/checkpoint/SKILL.md", "session-handoff", 1),
    ("skills/submit/SKILL.md", "ai-disclosure", 1),
    ("skills/revise/SKILL.md", "revision", 1),
    ("skills/review/templates/manuscript-review-8-categories.md", "quarto-pdf", 1),
    ("skills/review/templates/manuscript-review-8-categories.md", "quarto-word", 1),
    # agents
    ("agents/coder-critic.md", "quarto-empirical", 1),
    ("agents/coder.md", "quarto-pdf", 1),
    ("agents/coder.md", "quarto-word", 1),
    ("agents/coder.md", "data-manifest", 1),
    ("agents/data-engineer.md", "quarto-empirical", 1),
    ("agents/data-engineer.md", "data-manifest", 1),
    ("agents/data-engineer.md", "quarto-pdf", 1),
    ("agents/data-engineer.md", "quarto-word", 1),
    ("agents/data-engineer.md", "ai-disclosure", 1),
    ("agents/strategist.md", "ai-disclosure", 1),
    ("agents/explorer.md", "ai-disclosure", 1),
    ("agents/theorist.md", "ai-disclosure", 1),
    ("agents/storyteller.md", "ai-disclosure", 1),
    # always-on rule pointing at an excluded one
    ("rules/agents.md", "permissions", 1),
]


def read_pattern(rule: str) -> re.Pattern:
    """'read' (any case, 'reads' too, never negated) followed on the same line by the rule's
    path, backticks optional, with nothing between but prose and other `.claude/rules/` paths —
    a read of some other file on the line does not count as a read of this rule."""
    name = re.escape(f"{rule}.md")
    between = r"(?:[^`\n]|`\.claude/rules/[\w-]+\.md`)*?"
    return re.compile(
        rf"(?<!not )(?<!n't )(?<!never )\b(?i:read)s?\b{between}`?(?:\.claude/rules/)?{name}`?"
    )


def read_lines(text: str, rule: str) -> int:
    return len(read_pattern(rule).findall(text))


class TestExcludedRulesAreRead(unittest.TestCase):
    def test_every_consumer_reads_its_rule(self):
        problems = []
        for rel, rule, minimum in READS:
            text = (ROOT / rel).read_text()
            n = read_lines(text, rule)
            if n < minimum:
                problems.append(f"{rel}: {n} read line(s) for {rule}.md, need {minimum}")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()


GATED_SKILLS = ["analyze", "discover", "lit-position", "pipeline", "review", "revise",
                "strategize", "submit", "talk", "write", "ztp-data-tag"]


class TestEveryOptionGateReadsTheRule(unittest.TestCase):
    """Each gate carries its own read: a later gate reached by another branch (a desk reject
    with the journal given, a DISAGREE row with no FATAL, a strike-three after compaction)
    must not depend on an earlier gate's read having run."""

    def test_each_gate_marker_is_followed_by_a_read(self):
        pat = read_pattern("option-gates")
        problems = []
        for skill in GATED_SKILLS:
            text = (ROOT / "skills" / skill / "SKILL.md").read_text()
            for m in re.finditer(re.escape("**Option gate**"), text):
                window = text[m.start(): m.start() + 200]
                if not pat.search(window):
                    line = text[: m.start()].count("\n") + 1
                    problems.append(f"{skill}/SKILL.md:{line}: gate without its own read")
        self.assertEqual([], problems)


class TestReadPatternIsStrict(unittest.TestCase):
    def test_false_passes_rejected(self):
        pat = read_pattern("option-gates")
        for line in ["Do not read `.claude/rules/option-gates.md` here.",
                     "Read `.claude/references/quarto-authoring.md`; gate per `.claude/rules/option-gates.md`."]:
            self.assertIsNone(pat.search(line), line)

    def test_true_reads_accepted(self):
        pat = read_pattern("option-gates")
        for line in ["Read .claude/rules/option-gates.md before the gate.",
                     "READ `.claude/rules/option-gates.md`",
                     "(read `.claude/rules/option-gates.md` first)"]:
            self.assertIsNotNone(pat.search(line), line)
