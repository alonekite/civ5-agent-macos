from __future__ import annotations

from uuid import UUID, uuid4


class SessionIdentityError(ValueError):
    pass


def new_bridge_session_id() -> str:
    return str(uuid4())


def validate_bridge_session_id(value: object) -> str:
    if not isinstance(value, str):
        raise SessionIdentityError("bridge_session_id must be a canonical UUIDv4")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise SessionIdentityError(
            "bridge_session_id must be a canonical UUIDv4"
        ) from error
    if parsed.version != 4 or str(parsed) != value:
        raise SessionIdentityError("bridge_session_id must be a canonical UUIDv4")
    return value
