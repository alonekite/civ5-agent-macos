from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace

from .identity import validate_bridge_session_id
from .models import CommandResult, GameState
from .turn_plan import (
    EXECUTION_REPORT_SCHEMA_VERSION,
    MAX_PLAN_ACTIONS,
    MAX_REPORT_MESSAGE_LENGTH,
    ExecutionReport,
    ExecutionEvent,
    ExecutionStepReport,
    PlannedAction,
    StaleTurnPlanError,
    TurnPlan,
    TurnPlanError,
    live_state_digest,
    validate_execution_report,
    validate_execution_event,
    validate_turn_plan,
)
from .turn_requirements import TurnRequirement, inspect_turn_requirements
from .validation import validate_live_state

StateReader = Callable[[], tuple[str, GameState]]
ActionExecutor = Callable[[PlannedAction, str], CommandResult]
OutcomeLookup = Callable[[PlannedAction, str], CommandResult | None]
EventSink = Callable[[ExecutionEvent], None]


def execute_turn_plan(
    plan: TurnPlan,
    read_state: StateReader,
    execute_action: ActionExecutor,
    event_sink: EventSink | None = None,
) -> ExecutionReport:
    emitter = _EventEmitter(plan, event_sink)
    emitter.emit("plan_received", reason_code="plan_received", message="plan received")

    def observed_action_executor(
        action: PlannedAction,
        session_id: str,
    ) -> CommandResult:
        index = plan.actions.index(action)
        emitter.emit(
            "action_started",
            action_index=index,
            action=action,
            reason_code="action_started",
            message="planned action submitted to bridge",
        )
        try:
            result = execute_action(action, session_id)
        except (OSError, TimeoutError, ConnectionError):
            emitter.emit(
                "action_outcome_unknown",
                action_index=index,
                action=action,
                reason_code="action_outcome_unknown",
                message="bridge outcome is unknown",
            )
            raise
        except (TypeError, ValueError) as error:
            emitter.emit(
                "action_rejected",
                action_index=index,
                action=action,
                reason_code="action_rejected",
                message=str(error),
            )
            raise
        emitter.emit(
            "action_result_received",
            action_index=index,
            action=action,
            reason_code="action_result_received",
            message=result.message if isinstance(result.message, str) else "invalid result",
        )
        return result

    report = _execute_turn_plan_core(plan, read_state, observed_action_executor)
    emitter.emit(
        report.status,
        reason_code=report.reason_code,
        message=report.message,
    )
    report = replace(report, event_sink_errors=tuple(emitter.errors))
    try:
        return validate_execution_report(report, plan)
    except TurnPlanError:
        return report


