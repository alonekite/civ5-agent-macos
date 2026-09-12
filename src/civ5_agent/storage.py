from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .models import GameState


READ_PROBE_MOD_ID = "7e554a47-61c0-4a17-89a6-3e0acf3bd989"
READ_PROBE_VERSION = 1


def default_user_data_dir() -> Path:
    return (
        Path.home()
        / "Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support"
        / "Civilization V Campaign Edition"
    )


def default_state_database() -> Path:
    return (
        default_user_data_dir()
        / "ModUserData"
        / f"{READ_PROBE_MOD_ID}-{READ_PROBE_VERSION}.db"
    )


class UserDataStateReader:
    """Read Civ V ModUserData without ever creating or modifying its database."""

    def __init__(self, database: Path | str | None = None):
        self.database = Path(database) if database is not None else default_state_database()

    def read_values(self) -> dict[str, Any]:
        if not self.database.is_file():
            raise FileNotFoundError(self.database)

        uri = f"{self.database.resolve().as_uri()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=1.0)) as connection:
            rows = connection.execute("SELECT Name, Value FROM SimpleValues").fetchall()
        return dict(rows)

    def read_state(self) -> GameState:
        values = self.read_values()
        return GameState(
            turn=_optional_int(values.get("turn")),
            active_player=_optional_int(values.get("active_player")),
            gold=_optional_int(values.get("gold")),
        )


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
