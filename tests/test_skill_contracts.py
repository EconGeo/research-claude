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

# Emptied 2026-09-24: setup.md and talk.md bound in pipeline/SKILL.md; audit-10-checks.md deleted
# (verifier.md is the one definition). Nothing goes in.
KNOWN_UNBOUND: set[str] = set()

# Level-2 budget in characters of SKILL.md body (frontmatter excluded). Ratchet downward only,
# except for a deliberate, documented raise (see 2026-09-24 note below).
#
# Measured 2026-09-16 after the refactor: review 10,878 / strategize 7,967 / write 7,482 /
# discover 5,934 / checkpoint 5,495 — each already within 122 chars of its cap, so rounding the
# achieved size up to the next 500 reproduces these numbers exactly and there is nothing left to
# ratchet this round. Headroom is deliberately thin: pasting a table back into any of these files
# turns this test red, which is the point.
#
# 2026-09-24: review's cap raised 11,000 -> 11,500. The 2026-09-16 pass had cut a scannable
# "Save Reports" outputs list from --peer (and an unrelated re-run-logging instruction) purely to
# fit the inherited 11,000 cap, which was never a reasoned token-economics ceiling — it was just
# the as-measured size rounded up. SKILL.md bodies load in full only when the skill is dispatched
# (see the assertion message below), not as standing context in every session, so the exactness
# this section restores costs nothing except in a /review session, where it's exactly what earns
# its keep. Restored; new measured size 11,296.
#
# 2026-09-24: write's cap raised 7,500 -> 7,600. Phase 3.5 pointed Paper Type Detection at
# `.claude/references/narrative-arcs.md` (the same file `/talk` reads) so the file actually
# delivers what its spec asked for — "independent of `/talk`", usable from `/write` too. One
# sentence, not a table; new measured size 7,589.
# 2026-09-24 (09-16 closeout, Task 1): review's cap raised 11,500 -> 12,500. `--theory` was
# advertised in the flag list with no mode section — a weight-20 component whose critic-only
# route dispatched nothing — and `--stress` reused --peer's Phase 3 recording from a file stress
# mode never writes. The new mode section, the `--variance` refusal line (D-19) and the stress
# fix cost +861 net after moving two incident paragraphs to gotchas.md. Measured size 12,157.
# 2026-09-24 (09-16 closeout, Task 3): discover's cap raised 6,000 -> 6,200. `/discover data`
# had no `state strike explorer` line, so the data stage could never escalate (the driver's
# generic strike, now removed, was the only thing that ever counted a round there). The strike
# line is a dispatch instruction, not prose; measured size 6,141.
BUDGET = {
    "review": 12500,
    "strategize": 8000,
    "write": 7600,
    "discover": 6200,
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
