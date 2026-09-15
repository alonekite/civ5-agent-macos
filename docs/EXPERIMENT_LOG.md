# Experiment Log

Use this as the single source of truth for what is actually verified on the M4 Mac.

## Template
### YYYY-MM-DD — Experiment name
**Hypothesis**

**Environment**
- macOS:
- Apple Silicon:
- Civ V build:
- DLC:
- Steam/App Store:
- Mods enabled:

**Procedure**

**Observed result**

**Conclusion**
confirmed / rejected / inconclusive

**Next step**

### 2026-09-12 — Phase 0 macOS machine reconnaissance
**Hypothesis**

The target Mac has a discoverable Civilization V installation and writable
game-owned user-data locations suitable for a minimal Lua-to-Python bridge
experiment.

**Environment**
- macOS: 26.6.2 (build 25G83)
- Apple Silicon: arm64 host
- Civ V: Civilization V Campaign Edition 1.4.2, bundle build 182084,
  Firaxis build 403694
- Game executable: x86_64 Mach-O; Rosetta package is installed
- Distribution: Mac App Store (`Contents/_MASReceipt` is present)
- DLC: bundled content directories include `Expansion`, `Expansion2`,
  `DLC_01` through `DLC_07`, Deluxe, and map packs; content activation was
  not tested in-game
- Mods enabled: none (`Civ5ModsDatabase.db`: 13 installed scenario entries,
  0 enabled, 0 activated; `MODS` contains 0 custom-mod directories)

**Procedure**

1. Ran `bash -n scripts/recon_macos.sh`.
2. Ran `bash scripts/recon_macos.sh` at `2026-09-12T16:44:43+0200`.
3. Cross-checked application metadata with `Info.plist` and executable
   architecture with `file`.
4. Inspected the game cache and ModUserData databases read-only with `sqlite3`.
5. Inspected `config.ini`, `modding.log`, and `Lua.log` without changing them.

**Observed result**

- Application found at:
  `/Applications/Civilization V Campaign Edition.app`
- User data found at:
  `$HOME/Library/Containers/com.aspyr.civ5campaign/Data/Library/Application Support/Civilization V Campaign Edition`
- `MODS`, `ModUserData`, `Logs`, `Saves`, `ModdedSaves`, and `cache` exist.
- `Lua.log` contains `Initializing Lua 5.1.4`, proving the embedded Lua runtime
  started, but not that a custom Lua mod loaded.
- `ModUserData` contains one SQLite database,
  `df3333a4-44be-4fc3-9143-21706ff451d5-1.db`. It belongs to the bundled
  Civilization Tutorials scenario, has a `SimpleValues` table, and currently
  contains no rows. This confirms the expected persistence directory and file
  shape exist, not yet that live cross-process reads or writes are safe.
- `EnableTuner = 0`, `SendRemarksToTuner = 0`, and `LoggingEnabled = 0`.
- No TCP 4318 listener was detected by `lsof` during the run.
- Process enumeration was denied in the current sandbox, so live game-process
  state is unverified rather than absent.

**Conclusion**

confirmed for application discovery, version/build, execution architecture,
Rosetta availability, user-data location, Lua runtime initialization, database
persistence location, and current FireTuner configuration.

inconclusive for custom Lua mod loading, DLC activation, live-game process
state, and bidirectional access to a database while Civ V is running.

**Next step**

Install a minimal allowlisted test mod that calls
`Modding.OpenUserData(<new project UUID>, 1)`, writes `Game.GetGameTurn()` plus
a monotonic sample sequence, and logs a unique marker. Start a modded game and
verify both the marker in `Lua.log` and changing values from an external
read-only Python watcher. Do not write to the existing tutorials database.

### 2026-09-12 — Phase 0 custom Lua mod loading attempt
**Hypothesis**

The installed Campaign Edition exposes a supported UI path that can enable and
load a custom Lua mod.

**Environment**
- Same host and game build as the Phase 0 reconnaissance above
- Smoke mod ID: `0de02ea8-297d-4d14-9cb5-3151ff03e3bf`, version 1
- Smoke behavior: print a unique marker and write two static values through
  `Modding.OpenUserData()`; no game actions

