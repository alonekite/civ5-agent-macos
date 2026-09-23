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

### 2026-09-15 — Schema 5 ordinary technology-state live proof

**Hypothesis**

The bounded segmented reader can report authoritative ordinary technology
state in a real match, including the transition from an unselected technology
to a manually selected current research target.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Ordinary single-player early-game match; no free or stolen technology choice.
- Recoverable live-session guard with FireTuner enabled only while the macOS
  firewall was enabled and Civ V had an explicit block-incoming rule.

**Procedure**

1. Prepared the guarded session and required a successful live preflight.
2. Read schema 5 through a single external read-only connection; no game action
   command was sent.
3. Compared the researched set and four ordinary candidates with the stock
   technology UI.
4. Observed the state first while another mandatory task had blocker priority,
   then after all tasks except ordinary research were resolved.
5. Selected one ordinary technology manually in the stock UI and read the same
   connection again.
6. Quit the game and restored the recorded firewall and FireTuner baseline.

**Observed result**

- The snapshot parsed as schema 5. Its known researched technology and all four
  researchable candidates agreed with the game UI, used stable `TECH_*`
  identifiers, and had no overlap or duplicates.
- With another mandatory task taking priority, current research was empty but
  the single end-turn blocker did not report research. Once research was the
  only remaining task, normal mode reported `required: true`.
- After the manual selection, the current research matched the selected stable
  identifier, normal mode reported `required: false`, and the game allowed the
  turn to end.
- A persistent connection remained reliable across the state change; immediate
  reconnect attempts after an earlier one-shot connection were unreliable,
  consistent with the established single-connection-owner design.
- Restoration returned FireTuner, its listener, firewall enablement, and the Civ
  V application-rule presence to their recorded pre-test states.

**Conclusion**

confirmed for schema 5 researched/researchable sets and ordinary research-choice
transitions. The test rejected using the single end-turn blocker alone as the
ordinary `required` signal; ordinary detection must also remain correct when a
higher-priority task masks that blocker. Free and steal technology modes remain
offline-only and manual-required.

**Next step**

Keep a persistent single connection, derive ordinary required state from an
empty current research plus at least one legal candidate while retaining
special blocker overrides, enforce the consistency invariant, and return to M4
effective scalar resolution.

Planning note: ADR-0014 later superseded the proposed scalar-resolution step.
M4 was closed as a structural knowledge view, and effective-rule analysis was
moved to future consumer-driven strategic, tactical, and vertical skills.

### 2026-09-16 — Combined M5/M6 release-gate attempt

**Hypothesis**

One guarded watcher can capture a verifiable private M5 journal while the M6
CLI validates and executes one explicit, single-action `end_turn` TurnPlan.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal single-player saved match.
- Recoverable live-session guard with FireTuner enabled only behind the macOS
  firewall and an explicit Civ V block-incoming rule.

**Procedure**

1. Prepared and live-preflighted the guarded session.
2. Started one watcher with a new private journal and audit path; schema 5 read
   successfully.
3. Resolved production and unit requirements manually, authored an explicit
   one-action `end_turn` TurnPlan, and validated it against the watcher.
4. Executed the plan exactly once. After the reported failure, no automated
   retry was attempted. The operator then ended the turn manually, and the
   watcher observed the transition.
5. Quit the game; the watcher failed closed as the listener disappeared. The
   recoverable session manager restored and verified the original baseline.
6. Verified the journal chain, replayed only structural counts, created a
   redacted structural export, and checked private file permissions.

**Observed result**

- TurnPlan creation and read-only validation succeeded.
- Execution failed before a command marker because the 2,069-byte generated
  Lua was truncated by the target FireTuner and parsed as invalid syntax. The
  automated action did not advance the turn.
- The watcher later captured the manually caused turn transition.
- The 23-record journal had a valid hash chain and contiguous replay: one start,
  twenty snapshots, one command submission, and one turn transition. Its lack
  of a terminal result or verification-error record exposed an exception-path
  lifecycle gap.
- Verification and redacted export reported matching structural counts. The
  journal, export, and plan all had mode `600`.
- Shutdown restoration proved FireTuner disabled, no TCP 4318 listener or agent
  socket, firewall restored to disabled, and no Civ V rule, matching baseline.

**Conclusion**

inconclusive for the M5/M6 release gate. M5 storage integrity, replay, export,
permissions, schema-5 capture, and observed transition worked live, but the
failed command lifecycle was incomplete. M6 live plan validation worked, but
execution did not reach the allowlisted game action. Neither milestone receives
complete live-verification status from this attempt.

**Next step**

Bound every FireTuner program before send, compact `end_turn`, preserve
post-submission uncertainty in the journal and M6 recovery path, pass offline
regression/CI, then repeat the bounded combined session without manually
changing state after any execution failure.

### 2026-09-16 — Combined M5/M6 release-gate second attempt

**Hypothesis**

The compact, pre-bounded `end_turn` program can pass through the target
FireTuner, automatically advance the turn, and leave a complete M5 command
lifecycle.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal single-player saved match using schema 5.
- Recoverable guarded FireTuner session under the explicit Civ V block-incoming
  firewall rule.

**Procedure**

1. Prepared and live-preflighted a fresh guarded session, then started one
   watcher with a new private journal and audit path.
2. Manually resolved visible turn requirements, created a new one-action
   `end_turn` TurnPlan, and passed read-only validation.
3. Executed the plan once. The compact command returned a deterministic blocked
   marker and did not advance the turn.
4. The operator then used the stock Next Turn control; it exposed a worker still
   requiring orders. After resolving that unit, a retry of the now-stale plan
   was rejected before any action step.
5. Quit the game, restored the exact host baseline, then verified, structurally
   replayed, and redacted-exported the private journal.
6. Inspected the bundled Brave New World `ActionInfoPanel.lua` and tutorial Lua
   for the authoritative blocker comparison.

**Observed result**

- Plan creation and validation again succeeded.
- The bounded Lua arrived intact and returned `blocked` with blocker value
  `-1`; the implementation had incorrectly required numeric zero.
- The stock UI sources compare the value with
  `EndTurnBlockingTypes.NO_ENDTURN_BLOCKING_TYPE`, confirming that a named game
  enum, not zero, is authoritative on the target build.
- The stale-plan retry returned no execution steps, confirming refusal before
  a second write.
- The 13-record journal contained one start, nine snapshots, one command
  submission, one failed command result, and one verification error. Hash-chain
  verification, contiguous structural replay, redacted export, and mode `600`
  checks all passed.
- No turn transition was recorded. Because the subsequent read that rejected
  the stale plan was not itself a background journal snapshot, this attempt
  alone does not prove whether the stock click changed turns before exposing
  the worker. The third attempt later isolated and proved the same-turn branch.
- Restoration returned FireTuner, listener, socket, firewall, and Civ V rule to
  the recorded baseline with no issues.

**Conclusion**

partial. The attempt live-verified the compact transport path, deterministic
blocked marker, complete M5 failed-command lifecycle, stale-plan pre-write
refusal, private integrity/export controls, and clean recovery. It did not
verify M6 automatic turn advancement. The blocker failure was caused by an
incorrect numeric assumption, not transport truncation or an unknown outcome.

**Next step**

Compare against the game's named no-blocker enum, expose the verified parsed
value for requirement inspection, test readiness independently of
`UI.CanEndTurn()`, then repeat with a newly authored plan. Treat an unchanged
turn or newly surfaced unit requirement as a verified failure and never retry
the old plan.

### 2026-09-16 — Combined M5/M6 release-gate third attempt

**Hypothesis**

ADR-0029's game-defined no-blocker guard can execute the final `end_turn` and
prove automatic turn advancement in the saved-match test state.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal single-player saved match with multiple units and some deferred or
  automated unit activity.
- Fresh guarded FireTuner session, private M5 journal, and newly authored
  schema 1 TurnPlan.

**Procedure**

1. Prepared and live-preflighted a fresh guarded session, then started one
   schema-5 watcher with a new journal.
2. Manually resolved all visible requirements until the stock UI displayed
   Next Turn.
3. Created and validated a new single-action `end_turn` plan. Factual
   inspection observed the game-defined no-blocker value and no ready unit.
4. Executed exactly once and made no further game input while the 30-second
   postcondition check ran.
5. Quit without resolving the newly surfaced unit, restored the exact host
   baseline, then performed a private, sanitized journal comparison and
   structural export.

**Observed result**

- The named-enum Lua guard accepted the command and invoked the stock end-turn
  control, proving ADR-0029's corrected guard on the target runtime.
