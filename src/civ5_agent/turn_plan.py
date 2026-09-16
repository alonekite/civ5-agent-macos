from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .identity import (
    new_plan_id,
    validate_bridge_session_id,
    validate_command_id,
    validate_plan_id,
)
from .models import GameState
from .validation import validate_live_state

TURN_PLAN_SCHEMA_VERSION = 1
EXECUTION_REPORT_SCHEMA_VERSION = 1
MAX_PLAN_ACTIONS = 64
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_TECH_PATTERN = re.compile(r"TECH_[A-Z0-9_]+\Z")
_PRODUCTION_PATTERNS = {
    "unit": re.compile(r"UNIT_[A-Z0-9_]+\Z"),
    "building": re.compile(r"BUILDING_[A-Z0-9_]+\Z"),
    "project": re.compile(r"PROJECT_[A-Z0-9_]+\Z"),
}
_ACTIONS = frozenset(
    {"end_turn", "choose_research", "set_city_production", "skip_unit"}
)
_REPORT_STATUSES = frozenset(
    {"completed", "paused", "stale", "failed", "recovery_required"}
)
_REASON_CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
MAX_REPORT_MESSAGE_LENGTH = 1024


class TurnPlanError(ValueError):
    pass


class StaleTurnPlanError(TurnPlanError):
    pass


@dataclass(frozen=True)
class PlannedAction:
    command_id: str
    action: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class TurnPlan:
    schema_version: int
    plan_id: str
    bridge_session_id: str
    turn: int
    active_player: int
    state_basis_digest: str
    actions: tuple[PlannedAction, ...]


@dataclass(frozen=True)
class ExecutionStepReport:
    index: int
    command_id: str
    action: str
    status: Literal["success", "error"]
    message: str
    before_state_digest: str | None
    after_state_digest: str | None


@dataclass(frozen=True)
class ExecutionReport:
    schema_version: int
    plan_id: str
    bridge_session_id: str
    status: Literal[
        "completed",
        "paused",
        "stale",
        "failed",
        "recovery_required",
    ]
    next_action_index: int
    steps: tuple[ExecutionStepReport, ...]
    reason_code: str
    message: str
    event_sink_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionEvent:
    schema_version: int
    plan_id: str
    bridge_session_id: str
    kind: Literal[
        "plan_received",
        "action_started",
        "action_result_received",
        "action_rejected",
        "action_outcome_unknown",
        "completed",
        "paused",
        "stale",
        "failed",
        "recovery_required",
    ]
    action_index: int | None
    command_id: str | None
    reason_code: str
    message: str


