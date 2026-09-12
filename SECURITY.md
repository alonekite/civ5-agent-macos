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

After every session:

1. quit Civilization V;
2. stop `civ5_agent.watch`;
3. run `bash scripts/configure_firetuner.sh restore`;
4. verify no process listens on TCP 4318;
5. verify the per-user agent Unix socket is gone.

Never expose FireTuner through port forwarding, a public Wi-Fi network, a VPN
that permits peer access, or an untrusted LAN. Do not pass arbitrary Lua from an
LLM or remote caller; keep actions on the audited allowlist.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report
contains an exploitable technique or sensitive machine information.