- The turn did not advance. During end-turn processing, five units changed
  position, ten changed remaining movement, and one unit changed from not ready
  to ready while the unit count stayed constant. The game selected that worker
  and changed the blocker from no blocker to another blocker.
- M6 returned a deterministic failed action after 30 seconds with distinct
  before/after state digests. It did not report completion or retry.
- The 11-record journal contained one start, seven snapshots, one command
  submission, one failed command result, and one verification error. Integrity,
  contiguous replay, redacted export, and journal/plan/export mode `600` checks
  passed.
- No turn transition occurred. Shutdown restored FireTuner, listener, socket,
  firewall, and Civ V rule to the recorded baseline with no issues.

**Conclusion**

partial. The target live-verified the corrected named-enum guard, actual
`Game.DoControl` execution, exact failed postcondition, changed after-state,
full M5 failure lifecycle, and no-retry behavior. The saved match was unsuitable
for a one-action success gate because end-turn processing first advanced
automated/deferred unit work and exposed a new unit requirement.

**Next step**

Repeat only in a minimal early-game state with no automated or deferred unit
orders. Manually resolve every research, production, and unit requirement, then
let a newly authored one-action plan perform the sole final Next Turn control.
An unchanged turn remains a verified failure and requires shutdown rather than
another plan in the same session.

### 2026-09-16 — Combined M5/M6 release-gate successful attempt

**Hypothesis**

A newly authored one-action `end_turn` plan can complete through the guarded
watcher path, automatically advance exactly one turn, and leave a complete M5
success lifecycle in the same private journal.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal single-player match with schema-5 live state and no unresolved
  requirement reported at plan-authoring time.
- Fresh guarded FireTuner session, private M5 journal, and newly authored
  schema-1 TurnPlan.

**Procedure**

1. Prepared and live-preflighted a fresh guarded session, then started one
   schema-5 watcher with a new private journal and audit file.
2. Confirmed the stock UI showed Next Turn, created one explicit `end_turn`
   plan from the current watcher state, and passed read-only validation.
3. Executed the plan exactly once and observed the game enter the next turn.
4. Confirmed that the watcher emitted a new schema-5 snapshot for that turn.
5. Quit the game, restored the recorded host baseline, then verified and
   structurally inspected the private journal and redacted export offline.

**Observed result**

- M6 returned `completed` with reason `turn_ended`, one successful `end_turn`
  step, distinct before/after state digests, and a verified one-turn advance.
- The watcher captured validated schema-5 snapshots on both sides of the turn
  transition.
- The 12-record journal contained one start, eight snapshots, one command
  submission, one successful command result, and one turn transition.
- Full-chain verification passed, replay sequences were contiguous, and the
  redacted export reported matching structural counts. Journal, plan, and
  export permissions were all mode `600`.
- Shutdown restoration proved FireTuner disabled, no TCP 4318 listener or agent
  socket, firewall restored to disabled, and no Civ V rule, matching baseline.

**Conclusion**

confirmed. This run closes the required M5 and M6 target-machine gate: the
deterministic executor completed an explicit plan and automatically advanced
the turn, while the factual journal preserved the successful command lifecycle
and observed transition with its integrity, replay, export, privacy, and
recovery controls intact.

**Next step**

Proceed with the M8 reproducible release candidate, stable-version transition,
final artifact scans and hashes, and the documented tag procedure. Additional
live branches remain optional enhancement evidence rather than release blockers.

### 2026-09-17 — Schema 6 adjacent movement live proof

**Hypothesis**

The guarded watcher can expose a conservative schema 6 ordinary-movement target,
reject a source-coordinate request before sending a game write, and execute one
separately authorized adjacent move with an exact read-after-write proof.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal single-player opening state with one active owned land unit and a
  manually inspected adjacent empty land target.
- Fresh guarded FireTuner session, one watcher, and a private command audit
  outside the repository.

**Procedure**

1. Prepared the guarded firewall/FireTuner session and passed live preflight.
2. Started one watcher and confirmed a validated schema 6 snapshot containing
   at least one bounded `ordinary_move_targets` entry.
3. Submitted the selected unit's current source as a destination and observed
   pre-send admission rejection with unchanged location and movement points.
4. Re-read live state, confirmed the chosen target was still admitted, obtained
   explicit user authorization, and submitted exactly one adjacent move.
5. Observed the game UI and watcher after-state, then quit the game, confirmed
   the private audit mode, and restored the recorded host baseline.

**Observed result**

- The source-coordinate negative case returned an error before game submission;
  before/after state showed unchanged unit location and movement points.
- The authorized command moved exactly the selected unit to exactly the selected
  adjacent target in the same active turn and reduced its movement points.
- The watcher emitted the corresponding fresh after-state. No combat, capture,
  swap, embark/disembark, prompt, or movement by another unit occurred.
- The private audit file had mode `600`.
- Shutdown restoration proved FireTuner disabled, no TCP 4318 listener or agent
  socket, firewall restored to disabled, and no Civ V rule, matching baseline.

**Conclusion**

Confirmed. C6 supplies target-machine evidence for schema 6 conservative
ordinary-movement targets and the direct verified `move_unit` path on the
supported Campaign Edition build. The capability remains unreleased until the
D4/C7 compatibility, artifact, tag, and publication gates complete.

**Next step**

Reconcile the public contracts and downstream capability forecast with this live
evidence, then perform D4/C7 stabilization for the planned 1.1.0 release.

### 2026-09-18 — Schema 7 worker-build read attempt

**Hypothesis**

The guarded watcher can collect schema 7 current-plot and ordinary worker-build
candidate facts without changing game state or UI selection.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal disposable single-player state with an idle owned worker on a blank
  featureless land plot.
- Exact implementation commit `86934a3`, a recoverable guarded FireTuner
  session, and one private watcher audit path outside the repository.

**Procedure**

1. Prepared the recoverable session and proved the firewall, explicit Civ V
   incoming block, FireTuner setting, and absence of a pre-existing listener.
2. Started the game, passed live preflight, and started one schema 7 watcher.
3. Stopped immediately when the read-only `worker_builds` segment returned a
   Lua runtime error; no command, stale-source test, or build was attempted.
4. Quit the game and restored the recorded host baseline before investigation.

**Observed result**

- The target runtime exposes `GameInfoActions` as a table. Calling it as an
  iterator failed before a complete schema 7 snapshot was produced.
- The failure occurred during read-only collection. No worker action, command
  submission, turn advancement, or game-state change was attempted.
- Restoration proved FireTuner disabled, no TCP 4318 listener or agent socket,
  firewall restored to disabled, and no Civ V rule, matching the baseline.

**Conclusion**

Not confirmed. C6 stopped safely at its first read-only gate. The candidate
enumerator must use the target-proven indexed `GameInfoActions` table shape,
retain the sub-900-byte read bound, pass the complete offline gate again, and
receive fresh operator authorization before C6 restarts.

**Next step**

Replace the invalid callable-table loop with bounded numeric table iteration,
add a regression assertion that forbids `GameInfoActions()`, re-run C1–C5, and
publish the repaired implementation before scheduling another live attempt.

### 2026-09-19 — Schema 7 worker-build read retry

**Hypothesis**

The indexed-action repair allows the guarded watcher to collect schema 7
worker-build candidates without changing game state or UI selection.

**Environment**

- Original App Store Civilization V: Campaign Edition on the same target Mac.
- Normal disposable single-player state with an idle owned worker on a blank
  featureless land plot.
- Exact repair commit `e5a4186`, successful Python 3.11/3.13 CI, a fresh
  recoverable guarded FireTuner session, and a new private watcher audit path.

**Procedure**

1. Prepared a new recoverable session, started the game, and passed live
   preflight.
2. Started one watcher and stopped immediately when the read-only
   `worker_builds` segment returned a second Lua runtime type error.
3. Did not run the stale-source command or any build command.
4. Quit the game and restored the recorded host baseline before investigation.

**Observed result**

- Indexed `GameInfoActions` enumeration passed the prior failure point.
- The target `unit:CanBuild` binding rejected a Lua boolean option flag because
  its third explicit argument requires a number.
- No complete schema 7 snapshot, command submission, game write, or turn
  advancement occurred.
- Restoration again proved FireTuner disabled, no TCP 4318 listener or agent
  socket, firewall restored to disabled, and no Civ V rule.

**Conclusion**

Not confirmed. C6 again stopped safely at its read-only gate. The exact
Expansion 2 SDK binding uses `luaL_optint` for the visibility and gold flags,
with defaults `0` and `1`; generated read and write guards must therefore pass
integer flags rather than Lua booleans.

**Next step**

Accept ADR-0034, change both generated `CanBuild` calls to `(plot, build, 0, 1)`,
add exact-form regression coverage, re-run and publish the complete offline
gate, then require fresh operator authorization before another C6 attempt.