**Procedure**

1. Built and validated `mods/phase0_smoke`, using the game's bundled
   `InGameUIAddin` mod format as the local reference.
2. Installed it as
   `MODS/Civ5 Agent Phase 0 Smoke (v 1)` without overwriting existing files.
3. Started Civilization V and reached the Brave New World main menu.
4. Inspected the refreshed `Civ5ModsDatabase.db`, the expected smoke database,
   and the installed front-end Lua source.

**Observed result**

- The game scanner registered the smoke mod with `Installed=1`, proving its
  `.modinfo` and installation directory were recognized.
- The same database reported `Enabled=0` and `Activated=0` for the smoke mod.
- No smoke ModUserData database was created, so the Lua add-in did not load.
- The visible main menu had no `MODS` item.
- The bundled front-end XML defines `ModsButton`, but the installed
  `Assets/Assets/UI/FrontEnd/MainMenu.lua` line 41 executes:
  `Controls.ModsButton:SetHide( true )`, with the vendor comment
  `MAC_PORT ... Comment this line out to re-enable mods`.

**Conclusion**

rejected on the unmodified Mac App Store Campaign Edition build. Custom mod
discovery works, but the vendor-supplied Mac UI forcibly removes the supported
activation path. The Lua runtime initialization does not prove custom Lua load.

**Next step**

Do not modify the signed Mac App Store application bundle. Keep the stock game
intact, enable FireTuner in the user-owned configuration, enter a normal game,
and test whether TCP 4318 permits read-only Lua evaluation of
`Game.GetGameTurn()`, `Game.GetActivePlayer()`, and player gold. A Civ V
distribution that exposes the Mods browser remains an alternative.

### 2026-09-12 — Modified application-copy launch attempt
**Hypothesis**

A copy-on-write duplicate of the application could expose the vendor's existing
Mods button without modifying the installed original.

**Procedure**

1. Made an APFS clone of the application and changed only the forced-hide line
   in the clone.
2. Preserved the original application as a separate complete bundle.
3. Tried the clone first under a distinct name and then temporarily at the
   original application path.

**Observed result**

macOS rejected the changed clone as damaged because its signed resources no
longer matched. The clone disappeared from `/Applications` after the system
dialog. The untouched original bundle was restored to
`/Applications/Civilization V Campaign Edition.app`; its App Store receipt,
executable, build 182084 metadata, and original forced-hide line were re-read,
and its launcher opened successfully afterward.

**Conclusion**

rejected. Modifying a copied signed App Store bundle is not a viable or safe
loading mechanism on this machine.

**Next step**

Test FireTuner/TCP against an ordinary in-progress game without modifying the
application bundle.

### 2026-09-12 — FireTuner in-game read proof

**Hypothesis**

The stock Campaign Edition can expose genuine in-progress game state to an
external Python process through its bundled localhost FireTuner service.

**Procedure**

1. Backed up `config.ini` and changed only `EnableTuner` from `0` to `1` with
   `scripts/configure_firetuner.sh enable`; re-read the setting afterward.
2. Started the untouched signed application and entered an ordinary game.
3. Connected Python to `127.0.0.1:4318` and performed the Firaxis `APP:` and
   `LSQ:` handshake.
4. Sent a read-only `print` probe first to `Main State`, then to the reported
   `InGame` state ID 172.
5. Compared the returned values with a direct screenshot of the game UI.
6. Ran `python3 -m civ5_agent.watch --once` through the implemented reader.

**Observed result**

- The server identified itself as `Civ5 / Sid Meier's Civilization V` and
  returned 130 ID/name Lua-state pairs, including `172 / InGame`.
- The main-state round trip returned `CIV5_AGENT_MAIN_PROBE` followed by a
  command-completion frame.
- The in-game round trip returned exactly:
  `InGame: CIV5_AGENT_STATE:1:0:3`.
- The visible game was on turn 1 and displayed 3 gold, matching the transport
  response; active-player ID 0 was also internally valid.