def reconcile_turn_plan(
    plan: TurnPlan,
    report: ExecutionReport,
    read_state: StateReader,
    lookup_result: OutcomeLookup,
) -> ExecutionReport:
    report = validate_execution_report(report, plan)
    if report.status != "recovery_required":
        raise TurnPlanError("only a recovery_required report can be reconciled")
    if report.next_action_index >= len(plan.actions):
        raise TurnPlanError("recovery report has no uncertain action")

    index = report.next_action_index
    action = plan.actions[index]
    expected_before_digest = (
        plan.state_basis_digest
        if index == 0
        else report.steps[-1].after_state_digest
    )
    if expected_before_digest is None:
        raise TurnPlanError("recovery report lacks the last verified state basis")
    try:
        result = lookup_result(action, plan.bridge_session_id)
    except (OSError, TimeoutError, ConnectionError, TypeError, ValueError) as error:
        return _preserve_event_errors(
            _report(
                plan,
                "recovery_required",
                index,
                report.steps,
                "recovery_lookup_unavailable",
                str(error),
            ),
            report,
            plan,
        )
    if result is None:
        return _preserve_event_errors(
            _report(
                plan,
                "recovery_required",
                index,
                report.steps,
                "command_result_unavailable",
                "watcher has no terminal result for the uncertain command",
            ),
            report,
            plan,
        )
    try:
        step, after_state = _validated_step(
            index,
            action,
            result,
            expected_before_digest,
        )
    except (TypeError, ValueError) as error:
        return _preserve_event_errors(
            _report(
                plan,
                "recovery_required",
                index,
                report.steps,
                "invalid_recovery_evidence",
                str(error),
            ),
            report,
            plan,
        )

    recovered_steps = (*report.steps, step)
    if step.status == "error":
        return _preserve_event_errors(
            _report(
                plan,
                "failed",
                index,
                recovered_steps,
                "action_failed",
                step.message,
            ),
            report,
            plan,
        )
    postcondition_error = _action_postcondition_error(plan, action, after_state)
    if postcondition_error is not None:
        return _preserve_event_errors(
            _report(
                plan,
                "recovery_required",
                index,
                report.steps,
                "invalid_recovery_evidence",
                postcondition_error,
            ),
            report,
            plan,
        )

    next_index = index + 1
    try:
        session_id, current_state = _read_validated_state(read_state)
    except (OSError, TimeoutError, ConnectionError, TypeError, ValueError) as error:
        return _preserve_event_errors(
            _report(
                plan,
                "paused",
                next_index,
                recovered_steps,
                "state_unavailable",
                str(error),
            ),
            report,
            plan,
        )
    if session_id != plan.bridge_session_id:
        return _preserve_event_errors(
            _report(
                plan,
                "stale",
                next_index,
                recovered_steps,
                "bridge_session_changed",
                "bridge session changed after cached result was recovered",
            ),
            report,
            plan,
        )
    if action.action == "end_turn":
        if current_state.turn <= plan.turn:
            return _preserve_event_errors(
                _report(
                    plan,
                    "stale",
                    next_index,
                    recovered_steps,
                    "state_drift",
                    "fresh state does not confirm the recovered turn advance",
                ),
                report,
                plan,
            )
        return _preserve_event_errors(
            _report(
                plan,
                "completed",
                next_index,
                recovered_steps,
                "turn_ended",
                "uncertain final end_turn was recovered and freshly confirmed",
            ),
            report,
            plan,
        )
    if live_state_digest(current_state) != live_state_digest(after_state):
        return _preserve_event_errors(
            _report(
                plan,
                "stale",
                next_index,
                recovered_steps,
                "state_drift",
                "fresh state differs from the recovered action result",
            ),
            report,
            plan,
        )
    return _preserve_event_errors(
        _report(
            plan,
            "paused",
            next_index,
            recovered_steps,
            "action_reconciled",
            "uncertain action succeeded and fresh state matches its result",
        ),
        report,
        plan,
    )


