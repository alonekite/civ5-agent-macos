import base64
import hashlib
import tempfile
import tomllib
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.check_release_artifact import ArtifactError, inspect_wheel
from civ5_agent import __version__


class ReleaseArtifactTest(unittest.TestCase):
    def test_package_version_matches_project_metadata(self):
        project_root = Path(__file__).resolve().parents[1]
        metadata = tomllib.loads((project_root / "pyproject.toml").read_text())

        self.assertEqual(__version__, metadata["project"]["version"])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "src" / "civ5_agent").mkdir(parents=True)
        (self.root / "src" / "civ5_agent" / "__init__.py").write_text(
            '__version__ = "0.1.0"\n'
        )
        (self.root / "pyproject.toml").write_text(
            """[project]
name = "civ5-agent-macos"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
civ5-turn = "civ5_agent.turn_cli:main"
"""
        )

    def make_wheel(self, overrides=None, *, corrupt_record=False):
        dist = "civ5_agent_macos-0.1.0.dist-info"
        members = {
            "civ5_agent/__init__.py": b'__version__ = "0.1.0"\n',
            f"{dist}/METADATA": (
                b"Metadata-Version: 2.4\nName: civ5-agent-macos\n"
                b"Version: 0.1.0\nRequires-Python: >=3.11\n\n"
            ),
            f"{dist}/WHEEL": (
                b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
            ),
            f"{dist}/entry_points.txt": (
                b"[console_scripts]\nciv5-turn = civ5_agent.turn_cli:main\n"
            ),
            f"{dist}/top_level.txt": b"civ5_agent\n",
            f"{dist}/licenses/LICENSE": b"MIT\n",
        }
        if overrides:
            members.update(overrides)
        record_name = f"{dist}/RECORD"
        record_lines = []
        for name, content in members.items():
            digest = base64.urlsafe_b64encode(
                hashlib.sha256(content).digest()
            ).rstrip(b"=").decode()
            record_lines.append(f"{name},sha256={digest},{len(content)}")
        record_lines.append(f"{record_name},,")
        if corrupt_record:
            record_lines[0] = record_lines[0].replace("sha256=", "sha256=bad")
        members[record_name] = ("\n".join(record_lines) + "\n").encode()

        path = self.root / "civ5_agent_macos-0.1.0-py3-none-any.whl"
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return path

    def test_accepts_complete_bounded_wheel(self):
        result = inspect_wheel(self.make_wheel(), self.root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["project"], "civ5-agent-macos")
        self.assertEqual(result["version"], "0.1.0")
        self.assertRegex(result["sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_private_content_and_unsafe_members(self):
        private_values = (
            ("macOS user path", b"/Users/private/game.db\n"),
            ("private IPv4 address", b"192.168.4.2\n"),
            ("email address", b"private@example.invalid\n"),
            ("MAC address", b"02:00:5e:10:00:00\n"),
        )
        for label, content in private_values:
            with self.subTest(label=label), self.assertRaisesRegex(
                ArtifactError, label
            ):
                inspect_wheel(
                    self.make_wheel({"civ5_agent/__init__.py": content}),
                    self.root,
                )

        with self.assertRaisesRegex(ArtifactError, "unsafe artifact member"):
            inspect_wheel(self.make_wheel({"../escape.py": b"bad\n"}), self.root)

    def test_rejects_source_and_record_mismatch(self):
        with self.assertRaisesRegex(ArtifactError, "source mismatch"):
            inspect_wheel(
                self.make_wheel({"civ5_agent/extra.py": b"pass\n"}),
                self.root,
            )

        with self.assertRaisesRegex(ArtifactError, "RECORD mismatch"):
            inspect_wheel(self.make_wheel(corrupt_record=True), self.root)


if __name__ == "__main__":
    unittest.main()
