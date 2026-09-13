import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from civ5_agent.preflight import (
    CIV_EXECUTABLE,
    SafetyStatus,
    UnsafeSessionError,
    _parse_civ_rule,
    _parse_firewall_enabled,
    _phase_issues,
    _read_firetuner_enabled,
    require_safe_phase,
    require_safe_tuner_session,
)


class PreflightParsingTest(unittest.TestCase):
    def test_reads_exactly_one_firetuner_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.ini"
            config.write_text("EnableTuner = 1\nLoggingEnabled = 0\n")
            self.assertTrue(_read_firetuner_enabled(config))
            config.write_text("EnableTuner = 0\nEnableTuner = 1\n")
            with self.assertRaisesRegex(ValueError, "expected one"):
                _read_firetuner_enabled(config)

    def test_parses_firewall_state(self):
        self.assertTrue(_parse_firewall_enabled("Firewall is enabled. (State = 1)"))
        self.assertFalse(_parse_firewall_enabled("Firewall is disabled. (State = 0)"))

    def test_requires_explicit_block_rule(self):
        blocked = f"1 : {CIV_EXECUTABLE}\n             (Block incoming connections)\n"
        allowed = f"1 : {CIV_EXECUTABLE}\n             (Allow incoming connections)\n"
        self.assertEqual(_parse_civ_rule(blocked, CIV_EXECUTABLE), (True, True))
        self.assertEqual(_parse_civ_rule(allowed, CIV_EXECUTABLE), (True, False))
        self.assertEqual(
            _parse_civ_rule("Total number of apps = 0\n", CIV_EXECUTABLE),
            (False, False),
        )


class PreflightPolicyTest(unittest.TestCase):
    def test_live_requires_every_network_guard(self):
        status = SafetyStatus(
            phase="live",
            firetuner_enabled=True,
            firewall_enabled=True,
            civ_rule_present=True,
            civ_incoming_blocked=True,
            port_4318_listening=True,
            agent_socket_present=False,
        )
        self.assertEqual(_phase_issues(status), [])
        status.civ_incoming_blocked = False
        self.assertIn("explicit block-incoming", " ".join(_phase_issues(status)))

    def test_shutdown_requires_closed_transport(self):
        status = SafetyStatus(
            phase="shutdown",
            firetuner_enabled=False,
            port_4318_listening=False,
            agent_socket_present=False,
        )
        self.assertEqual(_phase_issues(status), [])
        status.port_4318_listening = True
        self.assertIn("4318", " ".join(_phase_issues(status)))

    def test_required_phase_raises_with_all_issues(self):
        with patch(
            "civ5_agent.preflight.inspect_safety",
            return_value=SafetyStatus(
                phase="live",
                issues=["firewall disabled", "rule absent"],
            ),
        ):
            with self.assertRaisesRegex(
                UnsafeSessionError,
                "firewall disabled; rule absent",
            ):
                require_safe_phase("live")

    def test_rejects_unverified_tuner_endpoint_before_inspection(self):
        with patch("civ5_agent.preflight.inspect_safety") as inspect:
            with self.assertRaisesRegex(UnsafeSessionError, "verified local"):
                require_safe_tuner_session("192.0.2.1", 4318)
        inspect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
