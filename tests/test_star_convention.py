"""Star convention: * p <= 0.10, ** p <= 0.05, *** p <= 0.01 across the shipped tree."""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIRS = ["agents", "skills", "rules", "references", "templates"]
STRICT = re.compile(r"p\s*<\s*0?\.(?:10?|05|01)\b|p<0")


def shipped():
    for d in DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.suffix in {".md", ".qmd", ".txt", ".R", ".json", ".yml", ".yaml", ".csv", ".tex"}:
                yield p


class Case(unittest.TestCase):
    def test_no_strict_star_cutoffs(self):
        scanned, bad = 0, []
        for p in shipped():
            scanned += 1
            for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if STRICT.search(line) and "APSA" not in line and "residue:prohibition" not in line:
                    bad.append(f"{p.relative_to(ROOT)}:{n}: {line.strip()[:120]}")
        self.assertGreater(scanned, 50, "scanned too few files")
        self.assertEqual(bad, [], "strict-inequality star cutoffs:\n" + "\n".join(bad))

    def test_no_results_seen_and_no_phacking(self):
        scanned, bad = 0, []
        for p in shipped():
            scanned += 1
            t = p.read_text(errors="replace")
            if re.search(r"results[ _-]seen|--results-seen", t, re.I):
                bad.append(str(p.relative_to(ROOT)))
        self.assertGreater(scanned, 50)
        self.assertEqual(bad, [])
        self.assertNotIn("p-hacking", (ROOT / "agents" / "editor.md").read_text())


if __name__ == "__main__":
    unittest.main()
