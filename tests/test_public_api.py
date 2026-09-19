import unittest

import civ5_agent.api as api
from civ5_agent.actions import CommandValidationError
from civ5_agent.errors import (
    Civ5AgentError,
    SafetyError,
    ValidationError,
)
from civ5_agent.identity import SessionIdentityError
from civ5_agent.journal import JournalError
from civ5_agent.journal.codec import JournalCodecError
from civ5_agent.knowledge import KnowledgeValidationError, RulesetResolutionError
from civ5_agent.knowledge.import_sqlite import KnowledgeImportError
from civ5_agent.live_session import LiveSessionError
from civ5_agent.preflight import UnsafeSessionError
from civ5_agent.turn_plan import TurnPlanError
from civ5_agent.validation import StateValidationError


class PublicApiContractTest(unittest.TestCase):
    def test_every_declared_public_symbol_exists_once(self):
        self.assertEqual(len(api.__all__), len(set(api.__all__)))
        for name in api.__all__:
            self.assertTrue(hasattr(api, name), name)

    def test_implementation_internals_are_not_aggregated(self):
        for name in (
            "FireTunerClient",
            "LocalControlServer",
            "make_control_handler",
            "request",
        ):
            self.assertNotIn(name, api.__all__)
            self.assertFalse(hasattr(api, name))

    def test_validation_errors_share_supported_base_and_legacy_valueerror(self):
        errors = (
            CommandValidationError,
            SessionIdentityError,
            JournalCodecError,
            JournalError,
            KnowledgeImportError,
            KnowledgeValidationError,
            RulesetResolutionError,
            StateValidationError,
            TurnPlanError,
        )
        for error_type in errors:
            self.assertTrue(issubclass(error_type, ValidationError), error_type)
            self.assertTrue(issubclass(error_type, ValueError), error_type)
            self.assertTrue(issubclass(error_type, Civ5AgentError), error_type)

    def test_safety_errors_share_supported_base_and_legacy_runtimeerror(self):
        for error_type in (LiveSessionError, UnsafeSessionError):
            self.assertTrue(issubclass(error_type, SafetyError))
            self.assertTrue(issubclass(error_type, RuntimeError))

    def test_published_schema_and_size_constants_match_contract(self):
        self.assertIn("move_unit", api.ALLOWED_ACTIONS)
        self.assertIn("worker_build", api.ALLOWED_ACTIONS)
        self.assertEqual(
            api.SUPPORTED_LIVE_STATE_SCHEMA_VERSIONS,
            {2, 3, 4, 5, 6, 7, 8},
        )
        self.assertEqual(api.RESEARCH_RUNTIME_FACTS_CAPABILITY_VERSION, 1)
        self.assertFalse(hasattr(api, "RESEARCH_FORECAST_CAPABILITY_VERSION"))
        self.assertEqual(api.RUNTIME_CONTEXT_VERSION, 1)
        self.assertEqual(api.MAX_BUILD_IDENTIFIER_LENGTH, 64)
        self.assertEqual(api.MAX_ORDINARY_WORKER_BUILDS_PER_UNIT, 32)
        self.assertEqual(api.MAX_MAP_COORDINATE, 65_535)
        self.assertEqual(api.NO_END_TURN_BLOCKING_TYPE, -1)
        self.assertEqual(api.SUPPORTED_KNOWLEDGE_SCHEMA_VERSIONS, {1, 2, 3})
        self.assertEqual(api.JOURNAL_SCHEMA_VERSION, 1)
        self.assertEqual(api.TURN_PLAN_SCHEMA_VERSION, 1)
        self.assertEqual(api.EXECUTION_REPORT_SCHEMA_VERSION, 1)
        self.assertEqual(api.MAX_PLAN_ACTIONS, 64)
        self.assertEqual(api.MAX_COMMAND_MESSAGE_LENGTH, 1024)
        self.assertEqual(api.MAX_REPORT_MESSAGE_LENGTH, 1024)
        self.assertEqual(api.MAX_EVENT_SINK_ERRORS, 130)
        self.assertEqual(api.MAX_REQUEST_BYTES, 64 * 1024)
        self.assertEqual(api.MAX_RESPONSE_BYTES, 4 * 1024 * 1024)
        self.assertEqual(api.MAX_RECORD_BYTES, 4 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
