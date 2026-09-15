# ADR-0018: Keep deterministic execution independent of ruleset knowledge

Status: Accepted

Date: 2026-09-16

## Context

ADR-0014 moved scalar composition and decision support out of M4, but still
allowed a deterministic controller to query structural knowledge for validation.
After M6 was redefined as an executor of an explicit TurnPlan, that permission
became both unnecessary and misleading. It suggests that execution may derive
legality or plan content from static rules instead of authoritative live game
state and the verified action contract.

## Decision

M6 depends only on bridge session, live-state, and command contracts. It does
not import or query M4 structural knowledge.

- Stable identifier syntax, ownership, live capability, and action legality are
  checked by the bridge before every write.
- A human or future tactical/strategic/vertical-skill plan producer may query
  knowledge to choose explicit TurnPlan content.
- M6 treats plan identifiers as requested command arguments; it never repairs,
  substitutes, scores, or expands them from ruleset facts.
- If a future bridge action requires static data for safe validation, that data
  must be added to the bridge action contract or supplied as an explicit,
  verified precondition. It does not create a general M6-to-knowledge
  dependency.

## Consequences

- The milestone dependency remains M6 → M2, with no M4 or M5 edge.
- Live Civ V capability and write-after-read evidence outrank static knowledge.
- Plans remain reproducible inputs whose decisions can be inspected separately
  from mechanical execution.
- M4 stays useful to future decision support without becoming part of the
  write-safety path.

## Alternatives considered

- Let M6 validate every identifier through M4: rejected because the loaded
  ruleset view may be absent, stale, or different from live capability.
- Let M6 use M4 only as a fallback: rejected because fallback legality creates
  two execution authorities.
- Remove knowledge entirely: rejected because it remains valuable to future
  plan producers and offline analysis.

## Supersedes

This ADR supersedes ADR-0014's allowance for the deterministic controller to
query structural knowledge for validation. ADR-0014's structural-view and
decision-support boundaries otherwise remain accepted.
