# Runtime Research Facts Verification Specification

Status: Complete in immutable release `v1.3.0`

Milestone: M11

## Evidence boundary

Offline tests establish parsing, validation, compatibility, bounds, and
determinism. Inspection of bundled game source establishes candidate binding
shapes only. Neither is target-machine proof. The experiment log and live
verification ledger alone may record target evidence.

KnowledgeBundle compatibility is a downstream adapter result. Its failure must
not mutate or clear authoritative schema 8 runtime facts. It only blocks an
exact-supported forecast and forecast-dependent automatic intent eligibility.

The first bounded target attempt established schema 8 framing and read purity
but exposed the incorrect provisional `CvPlayer` owner for times-100 progress.
ADR-0037 corrects the owner to `CvTeamTechs`; that attempt is diagnostic only,
and the target matrix remains pending until rerun on the corrected code.

The corrected target attempt established repeated-read stability, UI agreement,
the exact `CvTeamTechs` progress, and a qualifying positive-overflow
precondition. The manual interturn then exposed acknowledgement-before-output
FireTuner framing that left the watcher connection desynchronized. ADR-0042
repairs that transport boundary; post-interturn overflow and selection behavior
remained pending until a fresh exact-commit run.

The first ADR-0042 rerun observed positive whole-point overflow, preserved it
through selection, and observed its later application. The first interturn kept
the original connection, but the second interturn rotated the bridge session.
ADR-0043 repairs the remaining assumption that only one output frame follows an
early acknowledgement. The observations are diagnostic across the rotation and
did not close the same-session C4 gate.

The exact `95ef3df` ADR-0043 rerun completed that gate. Repeated reads were
stable and side-effect-free; the same bridge session covered the pre-completion
window, positive whole-point overflow, selection without consumption, and the
following interturn where exact progress included the overflow. The audit was
mode `600` with zero records and guarded shutdown restored the exact baseline.
The direct pre-interturn surplus exceeded the reported whole-point overflow by
`3.19` points. Science changed from `447.21` in the pre-completion window to
`444.55` afterward, which is a plausible cross-turn production explanation but
not a claimed overflow formula.

## Offline matrix

| ID | Case | Required result |
|---|---|---|
| RF-S01 | ordinary action window, zero overflow | supported exact shape; zero preserved |
| RF-S02 | ordinary action window, positive overflow | supported exact whole-point value |
| RF-S03 | current research present/absent | nullable current and candidate equality remain coherent |
| RF-S04 | effective candidate costs and turns | exact runtime values; no core recomputation |
| RF-S05 | free technology | unsupported with `free_technology_mode`; no partial facts |
| RF-S06 | technology steal | unsupported with `technology_steal_mode`; no partial facts |
| RF-S07 | inactive or processing messages | unsupported with `outside_action_window` |
| RF-S08 | missing runtime method | unavailable with `runtime_api_binding_unavailable` |
| RF-S09 | malformed, negative, duplicate, or misordered fact | whole state rejected |
| RF-S10 | mismatched part turn/player | whole state rejected |
| RF-S11 | runtime context dimensions | exact per-dimension status/value/source rules |
| RF-S12 | ruleset fingerprint | always unsupported/null in schema 8 |
| RF-S13 | schemas 2–7 | accepted unchanged; new capabilities absent |
| RF-S14 | deterministic serialization and state digest | identical inputs produce identical bytes/digest |
| RF-S15 | generated programs and response | remain inside existing transport limits |
| RF-S16 | KnowledgeBundle binding missing/conflicting | runtime facts remain supported; downstream exact/automatic forecast path fails closed |
| RF-S17 | separately approved core-only manual research intent | may use live candidates without exact-forecast claim; unchanged core verification still required |

## Target matrix

1. Schema 8 watcher output is complete and read-only: no selection, popup,
   unit action, research change, or turn advance.
2. UI/current research, effective costs, progress, science, and turns-left agree
   with the runtime facts at the captured action window.
3. A controlled case with exact pre-interturn
   `0 < remaining_times100` and
   `remaining_times100 + 100 <= science_per_turn_times100` reports completion
   and a positive whole-point representation of the computed exact surplus in
   the next action window. The 20-remaining/22-produced case is illustrative,
   not a required literal fixture; fractional surplus must be preserved in
   evidence rather than rounded to force agreement.
4. Selecting a new technology does not immediately consume the overflow; the
   next interturn applies it. This is observation, not a new core write path.
5. The private audit remains unchanged by read-only collection, and guarded
   shutdown restores the exact FireTuner/firewall baseline.
6. The controlled sequence either retains one bridge-session identity or
   explicitly fails the continuity gate. A framing recovery may rotate the
   session for later reads, but evidence must not infer match continuity from
   mutable snapshot fields across that boundary.

If a suitable controlled save is unavailable or any exact runtime binding fails,
the affected target gate remains pending. Approximation is not evidence.
The operator procedure and sanitized evidence template are in
[M11 runtime research facts live test](RESEARCH_RUNTIME_FACTS_LIVE_TEST.md).