def live_state_digest(state: GameState) -> str:
    validated = validate_live_state(state)
    encoded = json.dumps(
        asdict(validated),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_turn_plan(
    state: GameState,
    bridge_session_id: str,
    actions: list[PlannedAction] | tuple[PlannedAction, ...],
    *,
    plan_id: str | None = None,
) -> TurnPlan:
    validated = validate_live_state(state)
    plan = TurnPlan(
        schema_version=TURN_PLAN_SCHEMA_VERSION,
        plan_id=plan_id or new_plan_id(),
        bridge_session_id=validate_bridge_session_id(bridge_session_id),
        turn=validated.turn,
        active_player=validated.active_player,
        state_basis_digest=live_state_digest(validated),
        actions=tuple(actions),
    )
    return validate_turn_plan(plan, validated, bridge_session_id)


def validate_turn_plan(
    plan: TurnPlan,
    state: GameState,
    bridge_session_id: str,
) -> TurnPlan:
    normalized = validate_turn_plan_structure(plan)
    try:
        current_session = validate_bridge_session_id(bridge_session_id)
    except ValueError as error:
        raise TurnPlanError(str(error)) from error
    if normalized.bridge_session_id != current_session:
        raise StaleTurnPlanError("TurnPlan targets a different bridge session")
    validated = validate_live_state(state)
    if not validated.turn_active:
        raise StaleTurnPlanError("active player's turn is not active")
    if normalized.turn != validated.turn:
        raise StaleTurnPlanError("TurnPlan targets a different turn")
    if normalized.active_player != validated.active_player:
        raise StaleTurnPlanError("TurnPlan targets a different active player")
    if not hmac.compare_digest(
        normalized.state_basis_digest,
        live_state_digest(validated),
    ):
        raise StaleTurnPlanError("TurnPlan state basis does not match live state")
    return normalized


def validate_turn_plan_structure(plan: TurnPlan) -> TurnPlan:
    if not isinstance(plan, TurnPlan):
        raise TurnPlanError("plan must be a TurnPlan")
    if (
        isinstance(plan.schema_version, bool)
        or not isinstance(plan.schema_version, int)
        or plan.schema_version != TURN_PLAN_SCHEMA_VERSION
    ):
        raise TurnPlanError("unsupported TurnPlan schema_version")
    try:
        validate_plan_id(plan.plan_id)
        validate_bridge_session_id(plan.bridge_session_id)
    except ValueError as error:
        raise TurnPlanError(str(error)) from error
    for field in ("turn", "active_player"):
        value = getattr(plan, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise TurnPlanError(f"{field} must be a non-negative integer")
    if not isinstance(plan.state_basis_digest, str) or not _DIGEST_PATTERN.fullmatch(
        plan.state_basis_digest
    ):
        raise TurnPlanError("state_basis_digest must be lowercase SHA-256")
    if not isinstance(plan.actions, tuple):
        raise TurnPlanError("actions must be a tuple")
    if not plan.actions or len(plan.actions) > MAX_PLAN_ACTIONS:
        raise TurnPlanError(f"actions must contain 1 to {MAX_PLAN_ACTIONS} items")

    command_ids: set[str] = set()
    normalized_actions = []
    for index, action in enumerate(plan.actions):
        normalized = _validate_planned_action(action)
        if normalized.command_id in command_ids:
            raise TurnPlanError("command_id values must be unique within a plan")
        command_ids.add(normalized.command_id)
        if normalized.action == "end_turn" and index != len(plan.actions) - 1:
            raise TurnPlanError("end_turn must be the final action")
        normalized_actions.append(normalized)
    if normalized_actions[-1].action != "end_turn":
        raise TurnPlanError("complete-turn plan must end with end_turn")
    return TurnPlan(
        schema_version=plan.schema_version,
        plan_id=plan.plan_id,
        bridge_session_id=plan.bridge_session_id,
        turn=plan.turn,
        active_player=plan.active_player,
        state_basis_digest=plan.state_basis_digest,
        actions=tuple(normalized_actions),
    )


def turn_plan_from_dict(values: object) -> TurnPlan:
    if not isinstance(values, dict):
        raise TurnPlanError("TurnPlan JSON root must be an object")
    expected = {
        "schema_version",
        "plan_id",
        "bridge_session_id",
        "turn",
        "active_player",
        "state_basis_digest",
        "actions",
    }
    if set(values) != expected:
        raise TurnPlanError(f"TurnPlan fields must be exactly {sorted(expected)}")
    raw_actions = values["actions"]
    if not isinstance(raw_actions, list):
        raise TurnPlanError("TurnPlan actions must be a JSON array")
    if not raw_actions or len(raw_actions) > MAX_PLAN_ACTIONS:
        raise TurnPlanError(f"actions must contain 1 to {MAX_PLAN_ACTIONS} items")
    actions = []
    action_fields = {"command_id", "action", "arguments"}
    for raw_action in raw_actions:
        if not isinstance(raw_action, dict) or set(raw_action) != action_fields:
            raise TurnPlanError(
                f"PlannedAction fields must be exactly {sorted(action_fields)}"
            )
        actions.append(
            PlannedAction(
                command_id=raw_action["command_id"],
                action=raw_action["action"],
                arguments=raw_action["arguments"],
            )
        )
    return validate_turn_plan_structure(
        TurnPlan(
            schema_version=values["schema_version"],
            plan_id=values["plan_id"],
            bridge_session_id=values["bridge_session_id"],
            turn=values["turn"],
            active_player=values["active_player"],
            state_basis_digest=values["state_basis_digest"],
            actions=tuple(actions),
        )
    )


def validate_execution_report(
    report: ExecutionReport,
    plan: TurnPlan,
) -> ExecutionReport:
    if not isinstance(report, ExecutionReport):
        raise TurnPlanError("report must be an ExecutionReport")
    if (
        isinstance(report.schema_version, bool)
        or not isinstance(report.schema_version, int)
        or report.schema_version != EXECUTION_REPORT_SCHEMA_VERSION
    ):
        raise TurnPlanError("unsupported ExecutionReport schema_version")
    try:
        validate_plan_id(report.plan_id)
        validate_bridge_session_id(report.bridge_session_id)
    except ValueError as error:
        raise TurnPlanError(str(error)) from error
    if report.plan_id != plan.plan_id or report.bridge_session_id != plan.bridge_session_id:
        raise TurnPlanError("execution report identity does not match TurnPlan")
    if report.status not in _REPORT_STATUSES:
        raise TurnPlanError("unsupported execution report status")
    if (
        isinstance(report.next_action_index, bool)
        or not isinstance(report.next_action_index, int)
        or not 0 <= report.next_action_index <= len(plan.actions)
    ):
        raise TurnPlanError("next_action_index is outside the TurnPlan")
    if not isinstance(report.steps, tuple) or len(report.steps) > len(plan.actions):
        raise TurnPlanError("execution report steps exceed the TurnPlan")
    if (
        not isinstance(report.reason_code, str)
        or not _REASON_CODE_PATTERN.fullmatch(report.reason_code)
    ):
        raise TurnPlanError("reason_code must be a bounded snake-case identifier")
    if (
        not isinstance(report.message, str)
        or len(report.message) > MAX_REPORT_MESSAGE_LENGTH
    ):
        raise TurnPlanError("execution report message is invalid or too long")
    if (
        not isinstance(report.event_sink_errors, tuple)
        or len(report.event_sink_errors) > (MAX_PLAN_ACTIONS * 2 + 2)
        or any(
            not isinstance(error, str) or len(error) > MAX_REPORT_MESSAGE_LENGTH
            for error in report.event_sink_errors
        )
    ):
        raise TurnPlanError("event_sink_errors is invalid or unbounded")

    normalized_steps = []
    for index, step in enumerate(report.steps):
        if not isinstance(step, ExecutionStepReport) or step.index != index:
            raise TurnPlanError("execution report step indexes must be contiguous")
        planned = plan.actions[index]
        if step.command_id != planned.command_id or step.action != planned.action:
            raise TurnPlanError("execution report step does not match TurnPlan action")
        if step.status not in {"success", "error"}:
            raise TurnPlanError("unsupported execution step status")
        if not isinstance(step.message, str) or len(step.message) > MAX_REPORT_MESSAGE_LENGTH:
            raise TurnPlanError("execution step message is invalid or too long")
        for digest in (step.before_state_digest, step.after_state_digest):
            if digest is not None and (
                not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest)
            ):
                raise TurnPlanError("execution step digest must be lowercase SHA-256")
        normalized_steps.append(step)

    errors = [step for step in normalized_steps if step.status == "error"]
    if report.status == "completed":
        if (
            report.next_action_index != len(plan.actions)
            or len(normalized_steps) != len(plan.actions)
            or errors
        ):
            raise TurnPlanError("completed report requires every action to succeed")
    elif report.status == "failed":
        valid_pre_execution_failure = not normalized_steps and report.next_action_index == 0
        valid_action_failure = bool(normalized_steps) and (
            len(errors) == 1
            and normalized_steps[-1] is errors[0]
            and report.next_action_index == errors[0].index
            and all(step.status == "success" for step in normalized_steps[:-1])
        )
        if not (valid_pre_execution_failure or valid_action_failure):
            raise TurnPlanError("failed report requires one final failed step")
    elif errors or report.next_action_index != len(normalized_steps):
        raise TurnPlanError(
            "paused, stale, and recovery reports contain only completed steps"
        )
    return report


def validate_execution_event(event: ExecutionEvent) -> ExecutionEvent:
    if not isinstance(event, ExecutionEvent):
        raise TurnPlanError("event must be an ExecutionEvent")
    if (
        isinstance(event.schema_version, bool)
        or not isinstance(event.schema_version, int)
        or event.schema_version != EXECUTION_REPORT_SCHEMA_VERSION
    ):
        raise TurnPlanError("unsupported ExecutionEvent schema_version")
    try:
        validate_plan_id(event.plan_id)
        validate_bridge_session_id(event.bridge_session_id)
        if event.command_id is not None:
            validate_command_id(event.command_id)
    except ValueError as error:
        raise TurnPlanError(str(error)) from error
    if event.kind not in {
        "plan_received",
        "action_started",
        "action_result_received",
        "action_rejected",
        "action_outcome_unknown",
        "completed",
        "paused",
        "stale",
        "failed",
        "recovery_required",
    }:
        raise TurnPlanError("unsupported ExecutionEvent kind")
    if event.action_index is not None and (
        isinstance(event.action_index, bool)
        or not isinstance(event.action_index, int)
        or not 0 <= event.action_index < MAX_PLAN_ACTIONS
    ):
        raise TurnPlanError("execution event action_index is invalid")
    has_action = event.action_index is not None or event.command_id is not None
    if has_action != (event.action_index is not None and event.command_id is not None):
        raise TurnPlanError("execution event action identity must be complete")
    if (
        not isinstance(event.reason_code, str)
        or not _REASON_CODE_PATTERN.fullmatch(event.reason_code)
        or not isinstance(event.message, str)
        or len(event.message) > MAX_REPORT_MESSAGE_LENGTH
    ):
        raise TurnPlanError("execution event reason or message is invalid")
    return event


def _validate_planned_action(action: PlannedAction) -> PlannedAction:
    if not isinstance(action, PlannedAction):
        raise TurnPlanError("every action must be a PlannedAction")
    try:
        command_id = validate_command_id(action.command_id)
    except ValueError as error:
        raise TurnPlanError(str(error)) from error
    if action.action not in _ACTIONS:
        raise TurnPlanError(f"unsupported planned action: {action.action!r}")
    if not isinstance(action.arguments, dict):
        raise TurnPlanError("action arguments must be an object")
    arguments = dict(action.arguments)
    if action.action == "end_turn":
        _require_fields(arguments, set(), action.action)
    elif action.action == "choose_research":
        _require_fields(arguments, {"tech_type"}, action.action)
        tech_type = arguments["tech_type"]
        if not isinstance(tech_type, str) or not _TECH_PATTERN.fullmatch(tech_type):
            raise TurnPlanError("tech_type must match TECH_[A-Z0-9_]+")
    elif action.action == "set_city_production":
        _require_fields(arguments, {"city_id", "kind", "item_type"}, action.action)
        city_id = arguments["city_id"]
        if isinstance(city_id, bool) or not isinstance(city_id, int) or city_id < 0:
            raise TurnPlanError("city_id must be a non-negative integer")
        kind = arguments["kind"]
        pattern = _PRODUCTION_PATTERNS.get(kind) if isinstance(kind, str) else None
        if pattern is None:
            raise TurnPlanError("production kind must be unit, building, or project")
        item_type = arguments["item_type"]
        if not isinstance(item_type, str) or not pattern.fullmatch(item_type):
            raise TurnPlanError(f"{kind} item_type has an invalid format")
    else:
        _require_fields(arguments, {"unit_id"}, action.action)
        unit_id = arguments["unit_id"]
        if isinstance(unit_id, bool) or not isinstance(unit_id, int) or unit_id < 0:
            raise TurnPlanError("unit_id must be a non-negative integer")
    return PlannedAction(command_id, action.action, arguments)


def _require_fields(arguments: dict[str, Any], expected: set[str], action: str) -> None:
    if set(arguments) != expected:
        raise TurnPlanError(
            f"{action} argument fields must be exactly {sorted(expected)}"
        )
