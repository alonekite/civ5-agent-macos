import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK_PATTERN = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("https://", "http://", "mailto:", "#")


def markdown_files():
    for name in ("README.md", "AGENTS.md", "SECURITY.md", "CHANGELOG.md"):
        path = ROOT / name
        if path.exists():
            yield path
    yield from sorted((ROOT / "docs").rglob("*.md"))


def local_links(path: Path):
    in_fence = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK_PATTERN.finditer(line):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split(maxsplit=1)[0]
            if target.startswith(EXTERNAL_PREFIXES):
                continue
            yield line_number, unquote(target.split("#", 1)[0])


class DocumentationTest(unittest.TestCase):
    def test_local_markdown_links_resolve_inside_repository(self):
        failures = []
        for document in markdown_files():
            for line_number, target in local_links(document):
                if not target:
                    continue
                if target.startswith("/"):
                    failures.append(
                        f"{document.relative_to(ROOT)}:{line_number}: "
                        f"absolute local link {target!r}"
                    )
                    continue
                resolved = (document.parent / target).resolve()
                try:
                    resolved.relative_to(ROOT)
                except ValueError:
                    failures.append(
                        f"{document.relative_to(ROOT)}:{line_number}: "
                        f"link escapes repository: {target!r}"
                    )
                    continue
                if not resolved.exists():
                    failures.append(
                        f"{document.relative_to(ROOT)}:{line_number}: "
                        f"missing link target {target!r}"
                    )
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
