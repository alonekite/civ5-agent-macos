# Risk Register

Probability and impact are qualitative: low, medium, or high. A risk remains
open until evidence justifies closing it; mitigation does not erase the risk.

| ID | Risk | Probability | Impact | State | Mitigation / next evidence |
|---|---|---:|---:|---|---|
| R-001 | FireTuner listens on all IPv4 interfaces and accepts unauthenticated Lua | High when enabled | High | Controlled | Keep disabled by default; use recoverable live-session prepare/restore; require firewall plus explicit Civ V block rule; verify shutdown |
| R-002 | Civ V services only one reliable FireTuner client | High | High | Controlled | Watcher owns one persistent connection; local commands use private serialized IPC |
| R-003 | A candidate Lua action differs across Civ V builds or UI states | Medium | High | Controlled for release scope | Four actions only; derive from bundled stock UI, validate arguments, check live capability, require exact read-back, and retain bounded target-build evidence; other builds remain unsupported until separately verified |
| R-004 | DLC, Mod, or cache differences silently change knowledge semantics | Medium | High | Controlled by provenance | Version rulesets; detect active DLC, record declared mods plus source size/hash, reject family/context mismatch, and retain generated bundles locally; a new source hash or declared context requires separate review |
| R-005 | Knowledge export redistributes copyrighted prose or assets | Low | High | Controlled | Explicit gameplay-field allowlists; exclude Civilopedia text, quotes, images, audio, and game databases |
| R-006 | Leader AI flavor/personality fields enter the dataset | Medium | High | Controlled by positive allowlists | ADR-0005, importer column/table allowlists, generic forbidden-name validation, adversarial fixtures, reviewed remainder inventory, and source/artifact scans apply to every extension |
| R-007 | A write reports success without changing the intended state | Medium | High | Controlled | Store before/after snapshots; re-read exact target; timeout or ambiguity is an error |
| R-008 | Long-running project context exists only in a local chat | Medium | Medium | Controlled | Keep `PROJECT_STATE`, milestones, ADRs, module docs, development log, and Git history as durable handoff sources |
| R-009 | Documentation duplicates facts and becomes inconsistent | Medium | Medium | Open | Use `docs/INDEX.md` ownership rules; contracts own schemas, experiment log owns live evidence, state file owns current status |
| R-010 | A journal grows without bounds, mixes identities, or leaks private match facts through export | Medium | Medium | Controlled by design | Explicit match/session bindings, bounded hash-chained records, operator-controlled retention, payload-gated replay, and redacted exclusive export under ADR-0017/0020/0021; live integrity/export/privacy evidence passed |
| R-011 | Public API leaks FireTuner-specific behavior | Medium | Medium | Controlled | M7 exposes implementation-neutral models/protocols through `civ5_agent.api`; the watcher-only adapter is explicit and raw FireTuner/IPC internals are excluded and contract-tested |
| R-012 | Python version differences break CI after local success | Medium | Medium | Controlled | Keep Python 3.11 minimum; run GitHub Actions on 3.11 and 3.13; avoid newer-only syntax |
| R-013 | Mutable snapshot fields are mistaken for a permanent save identity | Medium | High | Controlled by design | Use bridge-session identity for execution and explicit match identity for journals; prohibit automatic cross-session inference until target-verified evidence exists |
| R-014 | FireTuner truncates an oversized Lua program and leaves a submitted write outcome unclear | High above target limit | High | Controlled by design | Enforce a 1,000-byte pre-send maximum, keep every generated program below it, record/cache unknown outcomes without retry; compact marker delivery is target-verified |
| R-015 | A numeric end-turn blocker assumption disagrees with the target runtime | Medium without symbolic checks | Medium | Controlled | Compare the Lua enum symbol, expose the verified parsed value, inspect it independently of UI clickability, and require turn-advance postcondition; target guard is live-verified |
| R-016 | A downstream tactical consumer couples to private internals or moves planning policy into the core | Medium | High | Controlled by boundary | ADR-0031, the stable downstream capability profile, aggregate API, private-internal exclusions, and structured capability request review preserve one-way dependency and strategy-neutral core evolution |
| R-017 | Selection drift or deferred mission processing moves the wrong unit or produces unexpected movement | Medium | High | Mitigated; monitor in release/regression | ADR-0032 requires exact selection verification, a visible adjacent empty target, no special movement modes, fresh before/after state, bounded polling, UUID no-retry behavior, and a controlled target-machine test; C6 passed on the target Mac |
| R-018 | Selection-dependent worker legality or immediate completion makes the wrong build, wrong unit, or ambiguous result appear successful | Medium | High | Mitigated; monitor in release/regression | ADR-0033 and D2 freeze selection-free unit candidates, exact selected-unit stock dispatch, blank featureless land, ordinary non-consuming builds, lower-movement proof, separate active/completed postconditions, bounded Lua, and UUID no-retry behavior; D3 freezes WB-S01–A02 plus a single-write operator gate; C6 exposed and repaired action-table shape, integer `CanBuild` flags, lexical boundaries, string-key resolution, and loop-index dispatch defects, then passed the active-build branch with matching command/watcher/UI evidence, a private audit, no observed extra side effect, and exact host restoration |

