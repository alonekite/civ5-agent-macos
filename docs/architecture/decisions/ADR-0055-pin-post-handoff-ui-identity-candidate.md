# ADR-0055: Pin post-handoff UI identity candidate

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-22

## Context

The operator-present run of the ADR-0053 candidate delivered the launcher
`PLAY` action and visibly reached the game's `Click to Continue` screen. The
process kept its PID and changed to the declared game executable, but AppKit
continued reporting the launcher executable. The framework required both
sources to report the new executable, so handoff timed out before the second
checkpoint or watcher. After the operator exited the game, framework recovery
remained incomplete because of the pending handoff.

The first framework repair accepted an exact successor from the process probe
with a stale AppKit executable URL. Independent execution-core review found
that the next UI step still required the two paths to match. The second repair
passes the tracked handoff identity through subsequent UI and process-start
checks.

## Decision

Pin the provisional SessionSpec v2 candidate to framework commit
`a722aac6dcd7854d5715bdf994115de6ed5c792d` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`cca1d5b674864e261b9252b67808749e954014c38a8d79b7b2be78541ee357d3`.

During the declared handoff, require the exact original PID and process
creation time, the declared successor executable from the process probe, and
one AppKit candidate with the unchanged bundle identifier and resolved bundle
path. AppKit may name only the old launcher or declared successor executable.
The tracked successor identity is carried into the next UI step and watcher
start. Recheck the process identity before UI delivery and child start. No
changed PID, creation time, third executable, or ambiguous candidate is
accepted; no UI action is retried after the delivery boundary.

Recovery of an interrupted handoff may close only after two independent fresh
process probes find the tracked PID absent. A reused PID remains unresolved.
This candidate remains pre-release and requires a fresh operator-present target
run before any framework 0.2 adoption.

## Evidence and limits

- The exact wheel has 20 valid members and RECORD hashes; 15 Python modules
  match the pinned source byte for byte. The wheel privacy scan passed.
- Framework source tests passed 130/130 on the host with eight documented
  environment skips. An isolated wheel install validated SessionSpec v2,
  including an existing core-generated private descriptor. GitHub Quality
  gate `35771791299` passed.
- Offline tests cover stale AppKit handoff, the next UI action, third-path
  refusal, delivery-boundary process drift, watcher prestart drift, graceful
  stop, and absent-target recovery. None proves the target's second click or
  watcher startup; the prior live run ended before those steps.

## Supersedes

This decision supersedes ADR-0053 only for the exact provisional candidate
commit and wheel pin and the handoff continuation and recovery behavior. Its
AX frontmost, regular-application, checkpoint, privacy, deadline, and
no-retry requirements remain in force. The adopted v0.1.0 framework path is
unchanged.
