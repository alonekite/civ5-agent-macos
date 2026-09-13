# Civ5 Agent on macOS (Apple Silicon)

Goal: build a reusable, testable read/write core between **Civilization V
running on Apple Silicon macOS** and external Python, backed by versioned
ruleset knowledge and a deterministic controller.

## Core question
Can a Lua mod running inside Civ V on an M4 Mac:
1. read game state,
2. export that state to an external Python process,
3. receive commands from Python,
4. execute safe game actions,
5. report success/failure back?

This repository does not implement MCP or LLM decision-making. Its job is to
provide safe, deterministic game I/O, ruleset knowledge, and verification.

Status: the low-level MVP was verified end-to-end on the target Mac on
2026-09-12. The watcher observed a live rich snapshot and the command CLI
advanced turn 0 → 1 with verified before/after state.

Snapshot schema 3 additionally reads the active player's score and era, city
growth/production progress, owned-unit health and strength, and met major
civilizations' public diplomacy state. It also reports whether science victory
is enabled and the active team's Apollo/spacecraft project counts. Its parser
and validation are offline-tested and retain schema 2 compatibility; schema 3
still requires a bounded live-game verification before it is considered
confirmed. City food and production rates use Civ V's exact times-100 integers
rather than rounded floats.

This is an unofficial, independently developed project. It is not affiliated
with or endorsed by Firaxis Games, 2K, Aspyr, or Apple, and it does not include
Civilization V binaries or assets.

## Target architecture
```text
Civilization V
   │ Lua mod
   ▼
Bridge storage / IPC
   ├── state: Civ V → Python
   └── commands: Python → Civ V
   ▼
Python controller
   ▲
   │
Versioned ruleset knowledge
```

Verified transport on the target App Store build: bundled FireTuner over
localhost TCP 4318, enabled through the user-owned game configuration. The
signed application bundle remains unchanged.

Fallbacks:
- `Modding.OpenUserData()` / database-backed persistence on a distribution that exposes Mods
- other Civ V-supported persistence/event mechanisms

Out of scope:
- Windows-only GameCore DLL approaches
- mouse/keyboard automation
- screen OCR
- LLM decision-making
- MCP integration

## MVP success criteria
Read: turn, active player, gold, capital/cities, research, units.
Write: end turn, choose research, choose city production.
Every command must return an id, status, before-state, after-state, and error if any.

## Verified live read

Before starting a live session, enable the macOS application firewall, add an
explicit block-incoming rule for Civ V, and enable FireTuner. Then run the
read-only preflight check:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight ready
```

The check fails closed unless FireTuner, the firewall, and the explicit Civ V
rule are all present. The configuration helper itself refuses `enable` until
the firewall and rule are verified, then creates a timestamp-preserving backup
and verifies the changed line:

```bash
bash scripts/configure_firetuner.sh enable
```

Security note: this specific game build was observed listening on `*:4318`,
not only loopback. Do not leave FireTuner enabled on an untrusted network,
especially if the macOS application firewall is disabled. Restore the setting
and quit Civ V when the test session ends.

Then run:

```bash
PYTHONPATH=src python3 -m civ5_agent.preflight live
PYTHONPATH=src python3 -m civ5_agent.watch --once
PYTHONPATH=src python3 -m civ5_agent.watch
```

The `live` check additionally requires a TCP 4318 listener. Neither preflight
mode changes the game, its configuration, or firewall settings.

The FireTuner watcher enforces the same `live` check before connecting, and
rechecks it before every watcher-mediated write. A direct command also checks
before connecting. Only the verified local endpoint `127.0.0.1:4318` is
accepted; custom or remote FireTuner endpoints fail closed.

The first command prints one JSON snapshot. The second keeps one FireTuner
connection open and prints only when the observed state changes. On this old
build, a persistent connection is preferable because the game can retain a
closed client socket until its UI processes another event.

While the long-running watcher is active it also owns a per-user, mode-0600
Unix socket. This lets a second terminal submit the sole allowlisted write
without opening a competing FireTuner connection:

```bash
PYTHONPATH=src python3 -m civ5_agent.command end_turn
```

The command first reads the before-state, asks Civ V whether ending the turn is
currently allowed, submits `CONTROL_ENDTURN` only when allowed, then polls until
it can prove the turn number advanced. A blocker or verification timeout is an
error and includes the before/after state in its JSON result.

The deterministic controller can inspect the same watcher snapshot without
using an LLM:

```bash
PYTHONPATH=src python3 -m civ5_agent.controller
```

It conservatively reports one of: wait, choose research, choose production,
issue unit orders, or end turn. Add `--execute` only when it should submit an
end-turn decision through the same verified command path.

## Versioned ruleset knowledge

`civ5_agent.knowledge` stores facts that belong to a Civ V ruleset rather than
one saved game. It uses canonical JSON, stable game identifiers, typed
relations, source hashes, and strict referential-integrity validation. AI flavor
and personality parameters are explicitly rejected.

The read-only importer currently extracts 81 BNW technologies, 8 eras, 148
unit types, 214 promotions, and their technology, era, prerequisite, and free
promotion relations from the merged SQLite cache on the tested Campaign Edition
installation. It also preserves 83 unit classes and their default and upgrade
relationships, plus 111 policies and 12 policy branches with their core effects
and prerequisite graph. The database itself and other game assets are not
copied into this repository. Generate a local artifact with:

```bash
PYTHONPATH=src python3 -m civ5_agent.knowledge.import_sqlite \
  --database "/path/to/Civ5DebugDatabase.db" \
  --source-label cache/Civ5DebugDatabase.db \
  --family bnw \
  --game-version 1.0.3.279 \
  --output technologies.json