- The formal watcher printed:
  `{"active_player": 0, "cities": [], "gold": 3, "research": null, "turn": 1, "units": []}`.
- Nine automated unit tests pass for framing, state-list parsing, asynchronous
  response collection, marker parsing, and read-only SQLite fallback behavior.
- This old server may leave a disconnected client in `CLOSE_WAIT` until the
  game UI handles another event. A single persistent watcher connection avoids
  that reliability issue.

**Conclusion**

confirmed. External Python can read real game data from a live Civ V match on
this Apple Silicon Mac through stock Civ V Lua/FireTuner, without screen OCR,
input automation, a Windows DLL, or modification of the app bundle.

**Next step**

Keep the watcher connected and observe a normal turn transition from N to N+1.
Then expand the allowlisted snapshot to cities, research, and units before
attempting any write action.

### 2026-09-12 — FireTuner exposure and safe shutdown

**Observed result**

- With FireTuner enabled, `lsof` reported `TCP *:4318 (LISTEN)`, not a
  loopback-only bind.
- The macOS application firewall reported disabled, and incoming connections
  to the game application were permitted.
- A normal `SIGTERM` did not close the old OpenGL game while its modal exit
  confirmation was open. After explicit approval, the disposable turn-1 test
  process was force-terminated.
- `scripts/configure_firetuner.sh restore` re-read all original values as zero,
  and a final listener check produced no TCP 4318 entry.

**Conclusion**

FireTuner is a viable development bridge but is not safe to leave enabled on
an untrusted network when the host firewall is disabled. Enable it only for a
bounded test session, keep one client connected, and restore the original
configuration afterward.

### 2026-09-12 — Rich read and verified end-turn MVP

**Hypothesis**

A single persistent Python watcher can read structured live state, share its
sole FireTuner connection with the command CLI, submit the allowlisted
`end_turn` action, and prove the action succeeded by re-reading game state.

**Procedure**

1. With explicit approval for a bounded trusted-network test, enabled
   FireTuner and started the untouched App Store game.
2. Entered a new Spain game and started
   `PYTHONPATH=src python3 -m civ5_agent.watch`.
3. Founded Madrid, chose Pottery, selected Scout production, and exhausted the
   Warrior's moves through ordinary game UI actions.
4. Observed each state change through the persistent watcher.
5. Ran `PYTHONPATH=src python3 -m civ5_agent.command end_turn` through the
   watcher's mode-0600 Unix socket.
6. Exited Civ V, stopped the watcher, restored `config.ini`, and verified no
   TCP 4318 listener or local agent socket remained.

**Observed result**

- Initial snapshot reported Isabella/Spain, turn 0, happiness 9, and two units:
  Settler ID 8192 at (52,29) and Warrior ID 16385 at (53,29), each with 120
  movement points.
- After founding Madrid, the watcher reported city ID 8192, population 1 at
  (52,29), removal of the Settler, science/turn 4, culture/turn 1, gold/turn 5,
  and happiness 5.
- It then observed Pottery (`TECH_POTTERY`, cost 40), Scout production, and the
  Warrior moved to (54,28) with zero moves remaining.
- Command UUID `ca5582ca-ad61-4f9f-b2a7-9f645921d60b` returned `success` with
  `verified turn 0 -> 1`.
- Re-read verification also observed gold 0 → 5, culture 0 → 1, Pottery
  progress 0 → 4, and Warrior movement 0 → 120.
- The independent watcher printed the same final turn-1 snapshot.
- During game shutdown Civ V emitted many Lua-state lifecycle frames. The
  client was subsequently hardened to discard those frames, treat `Closing` as
  a concise disconnect, and cap diagnostic previews.
- After shutdown, configuration was re-read as `EnableTuner = 0`,
  `SendRemarksToTuner = 0`, `LoggingEnabled = 0`; no listener or agent socket
  remained.

**Conclusion**

confirmed. The repository's MVP definition of done is met on the target Apple
Silicon Mac: the watcher reads live game-state changes, and the command CLI
advances one turn and returns verified before/after state over a shared,
single-client FireTuner connection.

