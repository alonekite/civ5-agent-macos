# Persistent host hardening and live sessions

This procedure keeps the macOS application firewall enabled and Civilization V
blocked from incoming connections across development sessions. FireTuner still
opens only for a bounded test.

Run these commands in an ordinary interactive host terminal, not a sandboxed
shell. `socketfilterfw` can return a false disabled/empty view inside a sandbox.

## One-time hardening

Quit Civilization V and stop the watcher. First require a closed transport:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

Create the persistent guard:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session harden
```

Enter the macOS administrator password locally if `sudo` asks for it. A
successful result is `hardened` or `already_hardened`. Verify the idle guard:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight hardened
```

The result must show FireTuner disabled, no listener or watcher socket, the
firewall enabled, and the Civ V rule present and blocking incoming connections.

The private recovery record is stored under the current user's Application
Support directory with mode `0600`. It contains only the original boolean
firewall/rule baseline. Do not copy it into the repository, edit it, or delete
it while the guard is installed.

## Each live test

Prepare the test. With intact persistent hardening this changes FireTuner but
does not mutate the firewall:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session prepare
PYTHONPATH=src python3 -m civ5_agent.preflight ready
```

Start Civ V, require `preflight live`, and run the watcher or bounded test.
When finished, quit Civ V and stop the watcher before restoring:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session restore
PYTHONPATH=src python3 -m civ5_agent.preflight hardened
```

`restore` disables FireTuner and deletes only the per-session recovery files.
It intentionally preserves the firewall and Civ V block rule.

If the hardening check reports drift, do not let `prepare` silently repair it.
Stop and inspect the host state. The recorded baseline remains the authority
for a later explicit `unharden`.

## Remove the persistent guard

Only after Civ V is quit, the watcher is stopped, FireTuner is disabled, and no
live-session record remains:

```bash
PYTHONPATH=src python3 -m civ5_agent.live_session unharden
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

`unharden` restores exactly the firewall enablement, Civ V rule presence, and
allow/block mode recorded by `harden`, then deletes the hardening record. It
does not guess a baseline when the record is missing.

## Compatibility fallback

When no persistent hardening record exists, `prepare` and `restore` retain the
older temporary workflow: establish the firewall guard for one session and
return it to the exact starting baseline afterward.

