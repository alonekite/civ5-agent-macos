from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JournalRecord:
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