**Next step**

Add deterministic state validation and richer city/unit details, then implement
one additional safe action at a time. Keep all writes behind explicit
preconditions and post-action verification.

### 2026-09-12 — Offline write-path hardening

**Hypothesis**

Research and production writes can reuse APIs and argument shapes from the
game's own Brave New World UI, while local IPC and verification remain robust
for larger or briefly unavailable snapshots.

**Procedure**

1. Compared the generated Lua with the installed Expansion 2 `TechPopup.lua`
   and `ProductionPopup.lua` sources.
2. Added strict identifier validation, game capability checks, and post-write
   snapshot verification for research and city production.
3. Separated the 64 KiB local request limit from a 4 MiB response limit.
4. Made verification tolerate transient invalid snapshots during UI/turn
   transitions while preserving the last validated state.
5. Ran the complete warning-enabled test suite.

**Observed result**

- The installed UI calls `Network.SendResearch(eTech, iValue, -1, false)` and
  `Game.CityPushOrder(city, eOrder, iData, false, not g_append, true)`, matching
  the bridge's ordinary-research and replace-production argument shapes.
- 41 tests passed with no warnings, including injection rejection, capability
  checks, read-back success requirements, transient-state retry, Unix-socket
  cleanup/permissions, and a response larger than the request limit.

**Conclusion**

confirmed offline. The new paths match locally installed stock UI source and
pass deterministic tests. They are not marked live-verified until exercised in
an actual match and observed through the independent watcher.

**Next step**

Run one bounded FireTuner session: validate snapshot schema 2, issue research
and production into empty choices, re-read both, then restore the configuration
and confirm port 4318 is closed.

### 2026-09-12 — Schema 2, research, production, and controller live proof

**Hypothesis**

With the macOS application firewall enabled and Civ V explicitly blocked from
incoming connections, the local watcher can read schema 2, safely perform the
two additional allowlisted writes, reject a blocked turn end, and execute a
complete deterministic turn-end decision.

**Environment**

- Same Apple Silicon Mac, App Store game, and Civ V build as earlier tests
- New Spain game, turn 0, Madrid founded
- macOS application firewall temporarily enabled
- Civ V rule visibly and programmatically reported `Block incoming connections`
- FireTuner enabled only for the bounded session

**Procedure**

1. Recorded the original firewall state as disabled and confirmed Civ V was
   absent from its eight application rules.
2. Enabled the firewall through System Settings with user authorization and
   verified Civ V was explicitly blocked.
3. Enabled FireTuner, restarted Civ V, and loaded a save with no research or
   city production selected.
4. Started the persistent watcher and read schema 2 through its local socket.
5. Ran the controller without execution, selected Pottery, selected Scout
   production, and re-read state after each request.
6. Attempted `end_turn` while the Warrior still required orders and checked
   that the game state did not change.
7. After the user moved the Warrior, ran the controller with `--execute` and
   verified the turn transition.
8. Restored FireTuner, exited the game, stopped the watcher, removed the Civ V
   firewall rule, restored the original disabled firewall state, and re-read
   every shutdown condition.

**Observed result**

- Schema 2 reported turn-active and end-turn fields plus Madrid ID 8192 and
  Warrior ID 16385. Research was `null`; Madrid production was empty.
- The dry-run controller returned `manual_required: choose research`.
- Research command UUID `5ec6fa7e-f8c2-4513-b4e0-bfe6f26d8ce5` returned
  success after observing `null -> TECH_POTTERY` (ID 1, progress 0, cost 40).
- Production command UUID `f375b5a4-d462-4dbb-a7f0-ed7cced2743c` returned
  success after observing Madrid production change from empty to
  `TXT_KEY_UNIT_SCOUT`.
- With Warrior movement 120, the controller required unit orders. Direct
  end-turn UUID `09b31edc-110b-46b0-9c05-4de387989ef4` returned error with
  blocker 3; before and after remained turn 0 and were identical.
- After the Warrior moved to (31,35) with zero movement, the snapshot reported
  `can_end_turn=true` and blocker -1.
