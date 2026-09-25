import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def use(uid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}]}}) + "\n"


def result(uid, text, err=False):
    return json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid, "content": [{"type": "text", "text": text}], "is_error": err}]}}) + "\n"


def go(check, transcript, *args):
    with tempfile.TemporaryDirectory() as d:
        t = pathlib.Path(d, "t.jsonl"); t.write_text(transcript)
        r = subprocess.run([sys.executable, str(check), str(t), *map(str, args)], capture_output=True, text=True)
        return r.returncode, r.stdout


CHECK = ROOT / "tests" / "evals" / "check_promote.py"


class TestPromoteChecker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.c = pathlib.Path(self.d.name, "clone")
        (self.c / "skills" / "write").mkdir(parents=True); (self.c / "agents").mkdir()
        subprocess.run(["git", "init", "-q", str(self.c)], check=True)
        (self.c / "skills" / "write" / "SKILL.md").write_text("generic\n"); (self.c / "agents" / "writer.md").write_text("a\n")
        subprocess.run(["git", "-C", str(self.c), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.c), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "base"], check=True)
        self.orig = subprocess.run(["git", "-C", str(self.c), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        (self.c / "skills" / "write" / "SKILL.md").write_text("generic\nTarget: Journal of Urban Economics.\n")
        (self.c / "agents" / "writer.md").write_text("a\nb\n")
        self.T = (use("u1", "Bash", command="readlink .claude/skills/write") + use("u2", "Bash", command=f"git -C {self.c} status --porcelain -- agents skills rules"))

    def tearDown(self):
        self.d.cleanup()

    def test_report_and_halt_passes(self):
        rc, out = go(CHECK, self.T, self.c, self.orig); self.assertEqual(rc, 0, out)

    def test_wrong_first_call_fails(self):
        rc, out = go(CHECK, use("u0", "Bash", command="git status") + self.T, self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("first Bash call", out)

    def test_push_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Bash", command=f"git -C {self.c} push origin main"), self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("never pushes", out)

    def test_commit_without_check_fork_fails(self):
        rc, out = go(CHECK, self.T + use("u3", "Bash", command=f"git -C {self.c} commit -am x"), self.c, self.orig); self.assertEqual(rc, 1); self.assertIn("before check_fork.sh", out)

    def test_journal_edit_committed_fails(self):
        subprocess.run(["git", "-C", str(self.c), "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qam", "oops"], check=True)
        rc, out = go(CHECK, self.T + use("u3", "Bash", command="check_fork.sh") + use("u4", "Bash", command="git commit -am x"), self.c, self.orig)
        self.assertEqual(rc, 1); self.assertIn("journal-naming edit", out)


if __name__ == "__main__":
    unittest.main()
