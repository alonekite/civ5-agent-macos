from __future__ import annotations

import json
import os
import stat
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .store import JournalError, JournalStore

REDACTED_EXPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RedactedExportReport:
    export_schema_version: int
    record_count: int
    first_turn: int | None
    last_turn: int | None
    kind_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def export_redacted_journal(
    source: Path,
    destination: Path,
) -> RedactedExportReport:
    records = JournalStore.open(source).read_all()
    turns = [record.turn for record in records if record.turn is not None]
    counts = dict(sorted(Counter(record.kind for record in records).items()))
    report = RedactedExportReport(
        export_schema_version=REDACTED_EXPORT_SCHEMA_VERSION,
        record_count=len(records),
        first_turn=turns[0] if turns else None,
        last_turn=turns[-1] if turns else None,
        kind_counts=counts,
    )
    document = {
        **report.to_dict(),
        "events": [
            {
                "sequence": record.sequence,
                "turn": record.turn,
                "kind": record.kind,
            }
            for record in records
        ],
    }
    encoded = (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    _write_private_new(destination, encoded)
    return report


def _write_private_new(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as error:
        raise JournalError(f"cannot create journal export: {error}") from error
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise JournalError("journal export path is not a regular file")
        os.fchmod(fd, 0o600)
        view = memoryview(encoded)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise JournalError("journal export write made no progress")
            view = view[written:]
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    else:
        os.close(fd)
