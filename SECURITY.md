# Security

## FireTuner exposure

The tested Mac App Store Campaign Edition build listens on `TCP *:4318` when
FireTuner is enabled. This exposes the game's Lua execution interface on every
IPv4 network interface, not only `127.0.0.1`. The protocol has no authentication
observed by this project.

Only enable FireTuner for a bounded test on a trusted machine. Turn on the
macOS application firewall, explicitly block incoming connections to
Civilization V, and verify the rule before starting the game. A firewall rule
is mitigation: the game still owns a wildcard listener.

Prepare a bounded session from the host environment:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
```

This records the original settings outside the repository, establishes and
verifies the guard, and rolls back on failure. A sandboxed process may see a
false disabled/empty firewall state, so it must not be used for this operation.
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
live-session restore command returns the settings to its private recorded
baseline and verifies the shutdown state.

The watcher and direct command path enforce the live check automatically. The
watcher's local control socket rechecks it before each allowlisted write, so a
removed firewall rule prevents the game action. The bridge refuses FireTuner
hosts and ports other than the verified `127.0.0.1:4318` endpoint. The low-level
client enforces the same rule. The live-session manager accepts either the
executable path or the canonical `.app` path reported by macOS for the Civ V
firewall rule.

Never expose FireTuner through port forwarding, a public Wi-Fi network, a VPN
that permits peer access, or an untrusted LAN. Do not pass arbitrary Lua from an
LLM or remote caller; keep actions on the audited allowlist.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report
contains an exploitable technique or sensitive machine information.