```

The importer excludes AI weights and flavor tables, Civilopedia prose, quotes,
icons, and audio. It also refuses to read a database with an active write-ahead
log or one that changes during extraction. Active DLC package IDs are read from
the database, and the requested vanilla/G&K/BNW family must match the detected
expansion content. See
[docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) for the data contract and reuse policy.

Two additional allowlisted commands were verified in a bounded live-game
session on the target Mac:

```bash
PYTHONPATH=src python3 -m civ5_agent.command choose_research TECH_POTTERY
PYTHONPATH=src python3 -m civ5_agent.command set_city_production 8192 unit UNIT_SCOUT
```

Research identifiers must match `TECH_[A-Z0-9_]+`. Production accepts only a
non-negative city ID, one of `unit|building|project`, and the corresponding
`UNIT_*`, `BUILDING_*`, or `PROJECT_*` identifier. Both commands check Civ V's
own capability predicate and verify the resulting snapshot. The live test
observed `null -> TECH_POTTERY` and empty production -> `TXT_KEY_UNIT_SCOUT`.

A unit-specific skip command is implemented and unit-tested, pending one
bounded live verification:

```bash
PYTHONPATH=src python3 -m civ5_agent.command skip_unit 16385
```

It accepts only a non-negative unit ID, proves the unit belongs to the active
player, clears and re-establishes the UI selection on that exact unit, checks
the stock action predicate, and succeeds only after the same unit is observed
at the same coordinates with zero movement.

Every watcher-mediated command is appended to
`~/Library/Logs/civ5-agent/commands.jsonl`. The directory and JSONL file are
created with private permissions, and the file contains canonical UUIDv4
command IDs, validated arguments, and full before/after game snapshots. The
local bridge rejects caller-supplied IDs that are not UUIDv4. Use `--audit-log
PATH` to choose another location. An audit write failure is reported separately
and never causes an already-run game action to be retried.

To restore the original configuration later:

```bash
bash scripts/configure_firetuner.sh restore
PYTHONPATH=src python3 -m civ5_agent.preflight shutdown
```

The shutdown check succeeds only when FireTuner is disabled, TCP 4318 is not
listening, and the agent Unix socket is absent.

## Security

On the tested Campaign Edition build, enabling FireTuner made Civ V listen on
`TCP *:4318`, not loopback only. That endpoint accepts Lua commands and has no
authentication observed by this project. Use it only for bounded development
sessions. See [SECURITY.md](SECURITY.md) before enabling it. For the next
schema-3 and unit-action verification, follow the ordered
[bounded live-test checklist](docs/LIVE_TEST_CHECKLIST.md).

## Prior art and references

This repository is an independent macOS implementation, not a fork. The design
was informed by these projects and by the Lua/XML sources bundled with the
user's installed copy of Civilization V:

- [corytodd/civ5-mcp](https://github.com/corytodd/civ5-mcp) — an MIT-licensed
  Civ V Lua/database bridge and MCP server documented as Windows-only.
- [vox-deorum/vox-deorum](https://github.com/vox-deorum/vox-deorum) — a larger
  LLM-enhanced Civ V/Vox Populi system whose game layer uses a modified Windows
  GameCore DLL.

No source files from either project are vendored here.
