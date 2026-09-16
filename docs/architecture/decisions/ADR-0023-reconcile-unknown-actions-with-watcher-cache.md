# ADR-0023: Reconcile unknown actions without automatic retry

Status: Accepted

Date: 2026-09-16

## Context

A client timeout after command submission does not prove whether Civ V applied
the action. Retrying because the outcome is unknown could apply the same intent
twice. M5 history and the M2 audit are optional evidence sinks, not execution
authority, while the current watcher already keeps terminal command results for
duplicate suppression during one bridge session.

## Decision

Recovery uses a read-only lookup keyed by the uncertain command UUID and current
bridge-session identity. The watcher serializes lookup with command execution and
returns a cached terminal result only from its current lifetime. M6 accepts that
result only when its action, exact arguments, command UUID, before-state basis,
and action-specific postcondition all match the TurnPlan and prior report.

M6 then reads and validates fresh live state. A recovered final `end_turn` may
complete the plan once fresh state confirms turn advance. A recovered non-final
success advances the factual report cursor but pauses before the next action; it
does not automatically continue the old plan. A plan producer may issue a new
plan from the fresh state.

A lookup miss, unavailable lookup, malformed evidence, replaced bridge session,
or contradictory fresh state never causes a retry. It remains
`recovery_required`, pauses, or becomes stale as appropriate. Recovery does not
read M5, parse the M2 audit, or infer an outcome from game-state similarity.

## Consequences

- An uncertain command is never resubmitted merely to discover its outcome.
- Recovery is deterministic and bounded while the original watcher cache and
  bridge session still exist.
- Watcher restart deliberately loses this recovery evidence; the outcome then
  remains unknown and requires conservative operator/plan-producer handling.
- Successfully recovered non-final actions do not silently resume subsequent
  writes, even when those actions were listed in the old plan.
- The journal remains suitable for audit and replay but cannot authorize an
  execution transition.

## Alternatives considered

- Retry the same UUID through the write endpoint: rejected because absence from
  a restarted or incomplete cache could execute an action again.
- Infer success solely from current state: rejected because multiple causes can
  produce the same observation and intermediate states can already have moved.
- Recover from M5 or the audit log: rejected because their writes may fail and
  neither is an execution-state authority.
- Automatically continue after a recovered non-final action: deferred because a
  fresh explicit plan is safer and keeps recovery separate from replanning.

## Supersedes

This finalizes the unknown-outcome policy left open by ADR-0015, ADR-0016, and
ADR-0022 without changing their module boundaries.
