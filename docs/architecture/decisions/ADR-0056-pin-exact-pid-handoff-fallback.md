# ADR-0056: Pin exact-PID AppKit handoff fallback

Status: Accepted for provisional SessionSpec v2 compatibility

Date: 2026-09-23

## Context

Two operator-present runs of the ADR-0055 candidate delivered the one-use
launcher `PLAY` action but never reached the second checkpoint. The later run
used a closed-set timeout diagnostic and reported `candidate_absent`: after
the declared same-process executable transition, the process probe observed
the expected game executable while AppKit bundle enumeration returned no
candidate in the framework process. A separate process could observe the game
in AppKit, but that does not establish the framework's in-process observation.
The watcher did not start, and the framework required recovery. The operator
exited the game and host hardening was independently reverified.

## Decision

Pin the provisional SessionSpec v2 candidate to framework commit
`d531450ecebc3326d3b314e7a6b438678f29aa28` and wheel
`local_app_test_automation-0.2.0.dev0-py3-none-any.whl` with SHA-256
`738c561c0f1d651c0ddba6a12275e44264b1eacc2f5fef1b641266133fb66157`.

Only when AppKit bundle enumeration is empty during an explicitly declared
same-process executable handoff may the framework query AppKit by the original
tracked PID. The result remains subject to the original PID, process creation
time, bundle identifier and resolved path, AppKit executable allowlist (old
launcher or declared successor), and process-probe exact successor checks.
Initial launch, later UI delivery, and cleanup do not use this fallback.
Ambiguity, changed identity, or a third executable fails closed. The
post-request, step-specific one-use operator authorization remains mandatory.

## Evidence and limits

- The fixed wheel digest was independently checked, its application module
  matches the pinned source byte for byte, and an isolated Python 3.12 install
  accepted the execution core's generated SessionSpec v2 through the public
  validation CLI.
- Framework host tests passed 136 cases with eight host-environment skips; the
  framework task reports all four macOS CI cells and wheel/clean-install gate
  passed in run `35786865141`.
- At pinning time, no target run had established the second click or watcher
  startup with this candidate. The exact-PID query addressed the observed
  absent-candidate class but was not itself proof of target success. Later
  target evidence belongs in the experiment log and verification matrix.

## Supersedes

This decision supersedes ADR-0055 only for the provisional candidate commit
and wheel pin and the declared-handoff candidate lookup. All other identity,
authorization, safety, privacy, and no-retry requirements remain in force.
The adopted v0.1.0 framework path is unchanged.
