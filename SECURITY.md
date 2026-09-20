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
live-session restore command returns the settings to its private recorded
baseline and verifies the shutdown state.

The provisional `civ5-live-test` supervisor may compose those same operations
for a bounded read-only profile. It runs in the foreground, launches Civ V only
after the firewall guard is verified, starts a watcher whose server admits only
`ping` and `read_state`, and requests a normal application quit before restoring
the baseline. It never accepts an administrator password and never force-kills
the game. Its private recovery record contains bounded checkpoint summaries,
not complete snapshots. A safety-boundary failure triggers orderly cleanup; a
data inconsistency pauses with the scene intact for operator inspection.

The watcher and direct command path enforce the live check automatically. The
watcher's local control socket rechecks it before each allowlisted write, so a
removed firewall rule prevents the game action. The bridge refuses FireTuner
hosts and ports other than the verified `127.0.0.1:4318` endpoint. The low-level
client enforces the same rule. The live-session manager accepts either the
executable path or the canonical `.app` path reported by macOS for the Civ V
firewall rule.

`civ5-watch --read-only` is a server-enforced mode, not a client convention. In
that mode every request other than `ping` and `read_state` is rejected before
command parsing or execution, and journal capture is prohibited.

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