### 2026-09-19 — Schema 7 worker-build guarded command attempt

**Hypothesis**

The repaired schema 7 watcher can expose one UI-matching ordinary build,
reject a stale source before submission, and execute one separately authorized
build through the guarded selected-unit path.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal disposable single-player state with an idle owned worker on a blank,
  featureless owned land plot and one enabled ordinary improvement action.
- Exact implementation commit `28469a3`, successful Python 3.11/3.13 CI, a
  fresh recoverable guarded FireTuner session, and one private watcher audit
  path outside the repository.

**Procedure**

1. Prepared a new guarded session, passed live preflight, and started one
   watcher.
2. Compared the schema 7 worker/plot/candidate facts with the game UI and
   confirmed that reading caused no visible side effect.
3. Sent one deliberately stale source-coordinate request and confirmed that it
   was rejected with identical before/after state and no game-side change.
4. Reconfirmed the candidate, obtained separate authorization, and sent the
   exact build request once.
5. Did not retry after the response lacked a valid command marker; quit the
   game and restored the recorded host baseline before investigation.

**Observed result**

- Schema 7 produced the expected worker, blank plot context, and one candidate
  matching the enabled stock UI action without changing selection or state.
- The stale-source request failed before write submission. Unit location,
  movement, current build, improvement, and candidate remained unchanged.
- The authorized write program reached the target Lua parser but returned a
  syntax error before any valid command marker. The generated text joined
  interpolated numeric literals directly to keywords (`or` and `then`).
- The UI showed no started build and no movement decrease. Because the protocol
  could not prove a terminal write outcome, the session followed the mandatory
  no-retry path.
- Restoration proved FireTuner disabled, no TCP 4318 listener or agent socket,
  firewall restored to disabled, and no Civ V rule, matching the baseline.

**Conclusion**

Partially confirmed. The schema 7 read path, manual UI agreement, and safe
stale-source rejection now have target-machine evidence. The build-write gate
did not pass; absence of a valid marker remains an unknown protocol outcome
even though the parser error and UI both indicate no game change.

**Next step**

Separate interpolated numeric literals from Lua keywords, add exact lexical-
boundary regression coverage, re-run and publish the complete offline gate,
then require a fresh session and separate operator authorization for C6. Never
reuse or retry the failed command.

### 2026-09-19 — Schema 7 worker-build action-resolution retry

**Hypothesis**

The numeric/keyword boundary repair allows one fresh guarded session to pass
schema 7 observation, stale-source rejection, action resolution, submission,
and one exact worker-build postcondition.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal disposable single-player state with an idle owned worker on a blank,
  featureless owned land plot and one enabled ordinary improvement action.
- Exact implementation commit `74ba4d1`, successful Python 3.11/3.13 CI, a
  new recoverable guarded FireTuner session, and a new private watcher audit
  path outside the repository.

**Procedure**

1. Prepared the guarded session, passed live preflight, and started one schema
   7 watcher.
2. Confirmed that one reported worker-build candidate matched the enabled stock
   UI action and that reading caused no visible side effect.
3. Sent one deliberately stale source-coordinate request; confirmed explicit
   pre-write rejection and identical before/after state.
4. Obtained a fresh compact snapshot, reconfirmed the candidate, received
   separate authorization, and sent the exact build request once.
5. Stopped after the target returned an explicit `invalid_build` marker; did
   not retry, exited the game, and restored the recorded host baseline.

**Observed result**

- Schema 7, the UI, and the fresh pre-write snapshot agreed on the idle worker,
  blank plot, and one ordinary improvement candidate.
- The stale-source request changed no state and caused no UI side effect.
- The authorized request parsed successfully but the game-side program could
  not resolve the matching action because it indexed `GameInfoActions` by the
  build type string. The target had already proven this object is a numerically
  indexed table.
- A valid rejection marker was returned. Before/after states were identical;
  the game UI confirmed no build, movement loss, popup, other unit action, or
  turn advance.
- No retry occurred. Restoration proved FireTuner disabled, no TCP 4318
  listener or agent socket, firewall restored to disabled, and no Civ V rule,
  matching the baseline.

**Conclusion**

Partially confirmed. Read purity, candidate/UI agreement, stale-source
rejection, repaired Lua parsing, explicit terminal rejection, no-retry policy,
and exact restoration passed. The write postcondition remains unproven because
the write program used the wrong action-table lookup shape.

**Next step**

Resolve the action through bounded numeric `GameInfoActions` iteration while
matching its build Type, build SubType, and MissionData. Preserve every mutable
guard and the 1,000-byte limit, add a regression forbidding string-key lookup,
run and publish the complete offline gate, then require a fresh separately
authorized C6 session.

### 2026-09-19 — Schema 7 worker-build action-index retry

**Hypothesis**

Numeric action-table resolution allows the guarded write to pass build/action
mapping and produce one exact worker-build success branch.

**Environment**

- Original App Store Civilization V: Campaign Edition on the target Apple
  Silicon Mac.
- Normal disposable single-player state with an idle owned worker on a blank,
  featureless owned land plot and one enabled ordinary improvement action.
- Exact implementation commit `4a6433f`, successful Python 3.11/3.13 CI, a
  fresh recoverable guarded FireTuner session, and a fresh private watcher
  audit path outside the repository.

**Procedure**

1. Prepared the guarded session, passed live preflight, and started one schema
   7 watcher.
2. Confirmed candidate/UI agreement and no read side effect, then proved one
   stale-source request was rejected before submission with identical state.
3. Read a fresh matching snapshot, obtained separate authorization, and sent
   the exact build once.
4. Stopped after the target returned an explicit `blocked` marker; did not
   retry, exited the game, and restored the recorded host baseline.

**Observed result**

- The repaired numeric loop found the build action: the prior `invalid_build`
  rejection did not recur.
- The command returned a valid terminal `blocked` marker. Before/after state
  remained identical, and the UI confirmed no build, movement loss, popup,
  other unit action, or turn advance.
- Inspection of the installed BNW `UnitPanel.lua` showed that the numeric loop
  index is passed to `Game.CanHandleAction` and `Game.HandleAction`. The program
  instead passed the matched table entry's `ID` field, which is not the stock
  click-path action index.
- No retry occurred. Restoration proved FireTuner disabled, no TCP 4318
  listener or agent socket, firewall restored to disabled, and no Civ V rule,
  matching the baseline.

**Conclusion**

Partially confirmed. Numeric resolution now reaches the executability guard,
and terminal rejection, unchanged state, no-retry behavior, and restoration
all passed. The write postcondition remains unproven because dispatch used the
entry ID rather than the table index required by the stock UI path.

**Next step**

Retain the matched numeric loop index and pass that exact value to both
`Game.CanHandleAction` and `Game.HandleAction`. Add regressions forbidding entry
ID dispatch, preserve every guard and the byte bound, run and publish the full
offline gate, then require a fresh separately authorized C6 session.

### 2026-09-19 — Schema 7 worker-build successful active-build proof

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  using the guarded FireTuner workflow and exact implementation commit
  `04dd70f`.
- Disposable single-player state with an idle owned worker on a manually
  confirmed eligible plot and one enabled ordinary mine action.
- Private watcher audit and temporary artifacts outside the repository.

**Procedure**

1. Prepared the recoverable host state, passed live preflight, and started one
   schema 7 watcher.
2. Confirmed candidate/UI agreement and no read side effect, then proved a
   stale-source request was rejected before submission with unchanged state.
3. Read a fresh matching snapshot, obtained separate authorization, and sent
   the exact build once.
4. Compared the command read-back with a fresh watcher snapshot and the game
   UI, checked the private audit, exited the game, and restored the host.

**Observed result**

- The command returned verified success through the active-build branch. The
  same worker remained on the same plot in the same active turn, its movement
  fell from full to zero, and its current build became the exact requested
  mine while the improvement remained incomplete.
- All protected plot facts were unchanged. The independent watcher snapshot
  and game UI agreed that construction had started.
- No popup, unit movement, other unit action, or turn advance was observed.
- The private audit file was mode `600` and contained exactly the expected two
  lifecycle records.
- Shutdown verification reported FireTuner disabled, no TCP 4318 listener or
  agent socket, firewall restored to disabled, and no Civ V firewall rule,
  matching the recorded baseline. A repeated restore was safely idempotent.

**Conclusion**

C6 passed for the active-build success branch on the target Mac. The separate
immediate-completion branch retains deterministic offline evidence only; a
second live write is neither necessary nor authorized.

**Next step**

Prepare the D4/C7 compatibility, artifact, privacy, and release evidence for
1.2.0. Tagging and publication still require explicit release approval.

