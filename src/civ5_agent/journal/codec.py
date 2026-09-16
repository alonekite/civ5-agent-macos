from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ..errors import ValidationError
from ..identity import validate_bridge_session_id, validate_match_id
from .models import JournalRecord

JOURNAL_SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 4 * 1024 * 1024
RECORD_KINDS = frozenset(
    {
        "journal_started",
        "session_binding",
        "snapshot",
        "turn_transition",
        "command_submitted",
        "command_result",
        "verification_error",
        "correction",
    }
)
_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "match_id",
        "bridge_session_id",
        "captured_at",
        "turn",
        "kind",
        "payload",
        "previous_hash",
        "record_hash",
    }
)
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


class JournalCodecError(ValidationError):
    pass


def build_record(
    *,
    sequence: int,
    match_id: str,
    bridge_session_id: str | None,
    captured_at: str,
    turn: int | None,
    kind: str,
    payload: dict[str, Any],
    previous_hash: str | None,
) -> JournalRecord:
    values: dict[str, Any] = {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "sequence": sequence,
        "match_id": match_id,
        "bridge_session_id": bridge_session_id,
        "captured_at": captured_at,
        "turn": turn,
        "kind": kind,
        "payload": payload,
        "previous_hash": previous_hash,
    }
    _validate_values(values, require_hash=False)
    record_hash = hashlib.sha256(_canonical_bytes(values)).hexdigest()
    return JournalRecord(**values, record_hash=record_hash)


def encode_record(record: JournalRecord) -> bytes:
    values = asdict(record)
    _validate_values(values, require_hash=True)
    expected_hash = hashlib.sha256(
        _canonical_bytes({key: value for key, value in values.items() if key != "record_hash"})
    ).hexdigest()
    if record.record_hash != expected_hash:
        raise JournalCodecError("record_hash does not match canonical record content")
    encoded = _canonical_bytes(values) + b"\n"
    if len(encoded) > MAX_RECORD_BYTES:
        raise JournalCodecError("journal record exceeds maximum size")
    return encoded


def decode_record(line: bytes) -> JournalRecord:
    if not line.endswith(b"\n"):
        raise JournalCodecError("journal record is truncated")
    if len(line) > MAX_RECORD_BYTES:
        raise JournalCodecError("journal record exceeds maximum size")
    try:
        value = json.loads(
            line,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, JournalCodecError) as error:
        if isinstance(error, JournalCodecError):
            raise
        raise JournalCodecError(f"invalid journal JSON: {error}") from error
    if not isinstance(value, dict):
        raise JournalCodecError("journal record must be an object")
    if frozenset(value) != _FIELDS:
        unknown = sorted(set(value) - _FIELDS)
        missing = sorted(_FIELDS - set(value))
        raise JournalCodecError(
            f"journal record fields mismatch: missing={missing}, unknown={unknown}"
        )
    _validate_values(value, require_hash=True)
    expected_hash = hashlib.sha256(
        _canonical_bytes({key: item for key, item in value.items() if key != "record_hash"})
    ).hexdigest()
    if value["record_hash"] != expected_hash:
        raise JournalCodecError("record_hash does not match canonical record content")
    return JournalRecord(**value)


def _validate_values(values: dict[str, Any], *, require_hash: bool) -> None:
    if values.get("schema_version") != JOURNAL_SCHEMA_VERSION:
        raise JournalCodecError("unsupported journal schema_version")
    sequence = values.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise JournalCodecError("sequence must be a non-negative integer")
    try:
        validate_match_id(values.get("match_id"))
        session_id = values.get("bridge_session_id")
        if session_id is not None:
            validate_bridge_session_id(session_id)
    except ValueError as error:
        raise JournalCodecError(str(error)) from error
    captured_at = values.get("captured_at")
    if not isinstance(captured_at, str) or not captured_at.endswith("Z"):
        raise JournalCodecError("captured_at must be a canonical UTC timestamp")
    try:
        parsed_time = datetime.fromisoformat(captured_at.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise JournalCodecError("captured_at must be a canonical UTC timestamp") from error
    if parsed_time.utcoffset() is None or parsed_time.utcoffset().total_seconds() != 0:
        raise JournalCodecError("captured_at must be a canonical UTC timestamp")
    turn = values.get("turn")
    if turn is not None and (
        isinstance(turn, bool) or not isinstance(turn, int) or turn < 0
    ):
        raise JournalCodecError("turn must be null or a non-negative integer")
    kind = values.get("kind")
    if kind not in RECORD_KINDS:
        raise JournalCodecError(f"unsupported journal record kind: {kind!r}")
    if not isinstance(values.get("payload"), dict):
        raise JournalCodecError("payload must be an object")
    previous_hash = values.get("previous_hash")
    if previous_hash is not None and (
        not isinstance(previous_hash, str) or not _HASH_PATTERN.fullmatch(previous_hash)
    ):
        raise JournalCodecError("previous_hash must be null or lowercase SHA-256")
    if require_hash:
        record_hash = values.get("record_hash")
        if not isinstance(record_hash, str) or not _HASH_PATTERN.fullmatch(record_hash):
            raise JournalCodecError("record_hash must be lowercase SHA-256")
    try:
        _canonical_bytes(values.get("payload"))
    except (TypeError, ValueError) as error:
        raise JournalCodecError(f"payload is not canonical JSON data: {error}") from error


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise JournalCodecError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise JournalCodecError(f"invalid JSON constant: {value}")
