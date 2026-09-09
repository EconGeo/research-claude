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
    def test_every_predicate_renders_as_prose_not_its_bare_type(self):
        """A missing `elif` in render_registry.pred() falls through to `else: s = t`, which
        renders the bare type string into permissions.md, silently dropping the predicate's
        component/threshold/glob. Nothing else catches it: `registry-rendered` only checks that
        the file MATCHES the render, so it stays green over the degraded prose."""
        import render_registry as rr
        seen = set()
        def walk(p, where):
            t = p["type"]; seen.add(t)
            s = rr.pred(p)
            self.assertNotEqual(s, t, f"{where}: {t} renders as its bare type string")
            self.assertFalse(s.startswith(t + " —"), f"{where}: {t} renders as its bare type string")
            for q in (p.get("of") or []): walk(q, where + ".of")
        for a, e in self.reg["agents"].items():
            for k in ("requires", "produces"):
                for j, p in enumerate(e[k] or []): walk(p, f"{a}.{k}[{j}]")
        # Types the registry happens not to use today are still rendered if one is added later.
        synthetic = {"fresh": {"type": "fresh"}, "critic-ran": {"type": "critic-ran"},
                     "score": {"type": "score", "component": "code", "min": 80},
                     "score-if-scored": {"type": "score-if-scored", "component": "code", "min": 80},
                     "path": {"type": "path", "glob": "x/*.md"}, "render": {"type": "render"},
                     "prose-check": {"type": "prose-check"}, "chunk": {"type": "chunk", "label_glob": "t-*", "min": 1},
                     "section": {"type": "section", "file": "manuscript", "heading": "H"},
                     "any_of": {"type": "any_of", "of": [{"type": "path", "glob": "x/*.md"}]}}
        self.assertEqual(set(synthetic), rl.PRED_TYPES, "a new predicate type needs a synthetic case here")
        for t in rl.PRED_TYPES - seen: walk(synthetic[t], f"synthetic {t}")
    def test_score_if_scored_needs_component_and_min(self):
        probs = []
        rl._check_pred({"type": "score-if-scored"}, "x", probs)
        self.assertTrue(any("missing 'component'" in p for p in probs), probs)
        self.assertTrue(any("missing 'min'" in p for p in probs), probs)
    def test_score_if_scored_rejects_overall(self):
        probs = []
        rl._check_pred({"type": "score-if-scored", "component": "overall", "min": 80}, "x", probs)
        self.assertTrue(any("overall" in p for p in probs), probs)

if __name__ == "__main__": unittest.main()
