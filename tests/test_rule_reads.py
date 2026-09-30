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


def read_lines(text: str, rule: str) -> int:
    """Lines on which 'read' precedes the rule's backticked path (or, inside rules/, its bare
    file name) within 160 characters. Same line only: a 'Read X' on the line above a gate
    that merely names the rule is not a read of the rule."""
    name = re.escape(f"{rule}.md")
    pat = re.compile(rf"\b[Rr]ead\b[^\n]{{0,160}}?`(?:\.claude/rules/)?{name}`")
    return len(pat.findall(text))


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
