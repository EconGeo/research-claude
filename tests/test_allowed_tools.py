"""`allowed-tools` must cover what the skill body actually runs.

Audit 2026-09-15 §3 P5: `revise`, `strategize`, `discover` and `lit-position` ran
`pipeline.py` with no pre-approved `Bash`, and no ZotPilot-using skill pre-approved
`mcp__zotpilot__*`. Per the skills docs (fetched 2026-09-24), `allowed-tools` uses
permission-rule syntax and only pre-approves — a missing entry costs a prompt per call, not a
failure — but `/pipeline --yes` and the live fixture tier run unattended, and every unexpected
prompt there is a stall. Per the permissions docs, an allow glob is valid only after a literal
`mcp__<server>__` prefix, so `mcp__zotpilot__*` is the right spelling.

The two rules below are derived from the body, so a future skill that starts running a script
or an MCP tool turns this red on its own.
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# body pattern -> the allowed-tools entry it requires (regex over the allowed-tools value)
REQUIRED = {
    "pipeline.py": r"(^|[\s,])Bash\b",
    "mcp__zotpilot__": r"(^|[\s,])mcp__zotpilot(__\*)?(?=$|[\s,])",
}


def split(skill_md: pathlib.Path):
    text = skill_md.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.S)
    assert m, f"{skill_md}: no frontmatter"
    front, body = m.group(1), m.group(2)
    a = re.search(r"^allowed-tools:\s*(.*)$", front, flags=re.M)
    return (a.group(1).strip() if a else None), body


class TestAllowedToolsCoverWhatTheBodyRuns(unittest.TestCase):
    def test_every_shipped_skill(self):
        missing = []
        for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
            allowed, body = split(skill_md)
            for needle, rule in REQUIRED.items():
                if needle in body and (allowed is None or not re.search(rule, allowed)):
                    missing.append(f"{skill_md.parent.name}: body runs {needle!r}, "
                                   f"allowed-tools={allowed!r}")
        self.assertEqual([], missing, "pre-approve the tool the body runs")


if __name__ == "__main__":
    unittest.main()
