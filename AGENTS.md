# Codex Instructions

Target: Civilization V on Apple Silicon macOS.

## Primary objective
Prove a reliable bidirectional bridge:
`Civ V Lua mod ↔ external Python`

## Hard constraints
- Do not assume Windows DLL compatibility.
- Do not assume Civ V Lua has unrestricted io/os/socket/HTTP/filesystem access.
- Treat every IPC mechanism as unverified until tested on the target machine.
- Prefer Civ V-supported Lua APIs.
- Whitelist actions.
- Verify every write action by re-reading state.
- Keep experiments reproducible and logged.

## Engineering order
1. inspect environment
2. prove read
3. prove write
4. add verification
5. deterministic controller
6. LLM
7. optional MCP

## Definition of done for MVP
`python -m civ5_agent.watch` shows live game-state changes, and
`python -m civ5_agent.command end_turn` advances one turn and returns verified success.
