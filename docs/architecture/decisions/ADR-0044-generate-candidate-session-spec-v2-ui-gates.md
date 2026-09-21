# ADR-0044: Generate candidate SessionSpec v2 UI gates at the core boundary

Status: Accepted

Date: 2026-09-21

## Context

The independent `local-app-test-automation` repository added SessionSpec v2 UI
steps on exact development commit `d7784a7`. The target Civ V build has two
pre-watcher UI gates: an Aspyr launcher `PLAY` button and an in-game
`Click to Continue` canvas. Putting a Civ-specific profile into the generic
framework would reverse ownership.

Target observation established one application bundle identity and window
title for both phases. The launcher exposes exactly one `AXButton` titled
`PLAY`. After that action, the game canvas exposes no actionable accessibility
element. The rendered continue prompt moves when resolution or letterboxing
changes, so one screenshot-derived coordinate is not universally stable.

## Decision

Keep the published v0.1.0/SessionSpec v1 integration unchanged. Add a separate,
provisional core CLI path that emits candidate SessionSpec v2 JSON with exactly
two ordered UI steps:

1. `accessibility_press` on the exact bundle, window, `AXButton`, and `PLAY`
   title verified on the target;
2. `window_relative_click` on the same bundle/window using normalized
   coordinates explicitly supplied and reviewed by the composition root.

Both steps use independent expiring human checkpoints. The framework launches
the application, completes the steps sequentially, and only then starts the
existing server-enforced read-only watcher process. The core validates exact
application identity, finite open-interval coordinates, time bounds, absolute
process paths, empty environment inheritance, and disabled raw-output
retention. It never imports the framework or adds it as a dependency.

The v2 candidate is pinned for compatibility testing by exact framework commit,
not adopted as a release. Formal adoption requires an immutable framework
release, artifact digest review, caller validation, target evidence, and a new
or superseding compatibility decision.

## Consequences

- Civ-specific selectors and coordinate calibration remain in this repository.
- The generic framework remains domain-neutral and independently installable.
- No UI action occurs without a fresh operator checkpoint response.
- Accessibility permission must be granted manually to the framework host;
  neither repository changes macOS privacy settings.
- The framework does not activate the window, capture it, infer that the
  continue screen is ready, or retry a delivered input. The operator must bring
  the exact window forward and visually verify both checkpoints.
- A resolution or window-layout change invalidates prior coordinate review and
  requires recalibration before authorization.

## Alternatives considered

- Hard-code the continue text coordinate from one screenshot: rejected because
  target observations showed resolution-dependent placement.
- Downgrade the launcher to a coordinate click: rejected because a unique AX
  button exists and is the safer exact selector.
- Put a Civ profile in the framework: rejected because it would make the
  generic repository own product-specific behavior.
- Start the watcher before UI gates: rejected because FireTuner readiness is not
  established until the game passes its launcher/startup sequence.
