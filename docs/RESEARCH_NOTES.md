# Research Notes

Current working conclusions:
- Civ V Lua can access internal game state.
- Windows projects demonstrate external read/write, but some depend on Windows-only DLLs.
- [`corytodd/civ5-mcp`](https://github.com/corytodd/civ5-mcp)
  demonstrates a Lua-to-database bridge and MCP server; its README says it has
  only been tested on Brave New World for Windows.
- [`vox-deorum/vox-deorum`](https://github.com/vox-deorum/vox-deorum)
  demonstrates richer LLM integration but relies on a modified Windows
  GameCore DLL / Vox Populi stack.
- The installed App Store Campaign Edition hides its Mods browser, so discovered
  custom mods remain disabled on the stock build.
- FireTuner/TCP 4318 is exposed after reversibly setting `EnableTuner = 1` in
  user-owned `config.ini`.
- Python completed a real bidirectional FireTuner round trip against Lua state
  ID 172 (`InGame`) and read turn 1, player 0, and 3 gold from a live match.
- The old server behaves as a single-client endpoint and can retain a closed
  connection in `CLOSE_WAIT`; prefer one persistent client connection.

Open questions:
1. Does the implemented unit-specific `skip_unit` action work on this build?
2. Which additional victory-progress fields are stable enough to add?
3. What is the smallest safe coordinate-movement API with reliable read-back?

Resolved since the initial notes:

- The watcher now owns the sole persistent FireTuner connection and exposes a
  per-user mode-0600 Unix socket for serialized read/write requests.
- `end_turn` has been verified live with before/after state.
- `choose_research` and `set_city_production` use the same stock APIs as the
  bundled UI and have been live-verified with strict identifiers, capability
  checks, and read-back verification.
- Snapshot schema 2 and the deterministic controller have been live-verified.
- Snapshot schema 3 has offline-tested score, era, and met-major diplomacy
  records derived from the bundled Brave New World UI; live verification is
  pending.
- The MVP read/write loop is complete; unit skip is the next live experiment.
