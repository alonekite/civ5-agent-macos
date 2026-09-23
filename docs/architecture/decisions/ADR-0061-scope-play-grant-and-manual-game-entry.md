# ADR-0061: Scope one PLAY grant to a user-initiated session and require manual game entry

Status: Accepted for provisional SessionSpec v2 compatibility; target use pending

Date: 2026-09-23

## Context

The ADR-0060 target run showed that post-handoff `AXFrontmost` and `AXRole`
both returned `cannot_complete` before the automatic Continue click. Repeating
that click path would not be justified. The operator instead chose to initiate
each protected session, allow one automatic launcher PLAY, then personally
complete Continue and any save loading or game creation before read-only
observation begins.

## Decision

Pin provisional framework commit
`3402862a43e9c29e056a42ecb75d90a04222684b` and its independently built
wheel SHA-256
`285251f0cabbcd98bfbb8c0a709aab5ba630192ea1d86706e72de9e2a77ab9a6`.
Its SessionSpec v2 optional `manual_gates` run after all UI steps and identity
handoffs but before any child process. The execution-layer candidate emits one
exact `press_launcher_play` AX action with the previously verified same-PID
game-executable handoff, one `manual_game_entry` gate, and the unchanged
server-enforced read-only watcher. It emits no Continue click coordinates or
other automatic game-canvas action.

PLAY may be passed without a new per-click user message only when the same
execution task has received a fresh exact user initiation for this one
protected read-only session. A private mode-0600 one-use grant is created only
after the framework requests the exact PLAY checkpoint; it binds framework
session ID, checkpoint ID, canonical SessionSpec digest, execution task ID,
initiation and checkpoint times, and a short expiry. Consumption precedes
framework `pass`. There is no generic auto-pass, persistent authorization,
old-nonce reuse, or authority for another UI step or session. The composition
root must independently verify message provenance, active checkpoint data,
and user presence; a local file cannot prove who sent a message.

The manual gate is not an automated click. After it is requested, the
composition root tells the operator in Chinese to click Continue and complete
save loading or game creation. Only a fresh same-task explicit completion
message may pass the gate, using a one-use post-request challenge. That
attestation does not prove game state. Before gate pass, the composition root
must recheck the exact tracked application and guarded `preflight live` state.
After watcher startup, the read-only capability probe must require a valid
same-session active-player-turn snapshot. Failure closes the session without
retrying PLAY or starting a second watcher.

## Compatibility and evidence

- Existing v1 and two-click v2 builders remain available and unchanged in
  their emitted shapes; the new builder is a separate operational preview.
- The framework commit passed its four-cell macOS CI and wheel gate
  (`35911563598`). The execution layer independently built the exact wheel,
  checked ZIP and changed source bytes, installed it, and validated a generated
  manual-gate descriptor through the installed public CLI. Core tests cover
  identity, ordering, grant binding/replay/expiry, manual confirmation, active
  match probing, and old contracts.
- No target run of this new flow has occurred. This ADR does not adopt
  framework 0.2, authorize unattended startup, or change game-write authority.

## Supersedes

This decision supersedes ADR-0060 only for the provisional candidate pin and
the chosen post-PLAY workflow. Its fail-closed AX diagnosis remains historical
target evidence.