- Controller command UUID `2bc5603a-2e88-425b-846d-621e1da40692` returned
  success and verified turn 0 -> 1. The re-read also observed gold 0 -> 3,
  culture 0 -> 1, Pottery progress 0 -> 4, and Warrior movement 0 -> 120.
- Shutdown handling reported `Civ V FireTuner is closing` without lifecycle
  output flooding.
- Final checks found FireTuner configuration values all zero, no TCP 4318
  listener, no agent Unix socket, firewall restored to disabled, and no Civ V
  entry in the application-rule list.

**Conclusion**

confirmed. Schema 2, research selection, city production, blocked-action
refusal, and deterministic controller execution all work against the live game
with mandatory post-write state verification.

**Next step**

Implement one strictly validated unit action, beginning with a non-spatial
`skip` or `fortify` command before attempting coordinate-based movement. Keep
it behind unit ownership, turn-active, and post-action movement/state checks.

### 2026-09-12 — Offline unit-skip and audit hardening

**Hypothesis**

A unit skip can be scoped to one owned unit despite Civ V's selection-oriented
network API, and every write result can be persisted without creating retry
ambiguity.

**Procedure**

1. Inspected the installed Expansion 2 mission XML and `UnitPanel.lua` /
   `ActionInfoPanel.lua` sources.
2. Implemented `skip_unit UNIT_ID` using the stock `MISSION_SKIP` network
   message only after selecting and re-reading the exact owned unit and passing
   `Game.CanHandleAction`.
3. Required post-action proof that the same unit has zero movement and unchanged
   coordinates.
4. Added a mode-0600, no-symbolic-link JSONL command audit log.
5. Expanded live-state type validation and aligned explicit end-turn blockers
   with the full installed Brave New World UI list, including the multiplayer
   already-sent guard.
6. Ran the complete warning-enabled suite.

**Observed result**

- 54 tests pass with no warnings.
- Tests cover wrong-owner rejection, exact-unit selection, one and only one
  network mission call, idle-in-place read-back, malformed schema types, audit
  permissions, and symbolic-link refusal.

**Conclusion**

confirmed offline. Unit skip and command audit behavior are implemented and
tested, but unit skip remains unverified against the live game.

**Next step**

In a later bounded, firewall-protected session, run `skip_unit` on a ready unit
and verify its movement becomes zero without a coordinate change. Only then
consider adding it to automatic controller execution.

### 2026-09-13 — Read-only safety preflight

**Hypothesis**

The FireTuner session safety gates can be checked reproducibly without changing
the game configuration or macOS firewall.

**Procedure**

1. Added `civ5_agent.preflight` modes for general status, guarded startup,
   live transport, and verified shutdown.
2. Parsed the exact `EnableTuner` setting, macOS application-firewall state and
   Civ V rule, TCP 4318 listener state, and agent Unix-socket presence.
3. Made `ready`, `live`, and `shutdown` fail closed when their required state
   cannot be proved.
4. Required the watcher and direct command path to pass the live check before
   connecting, rechecked it before watcher-mediated writes, and rejected any
   endpoint other than `127.0.0.1:4318`.
5. Ran the complete warning-enabled test suite and then executed the `status`
   and `shutdown` modes against the restored host.

**Observed result**

- 62 tests pass with no warnings.
- The real host reported FireTuner disabled, no TCP 4318 listener, no agent
  socket, the application firewall restored to disabled, and no Civ V rule.
- Both the neutral `status` report and strict `shutdown` verification returned
  `ok: true`.

**Conclusion**

confirmed. Future bounded live tests now have a read-only, machine-verifiable
gate before connecting and a strict cleanup check after the session.

**Next step**

Use `preflight ready` and `preflight live` in the next firewall-protected game
session, then live-verify `skip_unit` before permitting controller execution of
unit actions.

### 2026-09-13 — Offline schema 3 diplomacy read

**Hypothesis**

The bridge can add useful diplomacy context without exposing civilizations the
player has not met and without breaking schema 2 consumers.

**Procedure**

1. Inspected the bundled Brave New World `DiploList.lua` and
   `VictoryProgress.lua` rather than assuming undocumented APIs.