### 2026-09-19 — Schema 8 first target attempt and progress-binding diagnosis

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  using guarded FireTuner preparation and development commit `bd5ba1e`.
- Normal single-player ordinary-research action window with no technology
  currently selected.
- Schema 8 watcher with a private temporary audit location outside the
  repository.

**Procedure**

1. Prepared the recoverable host state, passed live preflight, and started one
   schema 8 watcher.
2. Inspected only the schema, research capability status, and runtime context;
   the operator confirmed no popup, selection, movement, research change, or
   turn advance.
3. Stopped the watcher and, after separate authorization, used bounded
   `pcall` diagnostics containing only research-read methods. Handshake-only
   timeouts sent no Lua and were not treated as evidence.
4. Queried exact/whole progress on the active team's technology object to
   identify the binding owner, then exited the game and restored the recorded
   host baseline.

**Observed result**

- Schema 8 framing, parsing, runtime-context shape, and visible read purity
  passed.
- `research_runtime_facts` failed closed as `unavailable` with
  `runtime_api_binding_unavailable`; no partial facts were emitted.
- `CvPlayer` exposed science times-100, overflow, effective research cost, and
  turns-left reads, but did not expose `GetResearchProgressTimes100`.
- `CvTeamTechs` exposed both exact times-100 and whole-point research-progress
  reads. The player whole-point value differed from team technology progress in
  this state, so substitution or multiplication would not preserve semantics.
- Shutdown verification returned FireTuner, port 4318, agent socket, firewall,
  and the Civ V firewall rule to the exact recorded baseline. The private audit
  was not independently inspected, so this attempt does not close the C4 audit
  row.

**Conclusion**

Partial diagnostic evidence only. The provisional schema 8 collector assigned
the exact progress method to the wrong Lua object and correctly failed closed.
ADR-0037 moves that read and its provenance to `CvTeamTechs` without changing
the field, units, schema, capability version, or any write contract. C4 remains
pending.

**Next step**

Complete the offline regression and artifact gate for the corrected binding,
then rerun the full bounded C4 procedure on its exact commit. Do not describe
the first attempt as successful schema 8 verification.

### 2026-09-21 — Corrected schema 8 overflow attempt and framing diagnosis

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  using guarded FireTuner preparation and implementation commit `aaa4212`.
- Ordinary single-player research action window with one naturally completing
  technology and a qualifying exact positive-overflow precondition.
- Published external supervisor v0.1.0, server-enforced read-only watcher, and
  private temporary artifacts outside the repository.

**Procedure**

1. Prepared the recoverable host state. Simultaneous framework application and
   watcher startup failed closed before TCP 4318 readiness; a separate generic
   launch phase then kept the verified application open, live preflight passed,
   and an `observe_verified` session started the watcher.
2. Started one read-only schema 8 watcher, read the research summary twice, and
   compared it with the stock UI in the same action window.
3. Manually advanced exactly one turn, closed the stock completion popup without
   selecting a replacement technology, and requested the next read.
4. Stopped after repeated framing errors, checked the private audit, ran one
   bounded read-only header diagnostic after the watcher stopped, exited the
   game, and restored the recorded host baseline.

**Observed result**

- Schema 8 was supported with phase
  `action_window_after_interturn_research_resolution`. Two reads were identical
  and caused no observed popup, selection, movement, research change, or turn
  advancement.
- The stock UI agreed with effective cost `2200`, displayed progress about
  `1900/2200`, science about `447`, and one turn remaining. The exact values
  were progress `189998` times-100 and science `44721` times-100.
- Exact remaining research was `30002` times-100 and the computed surplus was
  `14719` times-100, satisfying the positive-overflow precondition. The initial
  whole-point overflow was zero.
- After the manual interturn, the same watcher connection repeatedly reported
  `snapshot part appeared before snapshot header`; no post-completion overflow
  value was accepted or inferred. Closing the popup did not clear the error.
- After the watcher stopped, the exact header program returned a valid header
  on a fresh isolated read-only connection. This bounded the defect to
  response attribution on the old connection rather than the schema 8 header
  binding. A later independent handshake timed out and supplied no evidence.
- The private audit was mode `600` with zero records. Guarded shutdown restored
  FireTuner, TCP 4318, the agent socket, firewall state, and the Civ V rule to
  the exact original baseline.

**Conclusion**

Partial C4 evidence. Corrected `CvTeamTechs` progress, units, repeated-read
stability, UI agreement, runtime context, and the exact pre-overflow condition
passed. Post-interturn overflow and selection behavior remain pending. The run
identified command acknowledgement arriving before Lua output as the framing
condition addressed by ADR-0042; it is not a completed C4 proof.

**Next step**

Pass the complete offline, artifact, privacy, and CI gates for ADR-0042, then
repeat the controlled sequence on the exact repaired commit. Require the same
private bridge-session identity throughout the evidence sequence and stop
rather than infer continuity if recovery rotates it.

### 2026-09-21 — Repaired schema 8 controlled overflow and second framing diagnosis

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  using guarded FireTuner preparation and implementation commit `57c92a9`.
- The same ordinary single-player save supplied a natural positive-overflow
  case without debug writes or save editing.
- Published external supervisor v0.1.0, one server-enforced read-only watcher,
  and private temporary artifacts outside the repository.

**Procedure**

1. Passed guarded preparation and host-context live preflight, then supervised
   one repaired read-only watcher against the already running game.
2. Read the pre-completion snapshot twice, manually advanced one interturn,
   closed the completion popup, and read the no-research action window twice.
3. Manually selected the only ordinary candidate without advancing the turn,
   read twice, then manually advanced the following interturn and read again.
4. Stopped at the observed bridge-session rotation, checked the private audit,
   exited the game, and restored the recorded host baseline.

**Observed result**

- Schema 8 repeated reads were stable and read-only. The initial exact values
  again showed cost `2200`, progress `189998` times-100, science `44721`
  times-100, remaining `30002` times-100, and computed surplus `14719`
  times-100.
- The first interturn completed the technology on the original FireTuner TCP
  connection. The next action window required a new research choice and exposed
  positive whole-point overflow `144`. The difference between that game value
  and the direct exact surplus remained `3.19` research points and was not
  rewritten or explained away.
- Selecting the next ordinary technology left its exact team progress at zero
  and preserved overflow `144`. The legacy current-research progress field
  reported `144` in that same window, demonstrating that it cannot substitute
  for the schema 8 exact team-progress field.
- After the following interturn, the selected technology had exact progress
  `59174` times-100 and overflow was zero. The watcher had recovered a valid
  state, but both its bridge-session hash and FireTuner TCP endpoint changed,
  so the controlled sequence failed the same-session continuity gate.
- The private audit was mode `600` with zero records. Guarded shutdown restored
  FireTuner, TCP 4318, the agent socket, firewall state, and the Civ V rule to
  the exact original baseline.
- Host-context checks confirmed that restricted orchestration can misreport
  the firewall or reject private Unix-socket access; those sandbox results were
  excluded from safety evidence.

**Conclusion**

Partial C4 evidence. Post-completion positive overflow, selection-without-
consumption, and later application were observed, and ADR-0042 converted the
old permanent framing failure into bounded recovery. C4 is not complete because
the second interturn rotated the connection. The run exposed that an early
acknowledgement may be followed by multiple Lua-output frames; ADR-0043 drains
all such frames to the existing idle/total deadline.

**Next step**

Pass the complete offline and artifact gates for ADR-0043, then rerun the exact
controlled sequence. Preserve one bridge-session identity across both
interturns before closing C4, and separately investigate the observed `3.19`
point difference without inventing an overflow formula.

### 2026-09-21 — Schema 8 same-session controlled overflow proof

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  using guarded FireTuner preparation and exact implementation commit
  `95ef3df`.
- The same ordinary single-player save supplied a natural positive-overflow
  case without debug writes or save editing.
- Published external supervisor v0.1.0, one server-enforced read-only watcher,
  and private temporary artifacts outside the repository.

**Procedure**

1. Passed guarded preparation and host-context live preflight. The generic
   framework launched and identity-verified the application, while direct
   operator tooling passed the product launcher and continue screen; those UI
   steps were not execution-core evidence.
2. Started one `observe_verified` read-only watcher and read the pre-completion
   action window twice. The operator confirmed UI agreement and no visible read
   side effect.
3. Manually advanced one interturn, closed the completion popup without
   selecting a replacement, and read the no-research window twice.
4. Manually selected the ordinary replacement technology without advancing,
   read twice, then manually advanced the following interturn and read twice.
