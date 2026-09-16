#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import configparser
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
_DIST_INFO_FILES = frozenset(
    {
        "METADATA",
        "RECORD",
        "WHEEL",
        "entry_points.txt",
        "top_level.txt",
    }
)
_FORBIDDEN_SUFFIXES = frozenset(
    {
        ".db",
        ".jsonl",
        ".key",
        ".log",
        ".p12",
        ".pem",
        ".sqlite",
        ".sqlite3",
    }
)
_FORBIDDEN_COMPONENTS = frozenset(
    {".git", "__pycache__", "build", "dist", "logs", "tmp"}
)
_TEXT_PATTERNS = (
    ("macOS user path", re.compile(rb"/Users/[^/\s]+/")),
    ("Linux user path", re.compile(rb"/home/[^/\s]+/")),
    ("Windows user path", re.compile(rb"[A-Za-z]:\\Users\\[^\\\s]+\\")),
    (
        "private IPv4 address",
        re.compile(
            rb"(?<![0-9])(?:10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
            rb"|192\.168\.[0-9]{1,3}\.[0-9]{1,3}"
            rb"|172\.(?:1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3})(?![0-9])"
        ),
    ),
    (
        "private key",
        re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ),
    ("GitHub token", re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("AWS access key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    (
        "email address",
        re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
    (
        "MAC address",
        re.compile(rb"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f])"),
    ),
)


class ArtifactError(ValueError):
    pass


def inspect_wheel(path: Path, project_root: Path) -> dict[str, object]:
    project = _load_project(project_root)
    expected_distribution = re.sub(r"[-_.]+", "_", project["name"])
    expected_dist_info = f"{expected_distribution}-{project['version']}.dist-info"
    expected_sources = {
        source.relative_to(project_root / "src").as_posix()
        for source in (project_root / "src" / "civ5_agent").rglob("*.py")
    }

    if path.suffix != ".whl":
        raise ArtifactError("artifact must be a .whl file")
    expected_filename = (
        f"{expected_distribution}-{project['version']}-py3-none-any.whl"
    )
    if path.name != expected_filename:
        raise ArtifactError(f"wheel filename must be {expected_filename}")
    size = path.stat().st_size
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise ArtifactError(f"artifact size must be 1..{MAX_ARTIFACT_BYTES} bytes")

    try:
        with ZipFile(path) as archive:
            files = {
                info.filename: info
                for info in archive.infolist()
                if not info.is_dir()
            }
            if len(files) != len([info for info in archive.infolist() if not info.is_dir()]):
                raise ArtifactError("artifact contains duplicate member names")
            for info in files.values():
                _validate_member(info, expected_dist_info)
                content = archive.read(info)
                _scan_content(info.filename, content)

            packaged_sources = {
                name for name in files if name.startswith("civ5_agent/")
            }
            if packaged_sources != expected_sources:
                missing = sorted(expected_sources - packaged_sources)
                extra = sorted(packaged_sources - expected_sources)
                raise ArtifactError(
                    f"package source mismatch: missing={missing!r}, extra={extra!r}"
                )

            metadata_name = f"{expected_dist_info}/METADATA"
            entry_points_name = f"{expected_dist_info}/entry_points.txt"
            record_name = f"{expected_dist_info}/RECORD"
            wheel_name = f"{expected_dist_info}/WHEEL"
            for required in (
                metadata_name,
                entry_points_name,
                record_name,
                wheel_name,
            ):
                if required not in files:
                    raise ArtifactError(f"artifact is missing {required}")
            _validate_metadata(archive.read(metadata_name), project)
            _validate_entry_points(archive.read(entry_points_name), project)
            _validate_wheel_metadata(archive.read(wheel_name))
            _validate_record(archive, record_name, files)
    except BadZipFile as error:
        raise ArtifactError("artifact is not a valid wheel archive") from error

    return {
        "ok": True,
        "artifact": path.name,
        "bytes": size,
        "files": len(files),
        "project": project["name"],
        "sha256": _sha256(path.read_bytes()),
        "version": project["version"],
    }


def _load_project(project_root: Path) -> dict[str, object]:
    try:
        values = tomllib.loads((project_root / "pyproject.toml").read_text())
        project = values["project"]
        scripts = project["scripts"]
        name = project["name"]
        version = project["version"]
    except (KeyError, OSError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ArtifactError("project metadata is incomplete") from error
    if not isinstance(name, str) or not isinstance(version, str):
        raise ArtifactError("project name and version must be strings")
    if not isinstance(scripts, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in scripts.items()
    ):
        raise ArtifactError("project scripts must be a string mapping")
    return {"name": name, "version": version, "scripts": scripts}


def _validate_member(info: ZipInfo, expected_dist_info: str) -> None:
    path = PurePosixPath(info.filename)
    if (
        not info.filename
        or info.filename.startswith("/")
        or "\\" in info.filename
        or ".." in path.parts
        or any(part.lower() in _FORBIDDEN_COMPONENTS for part in path.parts)
    ):
        raise ArtifactError(f"unsafe artifact member: {info.filename!r}")
    if info.file_size > MAX_MEMBER_BYTES:
        raise ArtifactError(f"artifact member is too large: {info.filename}")
    if path.suffix.lower() in _FORBIDDEN_SUFFIXES:
        raise ArtifactError(f"forbidden artifact member: {info.filename}")
    mode = (info.external_attr >> 16) & 0o170000
    if mode not in {0, 0o100000}:
        raise ArtifactError(f"artifact member is not a regular file: {info.filename}")

    if path.parts[0] == "civ5_agent":
        if path.suffix != ".py":
            raise ArtifactError(f"unexpected package member: {info.filename}")
        return
    if path.parts[0] != expected_dist_info:
        raise ArtifactError(f"unexpected top-level artifact member: {info.filename}")
    relative = PurePosixPath(*path.parts[1:])
    if len(relative.parts) == 1 and relative.name in _DIST_INFO_FILES:
        return
    if relative.parts in {("LICENSE",), ("licenses", "LICENSE")}:
        return
    raise ArtifactError(f"unexpected metadata member: {info.filename}")


def _scan_content(name: str, content: bytes) -> None:
    for label, pattern in _TEXT_PATTERNS:
        if pattern.search(content):
            raise ArtifactError(f"{name} contains a {label}")


def _validate_metadata(content: bytes, project: dict[str, object]) -> None:
    text = content.decode("utf-8")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            fields.setdefault(key, value)
    if fields.get("Name") != project["name"]:
        raise ArtifactError("wheel metadata project name does not match pyproject")
    if fields.get("Version") != project["version"]:
        raise ArtifactError("wheel metadata version does not match pyproject")
    if fields.get("Requires-Python") != ">=3.11":
        raise ArtifactError("wheel metadata must require Python >=3.11")


def _validate_entry_points(content: bytes, project: dict[str, object]) -> None:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    try:
        parser.read_string(content.decode("utf-8"))
        actual = dict(parser["console_scripts"])
    except (KeyError, UnicodeDecodeError, configparser.Error) as error:
        raise ArtifactError("wheel entry points are malformed") from error
    if actual != project["scripts"]:
        raise ArtifactError("wheel console scripts do not match pyproject")


def _validate_wheel_metadata(content: bytes) -> None:
    text = content.decode("utf-8")
    if "Root-Is-Purelib: true\n" not in text or "Tag: py3-none-any\n" not in text:
        raise ArtifactError("wheel must be a pure Python py3-none-any artifact")


def _validate_record(
    archive: ZipFile,
    record_name: str,
    files: dict[str, ZipInfo],
) -> None:
    try:
        lines = archive.read(record_name).decode("utf-8").splitlines()
        entries = {}
        for line in lines:
            name, digest, size = line.rsplit(",", 2)
            if name in entries:
                raise ArtifactError("wheel RECORD contains duplicate paths")
            entries[name] = (digest, size)
    except (UnicodeDecodeError, ValueError) as error:
        raise ArtifactError("wheel RECORD is malformed") from error
    if set(entries) != set(files):
        raise ArtifactError("wheel RECORD paths do not match archive members")
    for name in files:
        digest, size = entries[name]
        if name == record_name:
            if digest or size:
                raise ArtifactError("wheel RECORD self-entry must omit hash and size")
            continue
        content = archive.read(name)
        expected_digest = base64.urlsafe_b64encode(
            hashlib.sha256(content).digest()
        ).rstrip(b"=").decode("ascii")
        if digest != f"sha256={expected_digest}" or size != str(len(content)):
            raise ArtifactError(f"wheel RECORD mismatch for {name}")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a civ5-agent wheel before release"
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        result = inspect_wheel(args.artifact, args.project_root.resolve())
        status = 0
    except (ArtifactError, OSError) as error:
        result = {"ok": False, "error": str(error)}
        status = 1
    print(json.dumps(result, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
