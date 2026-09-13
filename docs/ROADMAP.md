# Roadmap

## Phase 0 — Machine reconnaissance
- [x] Locate Civ V installation
- [x] Locate user/mod directories
- [x] Confirm application version and bundled DLC content
- [x] Test custom Lua mod loading path (mod is scanned, but this App Store build
  forcibly hides the Mods browser; activation/loading is rejected on the stock build)
- [x] Check TCP 4318 (disabled initially; enabled reversibly and verified in-game)
- [x] Add read-only preflight checks for guarded startup, live use, and shutdown
- [x] Record results

Phase 0 reconnaissance was run on 2026-09-12. See `docs/EXPERIMENT_LOG.md`.
Phase 0 found that this Campaign Edition hides its Mods browser, but also proved
a stock, signed-app route around that product limitation: enable the bundled
FireTuner endpoint in user-owned `config.ini` and use its localhost protocol.
No application-bundle modification is required.

## Phase 1 — Minimal read PoC
- [x] Export turn
- [x] Export active player id
- [x] Export gold
- [x] Python detects turn N → N+1 without screen reading

## Phase 2 — Rich read state
- [x] cities
- [x] research
- [x] units
- [ ] diplomacy
- [ ] victory progress if accessible

## Phase 3 — Write PoC
- [x] Python submits `end_turn`
- [x] Lua sees command
- [x] game advances
- [x] acknowledgement
- [x] Python verifies state change

## Phase 4+
- [x] research selection (live-verified with `TECH_POTTERY`)
- [x] city production (live-verified with `UNIT_SCOUT`)
- [ ] unit skip (implemented and unit-tested; live verification pending)
- [ ] coordinate-based unit movement
- [x] deterministic policy (live-verified refusal and successful execution paths)
- [ ] LLM controller
- [ ] optional MCP wrapper