5. Stopped the watcher through the supervisor, checked the private audit and
   socket, exited the game, and restored the recorded host baseline. The
   attempted direct coordinate click on the game's exit confirmation did not
   activate `Yes`; the operator completed that confirmation manually.

**Observed result**

- Every repeated pair was stable and read-only. One bridge-session identity
  remained unchanged across the initial window, both interturns, and the
  selection-only window.
- The pre-completion state reported cost `2200`, exact progress `189998`
  times-100, science `44721` times-100, remaining `30002` times-100, computed
  surplus `14719` times-100, and whole-point overflow zero. The stock UI showed
  the corresponding rounded progress, science, and one turn remaining.
- The next action window had no current research, required a choice, and
  reported whole-point overflow `144`. Its science value was `44455`
  times-100 rather than the prior window's `44721`.
- Selecting the replacement technology left exact progress at zero and
  preserved overflow `144` in the same turn and bridge session.
- After the following interturn, exact progress was `59174` times-100 and
  overflow was zero, proving later application while retaining the same bridge
  session.
- The `3.19` point difference between the direct pre-completion surplus and
  reported whole-point overflow was preserved. The observed cross-turn science
  change is a plausible production-change explanation, but no formula or cause
  is claimed without a same-resolution binding.
- The private audit was mode `600` with zero records and the watcher socket was
  removed. The supervisor reports an explicitly requested SIGINT stop as exit
  130/failure; its sanitized report showed no output gap, truncation, timeout,
  recovery, or application shutdown.
- Guarded restoration returned FireTuner, TCP 4318, the agent socket, firewall,
  and the Civ V rule to the exact original baseline.

**Conclusion**

M11 C4 passes. ADR-0043 preserved framing and one bridge session across both
interturns, while schema 8 proved exact progress ownership, runtime units,
read purity, UI agreement, positive overflow, selection-time preservation, and
later application. The failed automated exit-confirmation click is external
UI-automation evidence only and does not weaken the completed read-only core
gate.

**Next step**

Complete D2/C5 documentation reconciliation, privacy and artifact scans,
reproducible builds, clean-install checks, and exact-commit CI for core 1.3.0.
Tagging and GitHub Release publication still require explicit approval.

### 2026-09-21 — Candidate SessionSpec v2 UI-gate diagnostic

**Environment**

- Original Civilization V: Campaign Edition on the target Apple Silicon Mac,
  guarded FireTuner preparation, and core commit `7b0ef47`.
- Candidate `local-app-test-automation` commit `d7784a7`, installed with its
  declared dependencies in a private temporary Python 3.12 environment.
- A core-generated mode-`600` SessionSpec v2 using the verified application
  path, exact window title, exact `AXButton`/`PLAY` selector, and reviewed
  `0.5/0.64` continue ratios. Private descriptors, runtime state, process IDs,
  checkpoint IDs, and raw diagnostics remained outside the repository.

**Procedure**

1. Passed guarded preparation and host-context ready preflight, then validated
   the private descriptor with the exact candidate framework.
2. Confirmed the launcher target out of band, authorized one AX press, and
   required a fresh frontmost observation before submitting the checkpoint.
3. Waited for the continue canvas, confirmed the calibrated target out of band,
   and separately authorized one relative click.
4. Stopped when that action failed, ran only bounded read-only selector and
   identity diagnostics, invoked cleanup-only recovery, and did not retry.
5. The operator exited the identity-changed application. Guarded restoration
   returned the host to its recorded baseline.

**Observed result**

- The exact launcher selector resolved one unique target and the framework
  recorded `ui.action_completed` for the authorized `PLAY` press.
- A long-running controller created while another app was frontmost did not
  observe a later foreground change, although a fresh process did. Ordering
  authorization after a fresh frontmost check allowed the first action.
- The relative continue step failed immediately with `ui_action_error` and no
  `ui.action_completed`. A subsequent read-only diagnostic found one frontmost
  target, the exact window, and the reviewed point; no successful click is
  inferred from that later observation.
- During launcher-to-game startup, the application retained its PID while its
  executable identity changed. Cleanup therefore returned `identity_changed`
  and retained `recovery_required` rather than acting on a different identity.
- The watcher never started. No watcher socket or command-audit file was
  created, and no core read or write command ran.
- After manual application exit, TCP 4318 was not listening and no target,
  watcher, or supervisor process remained. Guarded restore returned FireTuner,
  firewall state, and the Civ V firewall rule to the exact original baseline.

**Conclusion**

Partial external-automation evidence only. The exact launcher AX action passed,
but the two-step gate did not complete and supplies no watcher or read-only-
probe evidence. Further live runs are blocked on a framework-owned repair for
long-running frontmost refresh, a formal launcher-to-game identity handoff, and
retry of only proven pre-delivery transient UI-readiness failures. Core bridge,
schema, command, and executor behavior were not exercised or changed.

**Next step**

Review the repaired framework contract and exact commit before generating a
fresh private descriptor. Repeat both independently authorized UI gates, then
require server-reported `read_only: true`, same-session sanitized probes, zero
audit records, and exact host restoration. Do not relax identity, retry, or
cleanup constraints in this repository.

### 2026-09-21 — Redacted focused-application-unavailable diagnostic

**Environment**

- Target Apple Silicon Mac and original Civilization V: Campaign Edition.
- Execution-core commit `97257c2` and independently installed framework
  candidate commit `cca95b4`.
- Fresh guarded preparation, private mode-`600` descriptor, framework runtime,
  session, and checkpoint; no earlier authorization was reused.

**Procedure**

1. Independently verified ready preflight, generated and validated the private
   SessionSpec v2, launched one fresh session, and stopped at `PLAY`.
2. The operator visually confirmed `PLAY`, authorized that checkpoint exactly
   once, then returned focus toward Civ V.
3. Stopped on the first allowlisted failure reason without replaying the
   checkpoint or action.
4. Ran guarded restoration and independently verified host-context shutdown.

**Observed result**

- About 1.78 seconds after authorization, the durable reason was exactly
  `focused_application_unavailable`.
- No `ui.action_delivery_started` marker existed. No UI action, executable
  handoff, second checkpoint, watcher, watcher socket, audit record, FireTuner
  read, or game write occurred.
- The application terminated normally without recovery-required state.
- Restore and shutdown preflight confirmed firewall disabled, no Civ V rule or
  incoming block, FireTuner disabled, no agent socket, and TCP 4318 closed.

**Conclusion**

This was another safe external-framework failure before delivery, now bounded
to a temporary Accessibility focused-application observation gap. It is not an
execution-core descriptor or game-bridge failure. Framework commit `055d816`
treats only that exact condition, before delivery and with permission intact,
as readiness within the existing timeout; every other identity failure remains
terminal.

**Next step**

Complete exact-commit isolated-wheel and CI review, pin the repaired candidate,
then run a fresh operator-present two-checkpoint test. Do not reuse this session
or authorization.

### 2026-09-21 — Handoff-capable v2 pre-delivery focus diagnostic

**Environment**

- Target Apple Silicon Mac and original Civilization V: Campaign Edition.
- Execution-core commit `8ac5023` and independently installed framework
  candidate commit `ccae54f`.
- Guarded preparation began from firewall disabled, no Civ V rule, and
  FireTuner disabled, then reached the expected ready state before launch.

**Procedure**

1. Generated and validated one private mode-`600` SessionSpec v2 with the exact
   successor executable and two UI gates.
2. Started the framework session, visually confirmed the unique launcher
   `PLAY` button, and authorized only that checkpoint once.
3. Stopped immediately when the framework reported an identity error before
   action delivery. No authorization or action was replayed.
4. Ran guarded restoration and independently repeated host-context shutdown
   preflight.

**Observed result**

- Moving from the launcher to Codex to confirm the checkpoint made Codex the
  frontmost application at final pre-delivery revalidation.
- The framework recorded neither `ui.action_delivery_started` nor
  `ui.action_completed`; therefore `PLAY` was not delivered and no ambiguous
  click occurred.
- No identity handoff, second checkpoint, watcher, watcher socket, audit event,
  FireTuner read, or game write occurred.
- Framework cleanup terminated the still-verified application without a
  recovery requirement.
- Host-context shutdown preflight confirmed firewall disabled, no Civ V rule,
  no incoming block, FireTuner disabled, no agent socket, and TCP 4318 closed.

**Conclusion**

This is a safe pre-delivery failure and external-framework evidence only. It
identified a control-client focus race rather than an execution-core descriptor
or game-bridge defect. Framework commit `e7bc316` now treats only unchanged
target focus loss as bounded pre-delivery readiness; identity changes and all
post-delivery failures remain terminal.

**Next step**

