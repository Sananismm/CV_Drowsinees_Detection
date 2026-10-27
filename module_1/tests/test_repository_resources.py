import json
from pathlib import Path
import re
import unittest


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = MODULE_ROOT.parent
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class RepositoryResourceTests(unittest.TestCase):
    def test_json_resources_parse(self):
        paths = [MODULE_ROOT / "configs" / "experiment.json"]
        paths.extend((REPOSITORY_ROOT / "interfaces").rglob("*.json"))
        for path in paths:
            with self.subTest(path=str(path)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_local_markdown_links_resolve(self):
        markdown_files = list((MODULE_ROOT / "docs").glob("*.md"))
        markdown_files.extend(
            [
                MODULE_ROOT / "README.md",
                MODULE_ROOT / "CONTRIBUTING.md",
                MODULE_ROOT / "CHANGELOG.md",
                REPOSITORY_ROOT / "interfaces" / "README.md",
            ]
        )
        broken = []
        for markdown_path in markdown_files:
            content = markdown_path.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(content):
                target = target.strip().strip("<>")
                if (
                    not target
                    or target.startswith(("http://", "https://", "mailto:", "#"))
                ):
                    continue
                relative_path = target.split("#", 1)[0]
                resolved = (markdown_path.parent / relative_path).resolve()
                if not resolved.exists():
                    broken.append(f"{markdown_path}: {target}")
        self.assertEqual(broken, [], "Broken Markdown links:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
