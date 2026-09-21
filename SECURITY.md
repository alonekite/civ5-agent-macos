# Security

## FireTuner exposure

The tested Mac App Store Campaign Edition build listens on `TCP *:4318` when
FireTuner is enabled. This exposes the game's Lua execution interface on every
IPv4 network interface, not only `127.0.0.1`. The protocol has no authentication
observed by this project.

Only enable FireTuner for a bounded test. A home network is not a sufficient
security boundary: local, guest, VPN, or compromised peers may still reach the
host. Keep the macOS application firewall enabled, explicitly block incoming
connections to Civilization V, and verify the rule before starting the game. A
firewall rule is mitigation: the game still owns a wildcard listener.

For sustained development, create the persistent firewall guard once:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session harden
PYTHONPATH=src python3 -m civ5_agent.preflight hardened
```

The private hardening record preserves the original firewall/rule baseline for
an explicit later `unharden`. FireTuner is not part of the persistent state and
must remain disabled while idle.

Prepare a bounded session from the host environment:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
```

This records the original settings outside the repository, establishes and
verifies the guard, and rolls back on failure. A sandboxed process may see a
false disabled/empty firewall state, so it must not be used for this operation.
If the Civ V entry is absent, preparation adds and blocks it while the game and
FireTuner are stopped, then verifies the block before enabling FireTuner.
Run the read-only safety check again after the game starts:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight live
```

After every session:

1. quit Civilization V;
2. stop `civ5_agent.watch`;
3. run `PYTHONPATH=src python3 -m civ5_agent.live_session restore`;
4. verify no process listens on TCP 4318;
5. verify the per-user agent Unix socket is gone.

Steps 3–5 can be verified together with:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

The preflight command reports JSON and makes no system changes. The explicit
live-session restore command returns session settings to its private recorded
baseline and verifies the shutdown state. Under persistent hardening, this
disables FireTuner while intentionally retaining the firewall and Civ V block
rule; verify that stronger idle state with `preflight hardened`. See
[persistent host hardening](docs/operations/HOST_HARDENING.md) for exact
installation and rollback commands.

The watcher and direct command path enforce the live check automatically. The
watcher's local control socket rechecks it before each allowlisted write, so a
removed firewall rule prevents the game action. The bridge refuses FireTuner
hosts and ports other than the verified `127.0.0.1:4318` endpoint. The low-level
client enforces the same rule. The live-session manager accepts either the
executable path or the canonical `.app` path reported by macOS for the Civ V
firewall rule.

`civ5-watch --read-only` is a server-enforced execution-core boundary for an
external composition root. It admits only `ping` and `read_state`; completed-
command lookup and every write request are rejected before execution. Read-only
mode cannot capture a journal and does not launch, quit, or otherwise automate
the game application.

`civ5-read-only probe` fails closed unless the watcher declares this mode and
the state read remains in the same bridge session. Its summary excludes names,
IDs, coordinates, technology/resource names, diplomacy, and full state. The
generated external SessionSpec inherits no environment and requests no raw
output retention. SessionSpec files still contain local absolute paths and must
remain private, mode-0600 artifacts outside the repository. The independent
automation framework does not replace firewall preparation, live preflight, or
restoration.

The adopted optional supervisor is `local-app-test-automation` v0.1.0 at the
exact wheel digest recorded in the external automation contract. Verify that
digest before installation. The framework is not imported by this package and
does not receive FireTuner credentials, arbitrary Lua, or a write-capable
watcher socket through this integration.

Never expose FireTuner through port forwarding, a public Wi-Fi network, a VPN
that permits peer access, or an untrusted LAN. Do not pass arbitrary Lua from an
LLM or remote caller; keep actions on the audited allowlist.

## Journal privacy

Private journals and full replay output may contain names, match state, command
arguments, and timestamps. Keep them outside the repository and do not attach
them to public issues. `civ5-journal export` removes payloads, timestamps,
identities, hashes, and paths and creates a mode-0600 file without overwriting an
existing destination. The remaining turn/event chronology may still be
sensitive, so the result is redacted rather than anonymous. It is not a backup
of the verifiable source journal.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report
contains an exploitable technique or sensitive machine information.
