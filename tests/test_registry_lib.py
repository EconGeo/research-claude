import sys, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_lib as rl

class TestYamlSubset(unittest.TestCase):
    def test_nested_map_list_scalars(self):
        text = "a:\n  b: 1\n  c: [] \n  d:\n    - x\n    - y: 2\n      z: true\n# comment\ne: \"q: r\"\n"
        self.assertEqual(rl.load_yaml_subset(text),
                         {"a": {"b": 1, "c": [], "d": ["x", {"y": 2, "z": True}]}, "e": "q: r"})
    def test_floats_and_null(self):
        self.assertEqual(rl.load_yaml_subset("w: 12.5\nn: null\ns: none\n"), {"w": 12.5, "n": None, "s": "none"})

class TestRegistry(unittest.TestCase):
    def setUp(self): self.reg = rl.load_registry(ROOT)
    def test_roster_matches_agents_dir(self):
        roster = {p.stem for p in (ROOT / "agents").glob("*.md")}
        declared = {a for a, e in self.reg["agents"].items() if e["kind"] == "agent"}
        self.assertEqual(declared - roster, set(), "declared but no agent file")
        self.assertEqual(roster - declared, set(), "agent file but not declared")
    def test_complete(self): self.assertEqual(rl.validate_registry(self.reg), [])
    def test_creator_without_critic_fails(self):
        reg = rl.load_registry(ROOT); reg["agents"]["coder"]["critic"] = "none"
        self.assertTrue(any("coder" in p for p in rl.validate_registry(reg)))
    def test_weights_sum_100(self):
        w = rl.component_weights(self.reg)
        self.assertEqual(sum(v for k, v in w.items() if k != "theory"), 100)
    def test_weights_agree_with_quality_md(self):
        self.assertEqual(rl.weights_report(self.reg, (ROOT / "rules" / "quality.md").read_text()), [])
    def test_parse_agree(self): self.assertIn(rl.parse_agree(ROOT), ("PASS", "SKIP"))

if __name__ == "__main__": unittest.main()
