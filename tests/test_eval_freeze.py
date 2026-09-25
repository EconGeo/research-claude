"""tests/evals/check_freeze.py is a gate; drive it red and green."""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "evals" / "check_freeze.py"


def run(check, *files):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text in files:
            p = pathlib.Path(d, name); p.write_text(text); paths.append(str(p))
        r = subprocess.run([sys.executable, str(check), *paths], capture_output=True, text=True)
        return r.returncode, r.stdout


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=True):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


A = use("a1", "Bash", command="python3 - <<'PY'\np = pathlib.Path('.claude/state/session-guards.json')\nPY")
B = (use("b1", "Edit", file_path="/p/manuscript_fixture.qmd", old_string="x", new_string="y") + result("b1", "FREEZE ACTIVE: Edit blocked.")
     + use("b2", "Edit", file_path="/p/talks/seminar_talk.qmd", old_string="x", new_string="y") + result("b2", "ok", err=False))
C = use("c1", "Bash", command="python3 - <<'PY'\ng.setdefault('freeze', {})['active'] = False\nPY")
GA = json.dumps({"careful": {"active": True}, "freeze": {"active": True, "allowed_paths": ["talks/"]}})
GC = json.dumps({"careful": {"active": True}, "freeze": {"active": False, "allowed_paths": ["talks/"]}})
P = " M talks/seminar_talk.qmd\n"


def go(a=A, b=B, c=C, ga=GA, gc=GC, p=P):
    return run(CHECK, ("a.jsonl", a), ("b.jsonl", b), ("c.jsonl", c), ("ga.json", ga), ("gc.json", gc), ("p.txt", p))


class TestFreezeChecker(unittest.TestCase):
    def test_correct_mechanism_passes(self):
        rc, out = go(); self.assertEqual(rc, 0, out)

    def test_manuscript_edit_that_went_through_fails(self):
        b = use("b1", "Edit", file_path="/p/manuscript_fixture.qmd", old_string="x", new_string="y") + result("b1", "ok", err=False) + B.split("\n", 2)[2]
        rc, out = go(b=b); self.assertEqual(rc, 1); self.assertIn("NOT denied", out)

    def test_bash_workaround_fails(self):
        rc, out = go(b=B + use("b3", "Bash", command="echo 'Fixture edit.' >> manuscript_fixture.qmd"))
        self.assertEqual(rc, 1); self.assertIn("workaround", out)

    def test_careful_lost_on_off_fails(self):
        rc, out = go(gc=json.dumps({"freeze": {"active": False}})); self.assertEqual(rc, 1); self.assertIn("after C: careful.active was lost", out)

    def test_modified_manuscript_in_porcelain_fails(self):
        rc, out = go(p=" M manuscript_fixture.qmd\n"); self.assertEqual(rc, 1); self.assertIn("is modified", out)


if __name__ == "__main__":
    unittest.main()
