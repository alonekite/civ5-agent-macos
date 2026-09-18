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