Review the exact framework fix through an isolated wheel and CI. In the next
operator-present run, authorize each checkpoint once, return to the exact Civ V
window, and keep it frontmost while the framework waits and delivers at most
one action.

### 2026-09-21 — Focus-wait v2 generic-identity diagnostic

**Environment**

- Target Apple Silicon Mac and original Civilization V: Campaign Edition.
- Execution-core commit `1bdc5f9` and independently installed framework
  candidate commit `e7bc316`.
- Fresh private descriptor, runtime, session, and checkpoint; no prior
  authorization or session state was reused.

**Procedure**

1. Repeated guarded preparation and ready preflight from the restored baseline.
2. Generated and validated a new private SessionSpec v2, launched one new
   framework session, visually confirmed `PLAY`, and passed its checkpoint once.
3. Stopped on the first framework failure without retrying authorization or UI
   delivery.
4. Restored the host and verified shutdown in the host execution context.

**Observed result**

- About 1.5 seconds after the new checkpoint response, the session reported
  generic `ui_identity_error`.
- No `ui.action_delivery_started` or `ui.action_completed` event existed, so no
  UI action was delivered and no ambiguous click occurred.
- No handoff, second checkpoint, watcher, watcher socket, audit record,
  FireTuner read, or game write occurred.
- The application terminated normally without recovery-required state.
- Guarded restore and host-context shutdown preflight returned firewall,
  Civ V rule, FireTuner, socket, and TCP 4318 to the original baseline.

**Conclusion**

Safe external-framework failure before delivery. The generic error code was
insufficient to determine whether focus-query, process identity, window, or
element validation failed. It does not prove the earlier focus hypothesis and
does not expose an execution-core defect.

**Next step**

Use only a closed-set, value-free reason token on a future diagnostic attempt.
Do not persist exception messages or observed paths, identities, process
values, titles, AX content, or selectors. Review and pin the corrected
framework before another target run.

### 2026-09-21 — Bounded-readiness timeout diagnostic

**Environment**

- Target Apple Silicon Mac and original Civilization V: Campaign Edition.
- Execution-core commit `b19f915` and independently installed framework
  implementation commit `055d816`.
- Fresh guarded preparation, independent ready preflight, private mode-`600`
  descriptor/runtime/session, and one newly authorized `PLAY` checkpoint.

**Procedure**

1. Started exactly one fresh application/session and stopped at the first
   checkpoint with zero delivery.
2. The operator visually confirmed the unique yellow `PLAY` button and
   authorized that checkpoint once, then was instructed to return to Civ V.
3. Waited through the existing 300-second pre-delivery readiness deadline
   without replaying authorization or action.
4. On terminal failure, restored the guarded host session and independently
   repeated shutdown preflight.

**Observed result**

- The checkpoint was answered once. Exactly 300 seconds later the framework
  failed with `ui_identity_error` and generic reason
  `target_not_ready_timeout`.
- `ui.action_delivery_started` remained absent: no `PLAY` press, handoff,
  second checkpoint, relative click, watcher, audit event, FireTuner read, or
  game write occurred.
- Framework cleanup terminated the owned application; recovery was not needed.
- Restore and host-context shutdown preflight confirmed firewall disabled, no
  Civ V rule or incoming block, FireTuner disabled, no agent socket, TCP 4318
  closed, and no issues.

**Conclusion**

This is safe external-framework evidence before delivery. It confirms that a
readiness condition persisted for the entire deadline but the generic timeout
cannot identify which one. It does not contradict the earlier successful
launcher press, and it does not expose an execution-core or game-bridge defect.

**Next step**

Use a reviewed framework that preserves only the last allowlisted readiness
class at timeout. Do not introduce a focus fallback or repeat this target run
until exact-commit wheel, tests, CI, and execution-layer compatibility review
all pass.

### 2026-09-21 — First-checkpoint control-plane lifetime failure

**Environment**

- Target Apple Silicon Mac and original Civilization V: Campaign Edition.
- Execution-core commit `9346395` and independently installed framework
  implementation commit `c47b8cb`.
- Fresh guarded preparation, host-context ready preflight, a new private
  mode-`600` SessionSpec v2/runtime/session, and one visually confirmed first
  checkpoint.

**Procedure**

1. Established the guarded session in the execution layer and verified it in
   the unsandboxed host context. The ordinary Codex sandbox simultaneously
   reproduced its known false disabled/empty `socketfilterfw` view and was not
   accepted as authoritative.
2. Authorized one fresh framework launch only to the first `PLAY` checkpoint.
   Confirmed zero UI delivery and visually confirmed the yellow button.
3. Authorized that exact checkpoint once. The public control request failed
   because the active supervisor control socket was unavailable; no retry or
   replacement session was authorized.
4. Allowed the checkpoint to expire fail-closed, then restored the guarded host
   session and independently verified shutdown in host context.

**Observed result**

- The checkpoint remained recorded as awaiting a human until its five-minute
  deadline, but its control socket could not accept the answer.
- The final state was `checkpoint_expired` / `deadline_exceeded`.
- No checkpoint-answer event, `ui.action_delivery_started`, completed UI
  action, process handoff, second checkpoint, watcher, FireTuner read, or game
  write occurred.
- Framework cleanup terminated the owned application without recovery.
- Guarded restore and authoritative shutdown preflight returned FireTuner,
  listener, watcher socket, firewall, and Civ V rule to the original baseline.

**Conclusion**

Safe external-framework failure before delivery. The candidate framework does
not yet prove that its supervisor control plane remains reachable for the full
checkpoint lifetime. This is not a game-bridge write failure and must not be
worked around by replaying authorization or creating a replacement session.

**Next step**

Repair and independently verify framework control-socket lifetime, package the
exact candidate, and repeat execution-layer compatibility review before any
further target attempt.

### 2026-09-21 — Persistent host-hardening installation proof

**Environment**

- Target Apple Silicon Mac with Civilization V and the watcher stopped.
- Execution-core implementation commit `67dce37` and documentation commit
  `87c98a9`.
- Starting state: FireTuner disabled, TCP 4318 closed, no watcher socket,
  application firewall disabled, and no Civ V firewall rule.

**Procedure**

1. Ran the new `live_session harden` operation once from an interactive host
   terminal and completed local administrator authorization.
2. Required its structured result to identify the recorded original baseline
   and the protected idle state separately.
3. Independently ran `preflight hardened` in the host context after the
   mutation completed.

**Observed result**

- `harden` returned `ok=true` and `result=hardened`.
- The recorded baseline preserved firewall disabled, Civ V rule absent, and
  incoming block absent.
- Both the operation result and the later independent read showed FireTuner
  disabled, firewall enabled, Civ V rule present and blocking incoming
  connections, TCP 4318 closed, no watcher socket, and no issues.
- No game, watcher, FireTuner listener, UI action, bridge read, or game write
  occurred.

**Conclusion**

The one-time persistent guard and the read-only `hardened` phase are verified
on the target Mac. The private recovery record remains installed so subsequent
development sessions can retain the guard. Its contents and path were not
committed.

**Next step**

During the next authorized live test, prove that `prepare` and `restore` toggle
FireTuner while retaining the hardened firewall/rule state. Exercise
`unharden` only when the user actually wants to remove the persistent guard;
do not undo the desired development configuration merely to add coverage.

## 2026-09-22 — Candidate control repair and macOS 26 focus boundary

- Scope: operator-present SessionSpec v2 runs against core commit `38b43a3`
  and exact framework candidate `f7514af`; no game-state write was authorized.
- The first run reached and answered the unique launcher `PLAY` checkpoint
  through the repaired control socket. The framework remained before its
  delivery boundary for the full declared deadline and failed with sanitized
  `focused_application_unavailable`. It recorded zero UI deliveries, handoffs,
  later checkpoints, watcher starts, and game access.
- A second fresh run reached a new `PLAY` checkpoint but received no answer
  after operator presence was withdrawn. It expired as `checkpoint_expired`
  with zero delivery and terminated the owned launcher without recovery.
- A third fresh run answered its `PLAY` checkpoint and the operator returned
  the launcher to the foreground under the adjusted procedure. The same
  system-wide AX focused-application lookup remained unavailable for the full
  deadline. It again failed before delivery with zero handoff, later
  checkpoint, watcher, or game access.
- The execution layer exclusively ran each safety session. Every restore
  returned FireTuner, TCP 4318, and the watcher socket to closed state while
  retaining the enabled firewall and explicit Civ V incoming-block rule.
  Independent host-context `preflight hardened` passed after the final run.
- Result: the 0.5-second control-connection repair is target-confirmed for one
  checkpoint response. The remaining target gap is macOS 26 frontmost
  corroboration. Framework commit `51cebff` is accepted offline only after
  strict AX error classification; it has not yet received target evidence.

