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

Run the read-only safety check after configuring the session and again after
the game starts:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight ready
PYTHONPATH=src python3 -m civ5_agent.preflight live
```

After every session:

1. quit Civilization V;
2. stop `civ5_agent.watch`;
3. run `bash scripts/configure_firetuner.sh restore`;
4. verify no process listens on TCP 4318;
5. verify the per-user agent Unix socket is gone.

Steps 3–5 can be verified together with:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

The command reports JSON and makes no system changes.

The watcher and direct command path enforce the live check automatically. The
watcher's local control socket rechecks it before each allowlisted write, so a
removed firewall rule prevents the game action. The bridge refuses FireTuner
hosts and ports other than the verified `127.0.0.1:4318` endpoint.

Never expose FireTuner through port forwarding, a public Wi-Fi network, a VPN
that permits peer access, or an untrusted LAN. Do not pass arbitrary Lua from an
LLM or remote caller; keep actions on the audited allowlist.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report
contains an exploitable technique or sensitive machine information.