2. Added active-player score and era, plus records for alive major
   civilizations only when the active team reports `IsHasMet`.
3. Included the visible player/civilization names, team, score, war state, and
   the same approach estimate shown by the stock diplomacy list.
4. Added strict record validation, duplicate/self-player rejection, URL-style
   delimiter escaping, and schema 2 parser compatibility.
5. Ran the complete warning-enabled suite.

**Observed result**

- 66 tests pass with no warnings.
- Tests prove the emitted Lua filters on `IsHasMet`, remains read-only, parses
  escaped diplomacy records, validates field types, and accepts legacy schema
  2 snapshots without the new fields.

**Conclusion**

confirmed offline only. Schema 3 is ready for a bounded live read test, but its
new fields are not marked live-verified.

**Next step**

During the next firewall-protected game session, first confirm schema 3 in an
early game (an empty diplomacy list is valid), then verify a met civilization
later or from a suitable save before closing the roadmap item.

### 2026-09-13 — Local IPC boundary hardening

**Hypothesis**

The watcher control socket can bound memory use and return a useful response
for every malformed or failing request without affecting legitimate rich
snapshots.

**Procedure**

1. Enforced the existing 64 KiB request limit in the client before it opens a
   socket.
2. Enforced the 4 MiB response limit in the server after JSON serialization.
3. Rejected non-finite JSON values and converted non-object, unserializable,
   and unexpectedly failing callbacks into bounded error objects.
4. Added round-trip tests for every new rejection path while retaining a test
   proving legitimate responses may exceed the smaller request limit.

**Observed result**

- 71 tests pass with no warnings.
- Oversized client requests fail before connection; oversized and invalid
  callback responses return structured errors; unexpected callback details are
  not reflected to the caller.

**Conclusion**

confirmed offline. The local IPC boundary now has symmetric, explicit resource
limits without constraining normal game-state snapshots.

### 2026-09-13 — FireTuner entry-point closure

**Hypothesis**

No shipped CLI should be able to connect to FireTuner, or enable it, while the
application-firewall guard is absent.

**Procedure**

1. Moved the live-session requirement into `FireTunerClient.connect`, beneath
   every current Python entry point.
2. Made `configure_firetuner.sh enable` verify the global firewall state and an
   explicit Civ V block-incoming rule before creating a backup or editing the
   game configuration.
3. Added a test proving an unsafe session fails before `socket.create_connection`
   and ran shell syntax validation with the full suite.

**Observed result**

- 72 tests pass with no warnings.
- The watcher, command CLI, tuner diagnostic CLI, and direct library client now
  share the same fail-closed connection gate.

**Conclusion**

confirmed offline. The configuration and connection layers both require the
agreed firewall mitigation; the next live session will verify the complete
operator workflow.

### 2026-09-13 — Offline schema 3 city economy

**Hypothesis**

The snapshot can expose enough city growth and production data for later
planning without relying on rounded UI strings.

**Procedure**

1. Inspected the bundled Brave New World `CityView.lua`,
   `CityBannerManager.lua`, and `EconomicGeneralInfo.lua`.
2. Added food stored, growth threshold, food per turn, production stored,
   production needed, and production per turn to schema 3 city records.
3. Preserved the game's times-100 integers for fractional food and production.
4. Required the snapshot header to precede records and rejected duplicate
   headers to prevent unrelated FireTuner output from being merged.
5. Kept six-field schema 2 city records parseable and validated all new schema
   3 fields before policy or command code can consume them.

**Observed result**

- 74 tests pass with no warnings.
- Tests cover exact fixed-point parsing, missing schema 3 fields, legacy city
  records, records before headers, duplicate headers, and the existing
  read-only Lua denylist.

**Conclusion**

confirmed offline only. The expanded city records are ready for the same
bounded, firewall-protected live verification as the other schema 3 fields.

### 2026-09-13 — Offline schema 3 unit condition

**Hypothesis**

Owned-unit condition can be represented with stable read-only values before
any automatic unit policy is attempted.

**Procedure**

