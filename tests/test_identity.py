import unittest
from unittest.mock import patch
from uuid import UUID

from civ5_agent.identity import (
    SessionIdentityError,
    new_bridge_session_id,
    validate_bridge_session_id,
)


class BridgeSessionIdentityTest(unittest.TestCase):
    def test_generates_canonical_uuid4(self):
        value = new_bridge_session_id()
        self.assertEqual(validate_bridge_session_id(value), value)

    def test_rejects_non_string_non_v4_and_noncanonical_values(self):
        invalid = [
            None,
            7,
            "not-a-uuid",
            "123e4567-e89b-12d3-a456-426614174000",
            "123E4567-E89B-42D3-A456-426614174000",
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(SessionIdentityError):
                    validate_bridge_session_id(value)

    def test_generation_does_not_reuse_identity(self):
        with patch(
            "civ5_agent.identity.uuid4",
            side_effect=[
                UUID("123e4567-e89b-42d3-a456-426614174000"),
                UUID("123e4567-e89b-42d3-a456-426614174001"),
            ],
        ):
            self.assertNotEqual(new_bridge_session_id(), new_bridge_session_id())


if __name__ == "__main__":
    unittest.main()