## 2026-09-22 — Strict AX candidate target rejection and bounded diagnosis

- Scope: one fresh operator-present SessionSpec v2 run using execution core
  `ddb67ff` and exact framework candidate `51cebff`; no game-state write was
  authorized.
- Fresh hardened/ready checks passed before launch. The user authorized the
  unique launcher `PLAY` checkpoint once. The framework recorded the answer,
  then failed before its delivery boundary with sanitized
  `focused_application_query`. UI delivery, handoff, later checkpoint, watcher,
  and game access counts remained zero; the owned launcher terminated without
  recovery.
- A post-restore, input-free binding diagnostic confirmed Accessibility trust
  was present while system-wide `AXFocusedApplication` returned
  `kAXErrorCannotComplete` (`-25204`) and a null value. The strict candidate
  therefore rejected the state as designed rather than treating an error as
  proof of absence.
- A second input-free diagnostic queried bounded application-level
  `AXFrontmost` values without retaining or printing application identities.
  Across 118 running applications, 10 reported true, 76 false, and 32 an AX
  error. Restricted to regular GUI applications, one reported true, 16 false,
  and none errored; accessory and prohibited processes accounted for the other
  true values.
- Restore returned FireTuner, TCP 4318, and the watcher socket to closed state
  while retaining the firewall and Civ V incoming-block rule. Independent
  host-context `preflight hardened` passed.
- Result: candidate `51cebff` passes its fail-closed target behavior but does
  not pass the functional `PLAY` gate. A future candidate must either preserve
  the block or formally bind any `kAXErrorCannotComplete` corroboration to the
  exact regular application and repeat that identity immediately before
  delivery. No further target retry is authorized yet.

## 2026-09-22 — Regular-application candidate unattended abort

- Scope: exact framework candidate `b1f99ef` and execution-core commit
  `7d27458`; no game-state write was authorized. Cross-task coordination later
  established that the user was not present at the Mac, so this run is safety
  evidence only and not a functional operator-present result.
- The first attempt used an overly long private runtime root and failed before
  application launch with sanitized `control_unavailable`. Public recovery
  found no application or child process to clean up. A shorter private runtime
  root then made the control endpoint available and launched the owned target.
  This observation does not prove the exact private failure cause.
- The framework requested one private `PLAY` checkpoint. About 41 seconds
  later, the execution-layer agent improperly translated an earlier user
  message, sent before this checkpoint existed, into `pass`. This was an
  agent-submitted public control request, not an automatic framework answer.
  The later cross-task absence notice arrived after submission, but the answer
  had already violated the fresh operator-present gate and is not valid
  evidence. The private checkpoint ID and raw event timestamps remain outside
  the repository.
- The target never became the verified frontmost application. The step expired
  as `target_not_frontmost` at the declared deadline, before delivery.
  No `ui.delivery_started`, handoff, later checkpoint, watcher start, FireTuner
  access, or game-state access was observed.
- The framework requested graceful quit and observed the owned application
  exit without recovery. The execution layer restored FireTuner and independently
  verified the persistent hardened state: firewall enabled, Civ V incoming
  blocked with its rule present, TCP 4318 closed, and watcher socket absent.
- Result: no functional claim is made. Do not retry until the user is physically
  present and freshly confirms readiness; checkpoint authority from this run is
  exhausted and cannot be reused. Future procedure forbids using any
  confirmation sent before the exact checkpoint is created or without a fresh
  same-task assertion of current Mac presence and matching step/nonce.

## 2026-09-22 — Fresh authorization gate rejects task-identity mismatch

- Scope: one new operator-present setup attempt using exact framework candidate
  `b1f99ef` and execution core `7a9eee3`; no game-state read or write was
  authorized.
- The hardened preflight passed, isolated framework/core wheels installed, the
  private SessionSpec v2 validated, and the framework requested the first
  `press_launcher_play` checkpoint. Before any checkpoint decision, the new
  execution-layer authorization helper rejected the current canonical Codex
  task identity because the implementation accepted UUIDv4 only while Codex
  had supplied UUIDv7.
- The execution layer submitted `abort`, not `pass`. The framework recorded
  zero UI deliveries, terminated the owned launcher, and never started the
  watcher or accessed FireTuner. Private checkpoint identity and raw event
  times remain outside the repository.
- Restore closed FireTuner, TCP 4318, and the watcher socket while retaining
  the persistent firewall and Civ V incoming-block rule. An independent
  `preflight hardened` check passed afterward.
- Result: this is fail-closed compatibility evidence, not functional UI
  evidence. The helper now accepts canonical execution-task UUIDv4 or UUIDv7
  while retaining UUIDv4 for framework checkpoint identity; a completely new
  session and checkpoint are required for the next attempt.

## 2026-09-22 — Operator-present v2 PLAY delivery and incomplete handoff

- Scope: exact framework candidate `b1f99ef`, wheel digest
  `cc57a78719507ac65795169d7f87a7c8c58de7d793680f8360bb1de4d2175685`,
  and execution core `4028796`. The installed wheels ran from separate private
  environments. The session authorized only the declared UI steps and a
  read-only watcher; it authorized no game-state write.
- An initial fresh checkpoint expired without a response. Its framework session
  failed with `checkpoint_expired`; FireTuner was restored, and independent
  `preflight hardened` passed before a new session was created.
- In the new session, the operator sent the exact nonce-bearing PLAY response
  after the checkpoint request. The private helper accepted and consumed its
  mode-0600 ticket before the execution layer submitted one `pass`.
- Framework events recorded `ui.action_delivery_started` and
  `ui.action_completed` for `press_launcher_play`, followed by
  `identity_handoff.pending`. A read-only screen observation and the operator
  both saw the game's `Click to Continue` screen. A host process read showed
  the original PID running the declared game executable, while the framework's
  persisted application identity still named the launcher executable.
- No `identity_handoff.completed` or second checkpoint appeared. The framework
  waited its declared five-minute handoff interval, then reported
  `application_identity_error` and `recovery_required`. No continue click,
  watcher start, FireTuner connection, or game-state read was observed. This
  establishes a handoff-recognition failure, but the available evidence does
  not isolate which candidate/probe check withheld acceptance.
- Framework recovery remained `cleanup_incomplete` because it would not act
  on the changed executable identity. The operator exited the game manually;
  a host process check confirmed the tracked PID absent. A later framework
  recovery check still reported `cleanup_incomplete`, so no framework-clean
  outcome is claimed.
- The execution layer restored FireTuner. Independent `preflight hardened`
  confirmed the firewall enabled, the explicit Civ V incoming block present,
  TCP 4318 closed, and watcher socket absent. Private checkpoint IDs, nonce,
  raw event times, process ID, and local paths remain outside the repository.
- Result: the one-use authorization gate and automated PLAY delivery now have
  target evidence. The complete v2 flow remains unverified until the separate
  framework fixes and proves identity handoff and second-step continuation.

## 2026-09-22 — Closed-set handoff diagnosis after gated PLAY

- Scope: independent framework candidate `84404c3`, exact wheel digest
  `dc3e9a8af74ccc150b76cbca8a2c4eec3ab69f77b1ea9f2b8f842f2303de0896`,
  with a private SessionSpec v2, protected FireTuner session, and read-only
  watcher declared only after both UI gates. No game-state write was authorized.
- A fresh post-request one-use PLAY authorization produced one
  `ui.action_completed`, then `identity_handoff.pending`. Five minutes later
  the framework reported `ApplicationHandoffTimeoutError` with the closed-set
  reason `candidate_absent`. In that timeout iteration, its process probe had
  accepted the declared successor executable but AppKit bundle enumeration
  had no candidate. There was no second checkpoint, continue click, or watcher.
- Framework recovery remained incomplete. The operator exited Civ V normally;
  the execution layer restored FireTuner and independently verified the
  hardened idle state, including firewall/Civ V inbound blocking and closed
  TCP 4318. Private session IDs, process IDs, and paths remain outside the
  repository.
- Result: this isolates an AppKit candidate-enumeration gap during the exact
  handoff. It does not establish that a fallback is safe or successful on the
  target; that requires a separate candidate and run.

## 2026-09-23 — Exact-PID handoff passes; continue click stopped before delivery

- Scope: framework candidate `d531450`, exact wheel digest
  `738c561c0f1d651c0ddba6a12275e44264b1eacc2f5fef1b641266133fb66157`,
  independently checked and installed in a private framework environment.
  The execution core remained a separate wheel installation. The fresh
  SessionSpec v2 retained two independent one-use UI gates and a server-enforced
  read-only watcher. No game-state write was authorized.