1. Inspected the bundled Brave New World `UnitPanel.lua`,
   `MilitaryOverview.lua`, and `PlotMouseoverInclude.lua`.
2. Added damage, maximum hit points, base combat strength, base ranged
   strength, and range to schema 3 unit records.
3. Retained six-field schema 2 unit parsing and made the new fields mandatory
   only for schema 3.
4. Added type, non-negative, positive-max-health, and damage-within-health
   validation.

**Observed result**

- 75 tests pass with no warnings.
- Tests parse the added unit fields and reject damage greater than maximum hit
  points while all existing skip-unit verification remains green.

**Conclusion**

confirmed offline only. The bridge now has enough owned-unit condition data to
support a future conservative unit policy after schema 3 and `skip_unit` are
live-verified.

### 2026-09-13 — Offline science-victory progress

**Hypothesis**

Useful victory progress can be read without exposing other players' hidden
state by limiting it to the active team's own science projects.

**Procedure**

1. Followed the bundled Brave New World `VictoryProgress.lua` API usage.
2. Added the science-victory enabled flag and active-team counts for the Apollo
   Program, SS Booster, Cockpit, Stasis Chamber, and Engine.
3. Used `-1` as an explicit unavailable-project sentinel and validated all
   fields and the single-record invariant.
4. Kept schema 2 snapshots valid without a victory record.

**Observed result**

- 76 tests pass with no warnings.
- Tests cover Lua construction, record parsing, boolean and count validation,
  duplicate-record rejection, and the existing read-only denylist.

**Conclusion**

confirmed offline only. The victory roadmap item remains open until these
values are observed in a bounded live game.

### 2026-09-13 — Command identity and audit arguments

**Hypothesis**

Every local write request can carry a bounded, unambiguous identifier and leave
enough information to reproduce the requested action even when it fails.

**Procedure**

1. Required caller-supplied local command IDs to be canonical UUIDv4 strings;
   requests without an ID still receive a generated UUIDv4.
2. Rejected invalid IDs before any game write function is called.
3. Added the validated command arguments to each private JSONL audit record.
4. Preserved the existing operation, result, before/after snapshots, timestamp,
   permissions, and no-retry-on-audit-failure behavior.

**Observed result**

- 77 tests pass with no warnings.
- Tests prove malformed IDs never reach an executor and the audit API records
  the exact validated argument object supplied by the command path.

**Conclusion**

confirmed offline. Command results are now more traceable without broadening
the write allowlist.

### 2026-09-13 — Watcher-session replay protection

**Hypothesis**

A client retry using the same command UUID must not execute a game action a
second time.

**Procedure**

1. Cached completed watcher-mediated commands by UUID for the watcher lifetime.
2. Returned the cached response with `replayed: true` for an identical retry.
3. Rejected reuse of a UUID with a different operation or argument object.
4. Serialized lookup, execution, audit, and cache insertion under the existing
   FireTuner connection lock.

**Observed result**

- 79 tests pass with no warnings.
- Identical retries invoke the executor once; UUID collisions with different
  arguments are rejected before a second write.

**Conclusion**

confirmed offline. Watcher-mediated retries are idempotent within one watcher
session; persistence across watcher restarts remains future work.

### 2026-09-14 — Segmented live state and corrected unit-skip proof

**Hypothesis**

The target FireTuner can return the full expanded state as bounded, coherent
segments, and unit skip can be verified through readiness without incorrectly
requiring movement points to be spent.

**Environment**

- Same Apple Silicon Mac, Campaign Edition build, and stock signed application
  recorded above.
- Ordinary early single-player game with one founded city and one ready unit.
- FireTuner protected by an enabled macOS application firewall and an explicit
  Civ V block-incoming rule, prepared through the recoverable session manager.

**Procedure**

1. Started the persistent watcher after the live safety preflight passed.
2. Attempted the expanded schema 3 draft as one read-only Lua program.
3. After the target truncated that program near 1 KiB, split it into header,
   cities, units, diplomacy, and victory programs, each below 900 bytes.
4. Added per-part turn and active-player markers and rejected missing,
   duplicated, or mismatched parts.
