from __future__ import annotations

from uuid import UUID, uuid4


class SessionIdentityError(ValueError):
    pass


def new_bridge_session_id() -> str:
    return str(uuid4())


def validate_bridge_session_id(value: object) -> str:
    return _validate_uuid4(value, "bridge_session_id")


def new_match_id() -> str:
    return str(uuid4())


def validate_match_id(value: object) -> str:
    return _validate_uuid4(value, "match_id")


def _validate_uuid4(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise SessionIdentityError(f"{label} must be a canonical UUIDv4")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise SessionIdentityError(f"{label} must be a canonical UUIDv4") from error
    if parsed.version != 4 or str(parsed) != value:
        raise SessionIdentityError(f"{label} must be a canonical UUIDv4")
    return value
