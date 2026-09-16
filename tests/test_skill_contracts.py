"""Progressive-disclosure and size contracts for skills/.

A bundled file must be named in the step that reads it, or in the agent that reads it. A
`## Bundled Resources` table at the end of a SKILL.md does not count: it tells the model what
exists, never when to read it, so the model either reads nothing (the file rots into an orphan
that contradicts its inline summary) or reads everything defensively. Both were found across
this tree on 2026-09-15.

KNOWN_UNBOUND is a ratchet. Entries come out as each skill is refactored. Nothing goes in.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Sections that CATALOGUE files rather than USE them. Stripped before the search, so a file
# named only here still counts as unbound.
CATALOGUE = re.compile(r"^## (Bundled [Rr]esources|Resources|Principles|Rules)\b.*?(?=^## |\Z)",
                       re.M | re.S)

KNOWN_UNBOUND = {
    # Task 4 — strategize
    # Task 5 — write
    # Task 7 — checkpoint
    "skills/checkpoint/templates/memory-entry-types.md",
    "skills/checkpoint/templates/research-journal-entry.md",
    "skills/checkpoint/templates/session-report-entry.md",
    # Not in this plan's scope — pipeline, revise, submit
    "skills/pipeline/references/setup.md",
    "skills/pipeline/references/talk.md",
    "skills/revise/templates/diplomatic-disagreement.md",
    "skills/revise/templates/response-tracker.md",
    "skills/submit/templates/audit-10-checks.md",
}

# Level-2 budget in characters of SKILL.md body (frontmatter excluded). Ratchet downward only.
BUDGET = {
    "review": 11000,
    "strategize": 8000,
    "write": 7500,
    "discover": 6000,
    "checkpoint": 5500,
}


def agent_text():
    return "\n".join(p.read_text() for p in (ROOT / "agents").glob("*.md"))


def body_of(skill_md):
    return re.sub(r"^---\n.*?\n---\n", "", skill_md.read_text(), count=1, flags=re.S)


class TestStepBinding(unittest.TestCase):
    def test_every_bundled_file_is_bound_to_a_step_or_an_agent(self):
        agents = agent_text()
        unbound = []
        for skill_dir in sorted((ROOT / "skills").iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            steps = CATALOGUE.sub("", skill_md.read_text())
            for f in sorted(skill_dir.rglob("*.md")):
                if f.name == "SKILL.md":
                    continue
                rel = f.relative_to(ROOT).as_posix()
                named = rel in steps or f.name in steps or rel in agents or f.name in agents
                if not named and rel not in KNOWN_UNBOUND:
                    unbound.append(rel)
        self.assertEqual([], unbound,
                         "bundled files named in no step and no agent (bind them, or delete them)")

    def test_the_allowlist_has_no_stale_entries(self):
        """An entry that is now bound must come out, or the ratchet stops ratcheting."""
        agents = agent_text()
        stale = []
        for rel in sorted(KNOWN_UNBOUND):
            f = ROOT / rel
            if not f.exists():
                stale.append(f"{rel} (file is gone)")
                continue
            skill_md = ROOT / "skills" / rel.split("/")[1] / "SKILL.md"
            steps = CATALOGUE.sub("", skill_md.read_text())
            if rel in steps or f.name in steps or rel in agents or f.name in agents:
                stale.append(f"{rel} (now bound)")
        self.assertEqual([], stale, "remove these from KNOWN_UNBOUND")


class TestLevelTwoBudget(unittest.TestCase):
    def test_refactored_skills_stay_under_budget(self):
        over = []
        for name, cap in sorted(BUDGET.items()):
            n = len(body_of(ROOT / "skills" / name / "SKILL.md"))
            if n > cap:
                over.append(f"{name}: {n} chars > {cap}")
        self.assertEqual([], over, "SKILL.md bodies load in full on every invocation")


if __name__ == "__main__":
    unittest.main()