5. Read all early-game fields from the live match; after preserving the
   published schema 3 parser, assigned the readiness-bearing segmented shape
   its own schema 4 version.
6. Submitted one unit-skip command. Civ V accepted it and the game UI showed the
   unit had been skipped, but the old verifier incorrectly expected zero
   movement and reported an error.
7. Confirmed the stock UI uses `Unit:IsReadyToMove()`, added that boolean to the
   unit record, and changed the postcondition to require readiness `true ->
   false` while ID, coordinates, and movement remain unchanged.
8. Advanced normally to the next turn and, after explicit confirmation,
   submitted exactly one new unit-skip command through the final reader and
   verifier.
9. Quit the game, stopped the watcher, and ran session restoration. The first
   restoration exposed a path-identity defect: `socketfilterfw` retained the
   executable-path rule when asked to remove the application-bundle path.
10. Changed removal to use the same executable path as preparation, reran the
    saved recovery state, and independently checked the shutdown phase.

**Observed result**

- The final five Lua programs were 620–875 bytes and returned one coherent live
  snapshot. The target run exercised the same readiness-bearing shape before
  its compatibility-preserving version number was finalized as schema 4.
- Score and era were valid non-negative integers.
- City food, growth, production storage, cost, and per-turn values were valid
  integers and changed consistently across the observed turn transition.
- Unit health, strength, range, movement, and readiness were returned. The unit
  became ready again at the start of the next turn.
- The diplomacy list was empty before contact with another major civilization,
  as required by the hidden-information filter.
- The science-victory enabled flag and all five active-team project counts had
  valid values in the early-game zero-progress branch.
- The final skip command returned verified success: readiness changed from true
  to false while unit identity, coordinates, and remaining movement stayed the
  same. The end-turn blocker cleared as a corresponding secondary observation.
- No write was retried automatically.
- Final restoration returned the exact recorded baseline: FireTuner disabled,
  no TCP 4318 listener, no watcher socket, global firewall disabled, and no Civ
  V application rule. A separate read-only shutdown preflight confirmed all six
  conditions with no issues.

**Conclusion**

confirmed for segmented expanded-state reads, all early-game scalar branches,
the corrected `skip_unit` write-after-read postcondition, and complete recovery
to the pre-test machine state. Non-empty diplomacy and non-zero late-game
science-project branches remain enhancement tests, not blockers for the schema
4 read contract.

**Next step**

Keep the segmented command-size, identity, and exact firewall-rule removal
invariants in the regression suite. Test non-empty diplomacy or late-game
project progress only when a suitable save is available.

### 2026-09-15 — Stock UI technology-state API inspection

**Hypothesis**

The bundled BNW UI exposes supported read-only APIs for authoritative researched
and currently researchable technology state, and its end-turn blocker separates
ordinary, free, and special technology choices.

**Environment**

- Installed Campaign Edition BNW UI Lua sources on the target Mac.
- No live game, FireTuner, firewall, or network listener was enabled.

**Procedure**

1. Inspected the bundled Expansion 2 `TechPopup.lua`, `TechTree.lua`, and
   `ActionInfoPanel.lua` implementations.
2. Compared ordinary and free-technology button eligibility with the end-turn
   blocker branches used by the stock UI.
3. Added a sixth bounded read-only snapshot program and offline parser,
   validation, compatibility, and controller tests.

**Observed result**

- The stock technology UI enumerates `GameInfo.Technologies`, requires
  `player:CanResearch(techID)`, and additionally requires
  `player:CanResearchForFree(techID)` when free technologies are pending.
- Researched membership is available from the active player's team through
  `IsHasTech`.
- The stock action panel distinguishes research, free-technology, and
  steal-technology blockers.
- The new technology program is 874 bytes, below the existing 900-byte bound.

**Conclusion**

confirmed by bundled-source inspection and offline tests only. Schema 5 must be
read in a real ordinary choice before its researched list, candidate list, and
normal choice branch are marked live-verified. Free and steal technology modes
remain unverified until reproducible target-game situations exist.