def _execute_turn_plan_core(
    plan: TurnPlan,
    read_state: StateReader,
    execute_action: ActionExecutor,
) -> ExecutionReport:
    try:
        session_id, state = _read_validated_state(read_state)
    except (OSError, TimeoutError, ConnectionError, TypeError, ValueError) as error:
        return _report(plan, "paused", 0, (), "state_unavailable", str(error))
    try:
        plan = validate_turn_plan(plan, state, session_id)
    except StaleTurnPlanError as error:
        return _report(plan, "stale", 0, (), "initial_state_stale", str(error))
    except (TypeError, ValueError, TurnPlanError) as error:
        return _report(plan, "failed", 0, (), "invalid_plan", str(error), no_step=True)

    steps: list[ExecutionStepReport] = []
    expected_digest = plan.state_basis_digest
    current_state = state
    for index, action in enumerate(plan.actions):
        if index > 0:
            try:
                session_id, current_state = _read_validated_state(read_state)
            except (OSError, TimeoutError, ConnectionError, TypeError, ValueError) as error:
                return _report(
                    plan,
                    "paused",
                    index,
                    tuple(steps),
                    "state_unavailable",
                    str(error),
                )
        stale_reason = _state_mismatch(plan, session_id, current_state, expected_digest)
        if stale_reason is not None:
            return _report(
                plan,
                "stale",
                index,
                tuple(steps),
                "state_drift",
                stale_reason,
            )

        requirements = inspect_turn_requirements(current_state)
        missing = _uncovered_requirement(requirements, plan.actions[index:])
        if missing is not None:
            return _report(
                plan,
                "paused",
                index,
                tuple(steps),
                "unresolved_requirement",
                _requirement_message(missing),
            )
        if action.action == "end_turn" and requirements:
            return _report(
                plan,
                "paused",
                index,
                tuple(steps),
                "turn_not_ready",
                _requirement_message(requirements[0]),
            )

        before_digest = live_state_digest(current_state)
        try:
            result = execute_action(action, session_id)
        except (OSError, TimeoutError, ConnectionError) as error:
            return _report(
                plan,
                "recovery_required",
                index,
                tuple(steps),
                "action_outcome_unknown",
                str(error),
            )
        except (TypeError, ValueError) as error:
            failed_step = ExecutionStepReport(
                index=index,
                command_id=action.command_id,
                action=action.action,
                status="error",
                message=str(error)[:MAX_REPORT_MESSAGE_LENGTH],
                before_state_digest=before_digest,
                after_state_digest=None,
            )
            return _report(
                plan,
                "failed",
                index,
                (*steps, failed_step),
                "action_rejected",
                str(error),
            )
        try:
            step, after_state = _validated_step(index, action, result, before_digest)
        except (TypeError, ValueError) as error:
            failed_step = ExecutionStepReport(
                index=index,
                command_id=action.command_id,
                action=action.action,
                status="error",
                message=str(error),
                before_state_digest=before_digest,
                after_state_digest=None,
            )
            return _report(
                plan,
                "failed",
                index,
                (*steps, failed_step),
                "invalid_action_result",
                str(error),
            )
        steps.append(step)
        if step.status == "error":
            return _report(
                plan,
                "failed",
                index,
                tuple(steps),
                "action_failed",
                step.message,
            )
        expected_digest = step.after_state_digest
        if action.action == "end_turn":
            if after_state.turn <= plan.turn:
                failed_step = ExecutionStepReport(
                    index=index,
                    command_id=action.command_id,
                    action=action.action,
                    status="error",
                    message="end_turn result did not advance the turn",
                    before_state_digest=before_digest,
                    after_state_digest=expected_digest,
                )
                return _report(
                    plan,
                    "failed",
                    index,
                    (*steps[:-1], failed_step),
                    "postcondition_failed",
                    failed_step.message,
                )
        elif (
            after_state.turn != plan.turn
            or after_state.active_player != plan.active_player
            or not after_state.turn_active
        ):
            failed_step = ExecutionStepReport(
                index=index,
                command_id=action.command_id,
                action=action.action,
                status="error",
                message="non-final action changed turn or active player",
                before_state_digest=before_digest,
                after_state_digest=expected_digest,
            )
            return _report(
                plan,
                "failed",
                index,
                (*steps[:-1], failed_step),
                "postcondition_failed",
                failed_step.message,
            )

    return _report(
        plan,
        "completed",
        len(plan.actions),
        tuple(steps),
        "turn_ended",
        "every planned action and final end_turn were verified",
    )


def _read_validated_state(read_state: StateReader) -> tuple[str, GameState]:
    session_id, state = read_state()
    return validate_bridge_session_id(session_id), validate_live_state(state)


def _state_mismatch(
    plan: TurnPlan,
    session_id: str,
    state: GameState,
    expected_digest: str,
) -> str | None:
    if session_id != plan.bridge_session_id:
        return "bridge session changed"
    if state.turn != plan.turn:
        return "turn changed before the planned final end_turn"
    if state.active_player != plan.active_player:
        return "active player changed"
    if not state.turn_active:
        return "active player's turn is not active"
    if live_state_digest(state) != expected_digest:
        return "live state differs from the last verified state basis"
    return None


def _validated_step(
    index: int,
    action: PlannedAction,
    result: CommandResult,
    expected_before_digest: str,
) -> tuple[ExecutionStepReport, GameState]:
    if not isinstance(result, CommandResult):
        raise TypeError("action executor must return CommandResult")
    if result.id != action.command_id:
        raise ValueError("action result command id does not match TurnPlan")
    if result.status not in {"success", "error"}:
        raise ValueError("action result must be terminal")
    if (
        not isinstance(result.message, str)
        or len(result.message) > MAX_REPORT_MESSAGE_LENGTH
    ):
        raise ValueError("action result message is invalid or too long")
    if not isinstance(result.before, dict) or not isinstance(result.after, dict):
        raise ValueError("action result requires before and after live states")
    before_state = validate_live_state(GameState(**result.before))
    after_state = validate_live_state(GameState(**result.after))
    before_digest = live_state_digest(before_state)
    if before_digest != expected_before_digest:
        raise ValueError("action result before-state differs from executor observation")
    after_digest = live_state_digest(after_state)
    return (
        ExecutionStepReport(
            index=index,
            command_id=action.command_id,
            action=action.action,
            status=result.status,
            message=result.message,
            before_state_digest=before_digest,
            after_state_digest=after_digest,
        ),
        after_state,
    )


