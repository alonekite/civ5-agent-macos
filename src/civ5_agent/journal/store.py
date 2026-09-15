from __future__ import annotations

import fcntl
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..identity import (
    new_match_id,
    validate_bridge_session_id,
    validate_match_id,
)
from .codec import (
    MAX_RECORD_BYTES,
    JournalCodecError,
    build_record,
    decode_record,
    encode_record,
)
from .models import JournalRecord

_LIVE_RECORD_KINDS = frozenset(
    {
        "snapshot",
        "turn_transition",
        "command_submitted",
        "command_result",
        "verification_error",
    }
)
_APPENDABLE_RECORD_KINDS = _LIVE_RECORD_KINDS | {"correction"}


class JournalError(ValueError):
    pass


class JournalStore:
    def __init__(self, path: Path, match_id: str):
        self.path = path
        self.match_id = validate_match_id(match_id)

    @classmethod
    def create(
        cls,
        path: Path,
        initial_bridge_session_id: str,
        *,
        match_id: str | None = None,
    ) -> JournalStore:
        session_id = validate_bridge_session_id(initial_bridge_session_id)
        normalized_match_id = validate_match_id(match_id or new_match_id())
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = _open_new(path)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            record = build_record(
                sequence=0,
                match_id=normalized_match_id,
                bridge_session_id=session_id,
                captured_at=_utc_now(),
                turn=None,
                kind="journal_started",
                payload={},
                previous_hash=None,
            )
            _write_all(fd, encode_record(record))
            os.fsync(fd)
        finally:
            os.close(fd)
        return cls(path, normalized_match_id)

    @classmethod
    def open(cls, path: Path) -> JournalStore:
        fd = _open_existing(path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            records, _ = _read_verified(fd)
        finally:
            os.close(fd)
        if not records:
            raise JournalError("journal is empty")
        return cls(path, records[0].match_id)

    def read_all(self) -> tuple[JournalRecord, ...]:
        fd = _open_existing(self.path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            records, _ = _read_verified(fd)
        finally:
            os.close(fd)
        self._require_match(records)
        return tuple(records)

    def append(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        bridge_session_id: str | None = None,
        turn: int | None = None,
    ) -> JournalRecord:
        if kind not in _APPENDABLE_RECORD_KINDS:
            raise JournalError(f"record kind must use a dedicated operation: {kind!r}")
        session_id = (
            validate_bridge_session_id(bridge_session_id)
            if bridge_session_id is not None
            else None
        )
        if kind in _LIVE_RECORD_KINDS and session_id is None:
            raise JournalError(f"{kind} requires bridge_session_id")
        if kind in _LIVE_RECORD_KINDS and turn is None:
            raise JournalError(f"{kind} requires turn")
        return self._append_locked(kind, payload, session_id, turn)

    def bind_session(
        self,
        bridge_session_id: str,
        *,
        authority: str = "operator",
    ) -> JournalRecord:
        session_id = validate_bridge_session_id(bridge_session_id)
        if authority != "operator":
            raise JournalError("binding authority must be 'operator'")
        return self._append_locked(
            "session_binding",
            {"authority": authority},
            session_id,
            None,
        )

    def _append_locked(
        self,
        kind: str,
        payload: dict[str, Any],
        bridge_session_id: str | None,
        turn: int | None,
    ) -> JournalRecord:
        fd = _open_existing(self.path, os.O_RDWR | os.O_APPEND)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            records, bound_sessions = _read_verified(fd)
            self._require_match(records)
            if kind == "session_binding":
                if bridge_session_id in bound_sessions:
                    raise JournalError("bridge session is already bound to this journal")
            elif bridge_session_id is not None and bridge_session_id not in bound_sessions:
                raise JournalError("bridge session is not bound to this journal")
            prior_turn = next(
                (record.turn for record in reversed(records) if record.turn is not None),
                None,
            )
            if turn is not None and prior_turn is not None and turn < prior_turn:
                raise JournalError("journal turn cannot move backwards")
            if kind == "correction":
                supersedes = payload.get("supersedes_sequence")
                if (
                    isinstance(supersedes, bool)
                    or not isinstance(supersedes, int)
                    or supersedes < 0
                    or supersedes >= len(records)
                ):
                    raise JournalError(
                        "correction requires an existing supersedes_sequence"
                    )
            record = build_record(
                sequence=len(records),
                match_id=self.match_id,
                bridge_session_id=bridge_session_id,
                captured_at=_utc_now(),
                turn=turn,
                kind=kind,
                payload=payload,
                previous_hash=records[-1].record_hash,
            )
            _write_all(fd, encode_record(record))
            os.fsync(fd)
            return record
        except JournalCodecError as error:
            raise JournalError(str(error)) from error
        finally:
            os.close(fd)

    def _require_match(self, records: list[JournalRecord]) -> None:
        if not records or records[0].match_id != self.match_id:
            raise JournalError("journal match_id changed")


def _read_verified(fd: int) -> tuple[list[JournalRecord], set[str]]:
    os.lseek(fd, 0, os.SEEK_SET)
    records: list[JournalRecord] = []
    bound_sessions: set[str] = set()
    last_turn: int | None = None
    with os.fdopen(os.dup(fd), "rb") as stream:
        while True:
            line = stream.readline(MAX_RECORD_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_RECORD_BYTES:
                raise JournalError("journal record exceeds maximum size")
            try:
                record = decode_record(line)
            except JournalCodecError as error:
                raise JournalError(str(error)) from error
            expected_sequence = len(records)
            if record.sequence != expected_sequence:
                raise JournalError("journal sequence is not contiguous")
            if records:
                if record.match_id != records[0].match_id:
                    raise JournalError("journal mixes match identities")
                if record.previous_hash != records[-1].record_hash:
                    raise JournalError("journal integrity chain is broken")
                if record.kind == "journal_started":
                    raise JournalError("journal_started must be the first record")
            else:
                if record.kind != "journal_started":
                    raise JournalError("first journal record must be journal_started")
                if record.previous_hash is not None:
                    raise JournalError("first journal record cannot have previous_hash")
                if record.bridge_session_id is None:
                    raise JournalError("journal_started requires bridge_session_id")
            if record.kind == "session_binding":
                if record.bridge_session_id is None:
                    raise JournalError("session_binding requires bridge_session_id")
                if record.turn is not None or set(record.payload) != {"authority"}:
                    raise JournalError("invalid session_binding payload")
                if record.bridge_session_id in bound_sessions:
                    raise JournalError("bridge session is bound more than once")
                authority = record.payload.get("authority")
                if authority != "operator":
                    raise JournalError("invalid session binding authority")
                bound_sessions.add(record.bridge_session_id)
            elif record.kind == "journal_started":
                if record.turn is not None or record.payload:
                    raise JournalError("invalid journal_started payload")
                bound_sessions.add(record.bridge_session_id)
            elif record.kind in _LIVE_RECORD_KINDS:
                if record.bridge_session_id not in bound_sessions:
                    raise JournalError("record uses an unbound bridge session")
                if record.turn is None:
                    raise JournalError("live journal record requires turn")
            elif record.kind == "correction":
                supersedes = record.payload.get("supersedes_sequence")
                if (
                    isinstance(supersedes, bool)
                    or not isinstance(supersedes, int)
                    or supersedes < 0
                    or supersedes >= record.sequence
                ):
                    raise JournalError(
                        "correction requires an existing supersedes_sequence"
                    )
            if record.turn is not None:
                if last_turn is not None and record.turn < last_turn:
                    raise JournalError("journal turn moves backwards")
                last_turn = record.turn
            records.append(record)
    if not records:
        raise JournalError("journal is empty")
    return records, bound_sessions


def _open_new(path: Path) -> int:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    return _open(path, flags)


def _open_existing(path: Path, flags: int) -> int:
    return _open(path, flags)


def _open(path: Path, flags: int) -> int:
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as error:
        raise JournalError(f"cannot open journal: {error}") from error
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise JournalError("journal path is not a regular file")
    os.fchmod(fd, 0o600)
    return fd


def _write_all(fd: int, encoded: bytes) -> None:
    view = memoryview(encoded)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise JournalError("journal append made no progress")
        view = view[written:]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
