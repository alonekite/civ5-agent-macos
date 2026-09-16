import base64
import hashlib
import io
import tarfile
import tempfile
import tomllib
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from civ5_agent import __version__
from scripts.check_release_artifact import (
    ArtifactError,
    inspect_artifacts,
    inspect_sdist,
    inspect_wheel,
)


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
        for name in (
            "CHANGELOG.md",
            "LICENSE",
            "MANIFEST.in",
            "README.md",
            "SECURITY.md",
        ):
            (self.root / name).write_text(f"fixture {name}\n")
        for name in (
            "docs/INDEX.md",
            "scripts/check_release_artifact.py",
            "scripts/test.sh",
            "tests/test_fixture.py",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture {name}\n")
        (self.root / "pyproject.toml").write_text(
            """[project]
name = "civ5-agent-macos"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
civ5-turn = "civ5_agent.turn_cli:main"
"""
        )

    def make_wheel(self, overrides=None, *, corrupt_record=False, directory=None):
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
            f"{dist}/licenses/LICENSE": (self.root / "LICENSE").read_bytes(),
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

        destination = directory or self.root
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "civ5_agent_macos-0.1.0-py3-none-any.whl"
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return path

    def make_sdist(self, *, omit=None, symlink=False):
        root_name = "civ5_agent_macos-0.1.0"
        paths = (
            "CHANGELOG.md",
            "LICENSE",
            "MANIFEST.in",
            "README.md",
            "SECURITY.md",
            "pyproject.toml",
            "docs/INDEX.md",
            "scripts/check_release_artifact.py",
            "scripts/test.sh",
            "src/civ5_agent/__init__.py",
            "tests/test_fixture.py",
        )
        members = {
            name: (self.root / name).read_bytes()
            for name in paths
            if name != omit
        }
        metadata = (
            b"Metadata-Version: 2.4\nName: civ5-agent-macos\n"
            b"Version: 0.1.0\nRequires-Python: >=3.11\n\n"
        )
        entry_points = b"[console_scripts]\nciv5-turn = civ5_agent.turn_cli:main\n"
        egg_info = "src/civ5_agent_macos.egg-info"
        members.update(
            {
                "PKG-INFO": metadata,
                "setup.cfg": b"[egg_info]\n",
                f"{egg_info}/PKG-INFO": metadata,
                f"{egg_info}/SOURCES.txt": b"fixture\n",
                f"{egg_info}/dependency_links.txt": b"\n",
                f"{egg_info}/entry_points.txt": entry_points,
                f"{egg_info}/top_level.txt": b"civ5_agent\n",
            }
        )
        path = self.root / f"{root_name}.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, content in members.items():
                info = tarfile.TarInfo(f"{root_name}/{name}")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            if symlink:
                info = tarfile.TarInfo(f"{root_name}/unsafe-link")
                info.type = tarfile.SYMTYPE
                info.linkname = "/private/data"
                archive.addfile(info)
        return path

    def test_accepts_complete_bounded_wheel(self):
        result = inspect_wheel(self.make_wheel(), self.root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["project"], "civ5-agent-macos")
        self.assertEqual(result["version"], "0.1.0")
        self.assertRegex(result["sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_private_content_and_unsafe_members(self):
        private_values = (
            ("macOS user path", b"/" + b"Users/private/game.db\n"),
            ("private IPv4 address", b"192" + b".168.4.2\n"),
            ("email address", b"private" + b"@example.invalid\n"),
            ("MAC address", b"02:00:5e" + b":10:00:00\n"),
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

        with self.assertRaisesRegex(ArtifactError, "source content mismatch"):
            inspect_wheel(
                self.make_wheel(
                    {"civ5_agent/__init__.py": b'__version__ = "changed"\n'}
                ),
                self.root,
            )

    def test_compares_normalized_artifact_contents(self):
        first = self.make_wheel(directory=self.root / "first")
        second = self.make_wheel(directory=self.root / "second")

        result = inspect_artifacts([first, second], self.root)
        self.assertTrue(result["ok"])

        changed_wheel_metadata = (
            b"Wheel-Version: 1.0\nGenerator: changed\n"
            b"Root-Is-Purelib: true\nTag: py3-none-any\n"
        )
        changed = self.make_wheel(
            {"civ5_agent_macos-0.1.0.dist-info/WHEEL": changed_wheel_metadata},
            directory=self.root / "changed",
        )
        with self.assertRaisesRegex(ArtifactError, "not reproducible"):
            inspect_artifacts([first, changed], self.root)

    def test_accepts_complete_source_distribution(self):
        result = inspect_sdist(self.make_sdist(), self.root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["kind"], "sdist")
        self.assertRegex(result["content_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_incomplete_or_linked_source_distribution(self):
        with self.assertRaisesRegex(ArtifactError, "content mismatch"):
            inspect_sdist(self.make_sdist(omit="README.md"), self.root)

        with self.assertRaisesRegex(ArtifactError, "not a regular file"):
            inspect_sdist(self.make_sdist(symlink=True), self.root)


if __name__ == "__main__":
    unittest.main()
