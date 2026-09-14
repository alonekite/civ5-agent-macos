# Risk Register

Probability and impact are qualitative: low, medium, or high. A risk remains
open until evidence justifies closing it; mitigation does not erase the risk.

| ID | Risk | Probability | Impact | State | Mitigation / next evidence |
|---|---|---:|---:|---|---|
| R-001 | FireTuner listens on all IPv4 interfaces and accepts unauthenticated Lua | High when enabled | High | Controlled | Keep disabled by default; use recoverable live-session prepare/restore; require firewall plus explicit Civ V block rule; verify shutdown |
| R-002 | Civ V services only one reliable FireTuner client | High | High | Controlled | Watcher owns one persistent connection; local commands use private serialized IPC |
| R-003 | A candidate Lua action differs across Civ V builds or UI states | Medium | High | Open | Derive from bundled stock UI, whitelist, check capability predicates, and require bounded live verification |
| R-004 | DLC, Mod, or cache differences silently change knowledge semantics | Medium | High | Open | Version rulesets; record active packages and source hashes; reject family mismatch and unsupported inputs |
| R-005 | Knowledge export redistributes copyrighted prose or assets | Low | High | Controlled | Explicit gameplay-field allowlists; exclude Civilopedia text, quotes, images, audio, and game databases |
| R-006 | Leader AI flavor/personality fields enter the dataset | Medium | High | Open | Forbidden-field validation, importer allowlists, fixtures, and repository scans for every new entity family |
| R-007 | A write reports success without changing the intended state | Medium | High | Controlled | Store before/after snapshots; re-read exact target; timeout or ambiguity is an error |
| R-008 | Long-running project context exists only in a local chat | Medium | Medium | Controlled | Keep `PROJECT_STATE`, milestones, ADRs, module docs, development log, and Git history as durable handoff sources |
| R-009 | Documentation duplicates facts and becomes inconsistent | Medium | Medium | Open | Use `docs/INDEX.md` ownership rules; contracts own schemas, experiment log owns live evidence, state file owns current status |
| R-010 | A future journal grows without bounds or mixes different games | Medium | Medium | Planned | One-game identity, bounded records, retention/export policy, sequence and integrity checks in M5 |
| R-011 | Public API leaks FireTuner-specific behavior | Medium | Medium | Open | Stabilize implementation-neutral contracts in M7 and add adapters behind them |
| R-012 | Python version differences break CI after local success | Medium | Medium | Controlled | Keep Python 3.11 minimum; run GitHub Actions on 3.11 and 3.13; avoid newer-only syntax |

## Review rules

- Review this register when a milestone starts or completes.
- Any newly discovered high-impact risk blocks a release until it is mitigated,
  accepted explicitly, or proven inapplicable.
- Security-sensitive evidence belongs in a private report when publishing it
  would expose an exploitable technique or user-specific information.
- Link implementation work to the risk ID in commits or Issues when the primary
  purpose is risk reduction.
