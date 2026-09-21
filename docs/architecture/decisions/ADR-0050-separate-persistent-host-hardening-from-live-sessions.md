# ADR-0050: Separate persistent host hardening from live sessions

Status: Accepted

Date: 2026-09-21

## Context

FireTuner on the target Campaign Edition build listens on every IPv4 interface
and exposes an unauthenticated Lua execution endpoint. The established safety
guard enables the macOS application firewall and gives Civilization V an
explicit block-incoming rule before FireTuner is enabled.

The original recoverable session manager treated all three settings as one
bounded transaction. On a host whose baseline firewall was disabled and had no
Civ V rule, every test added the rule, enabled the firewall, enabled FireTuner,
then removed the rule and disabled the firewall at shutdown. This was safe and
recoverable but imposed repeated administrator interaction during sustained
development.

Leaving the firewall disabled because the host uses a home network is not an
acceptable replacement. Other local devices, guests, VPN peers, or compromised
devices can still reach a wildcard listener.

## Decision

Provide two independent, explicit lifecycles in the provisional
`civ5_agent.live_session` operations CLI:

1. `harden` records the exact firewall/rule baseline in a private mode-0600
   recovery file, enables the macOS application firewall, installs or changes
   the Civ V rule to block incoming connections, and verifies the idle
   `hardened` phase. `unharden` restores that exact recorded firewall/rule
   baseline only when no live session, game listener, watcher socket, or
   enabled FireTuner remains.
2. `prepare` and `restore` continue to record and restore a per-session
   baseline. When persistent hardening is recorded, `prepare` first verifies
   that the guard has not drifted; the session then changes only FireTuner, and
   `restore` leaves the firewall and Civ V rule in their hardened state.

The prior temporary session behavior remains available when no persistent
hardening record exists. This preserves recovery compatibility while making
the persistent guard the recommended development workflow.

The `hardened` preflight phase requires FireTuner disabled, no TCP 4318
listener, no watcher socket, the firewall enabled, and an explicit Civ V
block-incoming rule. Ordinary Codex sandboxes may report a false disabled/empty
`socketfilterfw` view; all hardening mutations and authoritative checks run in
the interactive host context.

## Consequences

- Routine test preparation and restoration no longer require firewall
  mutations after the one-time hardening succeeds.
- The global application firewall remains enabled between tests and may affect
  unrelated applications; this is visible, intentional host state.
- The original host state remains recoverable through `unharden`. Losing or
  manually editing the private baseline must fail closed rather than infer an
  earlier state.
- FireTuner still remains session-scoped and disabled while idle. Persistent
  hardening does not authorize leaving the Lua endpoint active.
- Offline tests cover persistence, idempotence, drift rejection, session
  preservation, exact rollback, and active-session refusal. Target-machine
  evidence is still required before calling the new workflow live-verified.

## Alternatives considered

- Leave FireTuner enabled on a home network with the firewall disabled:
  rejected because the endpoint is unauthenticated and broadly bound.
- Continue changing firewall state on every test: retained as a compatibility
  fallback, but not preferred for sustained development.
- Permanently enable FireTuner as well as the firewall guard: rejected because
  defense in depth requires closing the endpoint when no test is active.

