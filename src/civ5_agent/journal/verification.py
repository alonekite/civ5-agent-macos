from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .codec import JOURNAL_SCHEMA_VERSION
from .store import JournalStore


@dataclass(frozen=True)
class JournalVerification:
    schema_version: int
    match_id: str
    record_count: int
    first_turn: int | None
    last_turn: int | None
    bridge_session_count: int
    kind_counts: dict[str, int]
    head_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_journal(path: Path) -> JournalVerification:
    records = JournalStore.open(path).read_all()
    turns = [record.turn for record in records if record.turn is not None]
    sessions = {
        record.bridge_session_id
        for record in records
        if record.bridge_session_id is not None
    }
    counts = Counter(record.kind for record in records)
    return JournalVerification(
        schema_version=JOURNAL_SCHEMA_VERSION,
        match_id=records[0].match_id,
        record_count=len(records),
        first_turn=turns[0] if turns else None,
        last_turn=turns[-1] if turns else None,
        bridge_session_count=len(sessions),
        kind_counts=dict(sorted(counts.items())),
        head_hash=records[-1].record_hash,
    )
