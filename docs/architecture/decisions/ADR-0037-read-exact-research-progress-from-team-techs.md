# ADR-0037: Read exact research progress from team technologies

Status: Accepted

Date: 2026-09-19

Supersedes: ADR-0035's research-progress binding and provenance only

## Context

ADR-0035 selected exact times-100 research progress as an authoritative schema
8 fact but assigned `GetResearchProgressTimes100` to `CvPlayer`. The first M11
C4 target attempt parsed a complete schema 8 state without a visible read side
effect, but correctly reported `runtime_api_binding_unavailable` because that
method is not exposed on the Campaign Edition `CvPlayer` Lua object.

A bounded read-only target diagnostic proved that science times-100, overflow,
effective cost, and turns-left are callable on `CvPlayer`. It also proved that
`GetResearchProgressTimes100` is callable on the active team's `CvTeamTechs`
object. The installed BNW UI likewise treats research progress as team
technology state. Whole-point player and team accessors returned different
values in the diagnostic state, so they are not interchangeable substitutes.

## Decision

Schema 8 reads candidate progress with:

```text
Teams[player:GetTeam()]:GetTeamTechs():GetResearchProgressTimes100(tech_id)
```

The public `field_provenance.progress_times100` value is
`CvTeamTechs.GetResearchProgressTimes100`. Capability detection checks that
method on the team-technologies object. Cost, science, overflow, turns-left,
phase, field names, units, support states, and candidate semantics remain
unchanged.

## Consequences

- The implementation matches the target Lua binding owner without weakening
  missing-binding failure behavior.
- Schema 8 and capability version 1 do not change because this corrects an
  unreleased binding/provenance defect rather than changing the fact's meaning.
- Schemas 2–7, every write path, TurnPlan, result, executor, and journal schema
  remain unchanged.
- The failed first C4 attempt is diagnostic evidence, not successful schema 8
  verification. The complete C4 procedure must be rerun on the corrected code.
- All generated programs must still fit the 1,000-byte FireTuner limit.

## Alternatives considered

- Use `CvPlayer.GetResearchProgress`: rejected because it is whole-point and
  returned a different value from team technology progress in the diagnostic
  state.
- Multiply a whole-point value by 100: rejected because representation changes
  do not create unobserved precision.
- Treat the missing player method as supported: rejected because partial facts
  must fail closed.