- Protected idle preflight passed before `prepare`; the ready state retained
  macOS firewall and explicit Civ V inbound blocking. The operator authorized
  the exact PLAY checkpoint after its request. Framework events recorded one
  PLAY delivery and `identity_handoff.completed`, then requested the second
  `click_game_continue` checkpoint.
- After a separate fresh second-step authorization, the framework immediately
  failed `ui_identity_error` with allowlisted reason
  `focused_application_query`. There was no second
  `ui.action_delivery_started`, so no continue click was attempted and the
  watcher never started. The saved events do not distinguish the initial
  frontmost query from the final pre-delivery frontmost revalidation.
- Cleanup reported `identity_changed` and required recovery. The saved
  resource record contains an old launcher AppKit candidate executable and
  the accepted new game process executable, but no fresh stop-time process
  snapshot or termination-branch trace. That record permits, but does not
  prove, an AppKit candidate mismatch; the exact cleanup cause is unresolved.
- The operator exited normally. A process check found no Civ V or watcher;
  `restore` closed FireTuner, and independent `preflight hardened` passed with
  firewall enabled, Civ V inbound blocked, TCP 4318 closed, and watcher socket
  absent. No private checkpoint, PID, runtime path, or raw snapshot is committed.
- Result: automated PLAY, same-process executable handoff, and second
  checkpoint creation have target evidence. Continue click, watcher startup,
  and complete v2 composition do not. Do not reuse either authorization.

## 2026-09-23 — Candidate focus-query category after exact handoff

- Scope: independently reviewed framework candidate `192391e`, fixed wheel
  SHA-256 `3ad709c60f7a375e75b88a2e13b23b3d6afc084bee71b584124a1b37907a2a5a`,
  a private SessionSpec v2, protected FireTuner session, and server-enforced
  read-only watcher declared only after both UI gates. No game-state write or
  direct game command was authorized.
- The operator supplied a new same-task nonce response after each separate
  checkpoint request. Framework events recorded one PLAY delivery,
  `identity_handoff.completed`, and creation of the continue checkpoint.
  The second authorization was accepted, but the next event was
  `ui_identity_error` with closed-set `focused_application_query`,
  `focus_stage=selection`, and `focus_detail=candidate_query_error`.
- There was no second `ui.action_delivery_started` event. The framework did
  not click `Click to Continue` or start the watcher, and it performed no
  game-state read. The classification identifies the candidate frontmost
  query at initial step selection; it does not expose the raw AX error code or
  establish why that query failed.
- The framework requested normal application termination but reached its
  ten-second cleanup deadline before observing exit. A later process check
  found Civ V and watcher absent without any force termination. The execution
  layer restored FireTuner; independent `preflight hardened` confirmed firewall
  enabled, the Civ V inbound block present, TCP 4318 closed, and watcher socket
  absent. Cleanup-only framework recovery then reached a terminal failed
  state, not a successful session.
- Result: exact-PID handoff remained successful, but the v2 end-to-end flow
  remains unverified. This run provides a bounded framework-side focus-query
  diagnosis for offline investigation. Neither one-use authorization can be
  replayed. Private checkpoint values, PID, and runtime paths are omitted.

## 2026-09-23 — Candidate AX frontmost failure classified before continue delivery

- Scope: independently reviewed framework commit `04189d3`, exact wheel
  SHA-256 `4b965fefa0eb51d6a7486eedd03ea2c9c093fa4015356c540a47bdd9db057f86`,
  a private SessionSpec v2, protected FireTuner session, and watcher declared
  read-only after both UI gates. No game-state write was authorized.
- The first local attempt failed before app launch because the isolated
  validation-only environment lacked macOS UI dependencies. It requested no
  checkpoint and performed no UI action. A new session used an independently
  installed exact-candidate wheel with the required UI dependencies.
- The operator supplied a fresh same-task nonce after each checkpoint request.
  `PLAY` was delivered once, and `identity_handoff.completed` preceded the
  second checkpoint. The second authorization was accepted, but the next
  event was terminal `ui_identity_error` with
  `focus_stage=selection`, `focus_context=system_cannot_complete`, and
  `focus_detail=candidate_cannot_complete`. There was no second
  `ui.action_delivery_started`, no continue click, no watcher startup, and no
  game-state read. The classification does not establish why AX could not
  complete or justify a fallback or retry.
- The framework's graceful-exit request timed out. A later narrow process
  check found Civ V and watcher absent; cleanup-only recovery reached a
  terminal failed state. `restore` disabled FireTuner, and independent
  host-context `preflight hardened` confirmed firewall enabled, Civ V incoming
  blocked, TCP 4318 closed, and watcher socket absent. No force termination
  was used. Private checkpoints, nonces, PIDs, times, and runtime paths remain
  outside the repository.
- Result: two-step v2 composition remains unverified. The precise closed-set
  frontmost-query classification is handed to the independent framework task
  for offline root-cause investigation. Neither authorization can be reused.

## 2026-09-23 — One-second candidate AX timeout fails the same pre-delivery check

- Scope: independently reviewed framework commit `d7a51aa`, exact wheel
  SHA-256 `ebe64c31987b3c524ab8dcaf789c625bced01aa11df1aedce225630261847de0`,
  protected FireTuner session, private SessionSpec v2, and read-only watcher
  declared only after both UI steps. No game-state write was authorized.
- An initial attempt ended before application launch with
  `control_unavailable`, zero checkpoints, and zero UI actions. Its private
  control-socket path was 105 bytes; a Unix socket path-length limit is the
  likely cause, not established by a retained raw exception. A new short-path
  session passed descriptor and ready-state checks; the failed session was not
  resumed or given an authorization.
- In the new session, each checkpoint received a fresh same-task nonce only
  after its request. The framework completed one `PLAY` delivery and
  `identity_handoff.completed`, then requested the continue checkpoint. After
  its separate authorization, the next event was terminal `ui_identity_error`:
  `focus_stage=selection`, `focus_context=system_cannot_complete`, and
  `focus_detail=candidate_cannot_complete`. There was no second
  `ui.action_delivery_started`, no continue click, no watcher startup, and no
  game-state read.
- The framework requested normal game exit but timed out after ten seconds.
  A subsequent narrow process check found Civ V and watcher absent. Cleanup-
  only recovery reached a terminal failed state; `restore` closed FireTuner,
  and independent host-context `preflight hardened` confirmed firewall
  enabled, Civ V incoming blocked, TCP 4318 closed, and watcher socket absent.
  No force termination was used. Private checkpoint values, nonces, PIDs,
  times, and local runtime paths remain outside this repository.
- Result: raising only the exact-candidate AXFrontmost messaging timeout from
  0.25 to 1.0 seconds did not resolve the target-observed error. It does not
  prove a different timeout would help. The v2 end-to-end flow remains
  unverified; framework-side root-cause analysis must remain fail-closed.

## 2026-09-23 — Same-candidate AXRole probe also cannot complete

- Scope: independently reviewed framework commit `70b6342`, exact wheel
  SHA-256 `0be1ebe491c80a1bb90e95a8a6fc1a17a096238c61960147c0ba677884f2c0f1`,
  protected FireTuner session, private SessionSpec v2, and read-only watcher
  declared only after both UI gates. No game-state write was authorized.
- The operator supplied fresh same-task one-use authorization at each separate
  checkpoint. Framework events recorded one `PLAY` delivery,
  `identity_handoff.completed`, and the continue checkpoint. After the second
  authorization, `session.failure` reported `ui_identity_error` with
  `focused_application_query`, `focus_stage=selection`,
  `focus_context=system_cannot_complete`,
  `focus_detail=candidate_cannot_complete`, and
  `focus_probe=role_cannot_complete`. The diagnostic AXRole read on the same
  candidate element could not complete either.
- No second `ui.action_delivery_started` occurred. The framework did not
  click Continue, start the watcher, or read game state. The AXRole result
  weakens an AXFrontmost-only explanation but does not establish the underlying
  AX failure, justify another focus source, or authorize a retry.
- The framework requested normal application exit but did not observe it by
  its cleanup deadline. A later narrow process check found both game and
  watcher absent. Cleanup-only recovery reached a terminal failed state;
  `restore` closed FireTuner, and independent host-context
  `preflight hardened` confirmed firewall enabled, Civ V incoming blocked,
  TCP 4318 closed, and watcher socket absent. No force termination was used.
  Private checkpoints, nonces, PIDs, times, and runtime paths remain outside
  this repository.
- Result: the ADR-0060 diagnostic has target evidence, but the v2 end-to-end
  flow remains unverified. The closed-set result was sent to the independent
  framework task for offline root-cause analysis; neither authorization can
  be reused.
