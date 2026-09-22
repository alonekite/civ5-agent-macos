"""Private one-use authorization tickets for external UI checkpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import time

from .identity import validate_bridge_session_id

CHECKPOINT_AUTHORIZATION_VERSION = 1
CHECKPOINT_STEPS = frozenset({"press_launcher_play", "click_game_continue"})
_NONCE = re.compile(r"^[0-9a-f]{8}$")
_CHALLENGE_FIELDS = frozenset(
    {
        "checkpoint_id",
        "created_at_unix",
        "nonce",
        "requested_at_unix",
        "schema_version",
        "step_id",
        "task_id",
    }
)


def _validate_binding(
    checkpoint_id: str, step_id: str, task_id: str
) -> tuple[str, str, str]:
    checkpoint = validate_bridge_session_id(checkpoint_id)
    task = validate_bridge_session_id(task_id)
    if step_id not in CHECKPOINT_STEPS:
        raise ValueError("checkpoint step is not supported")
    return checkpoint, step_id, task


def _authorization_phrase(step_id: str, nonce: str) -> str:
    return f"I am at the Mac; authorize {step_id} {nonce}"


def parse_checkpoint_time(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("timestamp must be ISO 8601") from error
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).timestamp()


def create_checkpoint_challenge(
    path: Path,
    *,
    checkpoint_id: str,
    step_id: str,
    task_id: str,
    requested_at_unix: float,
    now: float | None = None,
    nonce: str | None = None,
) -> dict[str, object]:
    """Create one private post-checkpoint operator-presence challenge."""
    checkpoint, step, task = _validate_binding(checkpoint_id, step_id, task_id)
    if not path.is_absolute():
        raise ValueError("challenge path must be absolute")
    created_at = time.time() if now is None else now
    if (
        isinstance(created_at, bool)
        or not isinstance(created_at, (int, float))
        or not math.isfinite(created_at)
    ):
        raise ValueError("challenge creation time must be finite")
    if isinstance(requested_at_unix, bool) or not isinstance(
        requested_at_unix, (int, float)
    ):
        raise ValueError("checkpoint request time must be numeric")
    if not math.isfinite(requested_at_unix) or requested_at_unix > created_at:
        raise ValueError("challenge must be created after checkpoint.requested")
    challenge_nonce = secrets.token_hex(4) if nonce is None else nonce
    if not _NONCE.fullmatch(challenge_nonce):
        raise ValueError("challenge nonce must be eight lowercase hexadecimal characters")
    record = {
        "checkpoint_id": checkpoint,
        "created_at_unix": created_at,
        "nonce": challenge_nonce,
        "requested_at_unix": float(requested_at_unix),
        "schema_version": CHECKPOINT_AUTHORIZATION_VERSION,
        "step_id": step,
        "task_id": task,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise ValueError("challenge could not be created") from error
    try:
        os.fchmod(descriptor, 0o600)
        payload = json.dumps(
            record, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("challenge write did not make progress")
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
        "nonce": challenge_nonce,
        "prompt": _authorization_phrase(step, challenge_nonce),
        "schema_version": CHECKPOINT_AUTHORIZATION_VERSION,
        "step_id": step,
    }


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("challenge contains a duplicate JSON field")
        value[key] = item
    return value


def authorize_checkpoint_challenge(
    path: Path,
    *,
    checkpoint_id: str,
    step_id: str,
    task_id: str,
    response: str,
    max_age_seconds: int = 300,
    now: float | None = None,
) -> dict[str, object]:
    """Validate and consume one exact fresh same-task operator challenge."""
    checkpoint, step, task = _validate_binding(checkpoint_id, step_id, task_id)
    if not path.is_absolute():
        raise ValueError("challenge path must be absolute")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int):
        raise ValueError("maximum challenge age must be an integer")
    if not 1 <= max_age_seconds <= 600:
        raise ValueError("maximum challenge age must be in 1..600 seconds")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as error:
        raise ValueError("challenge is unavailable") from error
    try:
        metadata = os.fstat(descriptor)
        payload = os.read(descriptor, 4097)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ValueError("challenge must be an owned regular file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("challenge mode must be 0600")
    if metadata.st_size > 4096 or len(payload) > 4096:
        raise ValueError("challenge is too large")
    try:
        record = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("challenge contains a non-finite number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("challenge is not valid private JSON") from error
    if not isinstance(record, dict) or frozenset(record) != _CHALLENGE_FIELDS:
        raise ValueError("challenge fields are invalid")
    if record.get("schema_version") != CHECKPOINT_AUTHORIZATION_VERSION:
        raise ValueError("challenge schema is unsupported")
    if (
        record.get("checkpoint_id") != checkpoint
        or record.get("step_id") != step
        or record.get("task_id") != task
    ):
        raise ValueError("challenge binding does not match the active checkpoint")
    created_at = record.get("created_at_unix")
    requested_at = record.get("requested_at_unix")
    nonce = record.get("nonce")
    if (
        isinstance(created_at, bool)
        or not isinstance(created_at, (int, float))
        or not math.isfinite(created_at)
        or isinstance(requested_at, bool)
        or not isinstance(requested_at, (int, float))
        or not math.isfinite(requested_at)
        or requested_at > created_at
        or not isinstance(nonce, str)
        or not _NONCE.fullmatch(nonce)
    ):
        raise ValueError("challenge values are invalid")
    checked_at = time.time() if now is None else now
    if (
        isinstance(checked_at, bool)
        or not isinstance(checked_at, (int, float))
        or not math.isfinite(checked_at)
    ):
        raise ValueError("challenge check time must be finite")
    if checked_at < created_at or checked_at - created_at > max_age_seconds:
        raise ValueError("challenge is not fresh")
    if not isinstance(response, str) or len(response) > 256:
        raise ValueError("operator response is invalid")
    if not secrets.compare_digest(
        response.encode("utf-8"), _authorization_phrase(step, nonce).encode("utf-8")
    ):
        raise ValueError("operator response does not match the current challenge")
    try:
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ValueError("challenge changed before consumption")
        path.unlink()
    except OSError as error:
        raise ValueError("challenge could not be consumed") from error
    return {
        "authorized": True,
        "checkpoint_id": checkpoint,
        "schema_version": CHECKPOINT_AUTHORIZATION_VERSION,
        "step_id": step,
    }
