"""One-use PLAY grant derived from an explicit same-task session initiation."""

from __future__ import annotations

import json
import math
import os
import re
import stat
import time
from pathlib import Path
from uuid import UUID

from .identity import validate_bridge_session_id

PLAY_GRANT_VERSION = 1
PLAY_INITIATION_TEXT = (
    "我在 Mac 前，开始一次受保护的 Civ V 只读会话，并授权仅本次的 PLAY 点击"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = frozenset(
    {
        "checkpoint_id",
        "created_at_unix",
        "expires_at_unix",
        "framework_session_id",
        "schema_version",
        "spec_sha256",
        "step_id",
        "task_id",
    }
)


def _identity(value: str, *, name: str) -> str:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError(f"{name} must be a canonical UUIDv4 or UUIDv7") from error
    if parsed.version not in {4, 7} or str(parsed) != value:
        raise ValueError(f"{name} must be a canonical UUIDv4 or UUIDv7")
    return value


def _time(value: float, *, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _binding(
    *, framework_session_id: str, checkpoint_id: str, spec_sha256: str, task_id: str
) -> tuple[str, str, str, str]:
    session = validate_bridge_session_id(framework_session_id)
    checkpoint = validate_bridge_session_id(checkpoint_id)
    task = _identity(task_id, name="task_id")
    if not isinstance(spec_sha256, str) or not _SHA256.fullmatch(spec_sha256):
        raise ValueError("spec_sha256 must be a lowercase SHA-256 digest")
    return session, checkpoint, spec_sha256, task


def create_play_session_grant(
    path: Path,
    *,
    framework_session_id: str,
    checkpoint_id: str,
    spec_sha256: str,
    task_id: str,
    initiation_text: str,
    initiated_at_unix: float,
    checkpoint_requested_at_unix: float,
    checkpoint_expires_at_unix: float,
    now: float | None = None,
) -> dict[str, object]:
    """Bind one exact PLAY checkpoint to a recent user-initiated session.

    The composition root must verify that ``initiation_text`` came from a new
    user message in ``task_id`` before the framework session was launched.
    """
    session, checkpoint, digest, task = _binding(
        framework_session_id=framework_session_id,
        checkpoint_id=checkpoint_id,
        spec_sha256=spec_sha256,
        task_id=task_id,
    )
    if not path.is_absolute():
        raise ValueError("grant path must be absolute")
    if initiation_text != PLAY_INITIATION_TEXT:
        raise ValueError("PLAY initiation text is not exact")
    initiated = _time(initiated_at_unix, name="initiation time")
    requested = _time(checkpoint_requested_at_unix, name="checkpoint request time")
    checkpoint_expiry = _time(checkpoint_expires_at_unix, name="checkpoint expiry")
    created = _time(time.time() if now is None else now, name="creation time")
    if not initiated <= requested <= created < checkpoint_expiry:
        raise ValueError(
            "PLAY grant requires a live checkpoint after session initiation"
        )
    if requested - initiated > 600 or created - initiated > 600:
        raise ValueError("session initiation is too old for PLAY preauthorization")
    if created - requested > 300:
        raise ValueError("PLAY checkpoint is too old")
    expiry = min(initiated + 600, requested + 300, checkpoint_expiry)
    if created >= expiry:
        raise ValueError("PLAY grant has expired")
    record = {
        "checkpoint_id": checkpoint,
        "created_at_unix": created,
        "expires_at_unix": expiry,
        "framework_session_id": session,
        "schema_version": PLAY_GRANT_VERSION,
        "spec_sha256": digest,
        "step_id": "press_launcher_play",
        "task_id": task,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise ValueError("PLAY grant could not be created") from error
    try:
        os.fchmod(descriptor, 0o600)
        payload = json.dumps(
            record, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        remaining = memoryview((payload + "\n").encode("utf-8"))
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("PLAY grant write did not make progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
    return {
        "checkpoint_id": checkpoint,
        "framework_session_id": session,
        "ok": True,
        "schema_version": PLAY_GRANT_VERSION,
        "step_id": "press_launcher_play",
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("PLAY grant contains duplicate fields")
        result[key] = value
    return result


def consume_play_session_grant(
    path: Path,
    *,
    framework_session_id: str,
    checkpoint_id: str,
    spec_sha256: str,
    task_id: str,
    now: float | None = None,
) -> dict[str, object]:
    """Consume the exact one-use PLAY grant before responding ``pass``."""
    session, checkpoint, digest, task = _binding(
        framework_session_id=framework_session_id,
        checkpoint_id=checkpoint_id,
        spec_sha256=spec_sha256,
        task_id=task_id,
    )
    if not path.is_absolute():
        raise ValueError("grant path must be absolute")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as error:
        raise ValueError("PLAY grant is unavailable") from error
    try:
        metadata = os.fstat(descriptor)
        payload = os.read(descriptor, 4097)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ValueError("PLAY grant must be an owned regular file")
    if stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_size > 4096:
        raise ValueError("PLAY grant mode or size is invalid")
    try:
        record = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non-finite")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("PLAY grant is not valid private JSON") from error
    if not isinstance(record, dict) or frozenset(record) != _FIELDS:
        raise ValueError("PLAY grant fields are invalid")
    if (
        record.get("schema_version") != PLAY_GRANT_VERSION
        or record.get("step_id") != "press_launcher_play"
        or record.get("framework_session_id") != session
        or record.get("checkpoint_id") != checkpoint
        or record.get("spec_sha256") != digest
        or record.get("task_id") != task
    ):
        raise ValueError("PLAY grant does not match the active session checkpoint")
    created = _time(record.get("created_at_unix"), name="grant creation time")
    expiry = _time(record.get("expires_at_unix"), name="grant expiry")
    checked = _time(time.time() if now is None else now, name="check time")
    if not created <= checked < expiry:
        raise ValueError("PLAY grant is not fresh")
    try:
        current = path.lstat()
    except OSError as error:
        raise ValueError("PLAY grant changed before consumption") from error
    if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
        raise ValueError("PLAY grant changed before consumption")
    try:
        path.unlink()
    except OSError as error:
        raise ValueError("PLAY grant could not be consumed") from error
    return {
        "authorized": True,
        "checkpoint_id": checkpoint,
        "framework_session_id": session,
        "schema_version": PLAY_GRANT_VERSION,
        "step_id": "press_launcher_play",
    }
