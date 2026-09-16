from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .store import JournalStore


@dataclass(frozen=True)
class JournalReplayEvent:
    schema_version: int
    sequence: int
    match_id: str
    bridge_session_id: str | None
    captured_at: str
    turn: int | None
    kind: str
    payload: dict[str, Any]
    previous_hash: str | None
    record_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def replay_journal(path: Path) -> tuple[JournalReplayEvent, ...]:
    records = JournalStore.open(path).read_all()
    return tuple(
        JournalReplayEvent(
            schema_version=record.schema_version,
            sequence=record.sequence,
            match_id=record.match_id,
            bridge_session_id=record.bridge_session_id,
            captured_at=record.captured_at,
            turn=record.turn,
            kind=record.kind,
            payload=deepcopy(record.payload),
            previous_hash=record.previous_hash,
            record_hash=record.record_hash,
        )
        for record in records
    )