## Review rules

- Review this register when a milestone starts or completes.
- Any newly discovered high-impact risk blocks a release until it is mitigated,
  accepted explicitly, or proven inapplicable.
- Security-sensitive evidence belongs in a private report when publishing it
  would expose an exploitable technique or user-specific information.
- Link implementation work to the risk ID in commits or Issues when the primary
  purpose is risk reduction.

## M8 high-impact disposition — 2026-09-16

R-003 is **controlled**, not closed. The stable release supports the target
Campaign Edition build and only the four actions listed in the command
contract. Each has argument validation, a game capability check, an exact
postcondition, offline failure coverage, and target-build live evidence. A
different build or a new action is outside that evidence and must pass the
command contract's full admission process before support is claimed.

R-004 is **controlled**, not closed. Knowledge bundles carry family, game
version, sorted DLC/mod declarations, canonical source labels, source size, and
SHA-256. Import reads an immutable/query-only database, detects active DLC and
family mismatch, detects a source changing during import, and resolution
requires exact ruleset context. Generated bundles are not shipped. Provenance
makes a different cache or declared context reviewable rather than silently
universal; the project does not claim semantic equivalence between hashes.

R-006 is **controlled**, not closed. ADR-0005 prohibits collection, modeling,
export, and shipment of AI behavior parameters. Importers select reviewed
gameplay columns and table families rather than copying unknown data; bundle
validation rejects flavor/personality-shaped fields; fixtures exercise those
rejections; the completed remainder inventory records excluded AI families;
and repository plus release-artifact review remains mandatory. Any new
knowledge family reopens field-level review under the same positive-allowlist
rule.

R-014 is **controlled by design**, not closed. The target-machine attempt
proved that oversized Lua can be truncated after submission. ADR-0028 now
rejects programs above 1,000 UTF-8 bytes before transport, tests every generated
program against that limit, and preserves any post-submission uncertainty as a
journal verification error plus a non-retryable watcher cache entry. The second
attempt proved compact marker delivery and a complete deterministic-failure
journal lifecycle. A later attempt proved the successful lifecycle and
automatic turn advancement through the same M6 path.

R-016 is **controlled by boundary**, not closed. ADR-0031 makes the tactical
project a one-way consumer of stable public contracts, assigns tactical content
and adapters outside the core, and requires strategy-neutral capability
requests for missing facts or actions. The 1.0 downstream profile lists both
available and absent capabilities, and public/private API tests plus release
review prevent private implementation details from becoming an accidental
integration contract. Every future public capability reopens compatibility and
ownership review.

These dispositions bound the first stable release; they do not erase the
underlying conditions or authorize additional game builds, actions, sources, or
knowledge fields.

## M9 high-impact disposition — 2026-09-17

R-017 is **mitigated and monitored** after the 2026-09-17 target-machine proof.
Source inspection shows that ordinary human movement depends on the UI head
selection and deferred network-message processing. ADR-0032 narrows the first
capability to one caller-selected adjacent, visible, empty, non-city
destination; requires exact selection confirmation plus identity-and-coordinate
read-back; and prohibits automatic retry after uncertainty. The bounded C6
experiment then rejected the source coordinate before submission and moved
exactly the authorized unit to the admitted target with lower movement and no
observed side effect. This closes the live-evidence blocker; the risk remains
monitored because selection and mission processing are runtime behavior. The
1.1.0 release candidate carries the mitigation into its compatibility profile.