def _action_postcondition_error(
    plan: TurnPlan,
    action: PlannedAction,
    after_state: GameState,
) -> str | None:
    if action.action == "end_turn":
        if after_state.turn <= plan.turn:
            return "end_turn result did not advance the turn"
        return None
    if (
        after_state.turn != plan.turn
        or after_state.active_player != plan.active_player
        or not after_state.turn_active
    ):
        return "non-final action changed turn or active player"
    return None


def _uncovered_requirement(
    requirements: tuple[TurnRequirement, ...],
    remaining_actions: tuple[PlannedAction, ...],
) -> TurnRequirement | None:
    structured = [item for item in requirements if item.kind != "end_turn_blocked"]
    for requirement in structured:
        if not any(_action_covers(action, requirement) for action in remaining_actions):
            return requirement
    blocker = next(
        (item for item in requirements if item.kind == "end_turn_blocked"),
        None,
    )
    if blocker is not None and not structured:
        return blocker
    return None


def _action_covers(action: PlannedAction, requirement: TurnRequirement) -> bool:
    if requirement.kind == "research_choice":
        if (
            requirement.mode not in {"normal", "legacy_unknown"}
            or action.action != "choose_research"
        ):
            return False
        choice = action.arguments["tech_type"]
        return not requirement.candidates or choice in requirement.candidates
    if requirement.kind == "city_production":
        return (
            action.action == "set_city_production"
            and action.arguments["city_id"] == requirement.subject_id
        )
    if requirement.kind == "unit_orders":
        return (
            action.action == "skip_unit"
            and action.arguments["unit_id"] == requirement.subject_id
        )
    return False


def _requirement_message(requirement: TurnRequirement) -> str:
    values = asdict(requirement)
    details = ", ".join(
        f"{key}={value!r}"
        for key, value in values.items()
        if key != "kind" and value not in (None, (), [])
    )
    return requirement.kind if not details else f"{requirement.kind}: {details}"


def _report(
    plan: TurnPlan,
    status: str,
    next_action_index: int,
    steps: tuple[ExecutionStepReport, ...],
    reason_code: str,
    message: str,
    *,
    no_step: bool = False,
) -> ExecutionReport:
    report = ExecutionReport(
        schema_version=EXECUTION_REPORT_SCHEMA_VERSION,
        plan_id=getattr(plan, "plan_id", "00000000-0000-4000-8000-000000000000"),
        bridge_session_id=getattr(
            plan,
            "bridge_session_id",
            "00000000-0000-4000-8000-000000000000",
        ),
        status=status,
        next_action_index=next_action_index,
        steps=steps,
        reason_code=reason_code,
        message=str(message)[:1024],
    )
    if no_step:
        return report
    return validate_execution_report(report, plan)


def _preserve_event_errors(
    recovered: ExecutionReport,
    previous: ExecutionReport,
    plan: TurnPlan,
) -> ExecutionReport:
    return validate_execution_report(
        replace(recovered, event_sink_errors=previous.event_sink_errors),
        plan,
    )


class _EventEmitter:
    def __init__(self, plan: TurnPlan, sink: EventSink | None):
        self.plan = plan
        self.sink = sink
        self.errors: list[str] = []

    def emit(
        self,
        kind: str,
        *,
        reason_code: str,
        message: str,
        action_index: int | None = None,
        action: PlannedAction | None = None,
    ) -> None:
        if self.sink is None:
            return
        try:
            event = validate_execution_event(
                ExecutionEvent(
                    schema_version=EXECUTION_REPORT_SCHEMA_VERSION,
                    plan_id=self.plan.plan_id,
                    bridge_session_id=self.plan.bridge_session_id,
                    kind=kind,
                    action_index=action_index,
                    command_id=action.command_id if action is not None else None,
                    reason_code=reason_code,
                    message=str(message)[:1024],
                )
            )
            self.sink(event)
        except Exception as error:  # optional sink must not affect execution
            if len(self.errors) < (MAX_PLAN_ACTIONS * 2 + 2):
                self.errors.append(str(error)[:1024])
