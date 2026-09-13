# Verification Matrix

This matrix records the strongest current evidence. Detailed procedures and raw
observations belong in `docs/EXPERIMENT_LOG.md`.

| Capability | Static | Unit/integration | Target Mac | Current status |
|---|---:|---:|---:|---|
| Environment and game-path discovery | Yes | Script checks | Yes | Confirmed |
| Custom mod activation on App Store build | Yes | N/A | Yes | Rejected on stock build |
| FireTuner read transport | Yes | Yes | Yes | Confirmed with security constraints |
| Persistent single-client watcher | Yes | Yes | Yes | Confirmed |
| Schema 2 rich state | Yes | Yes | Yes | Confirmed |
| Schema 3 score/era/city/unit fields | Yes | Yes | No | Live verification pending |
| Schema 3 met-major diplomacy | Yes | Yes | No | Live verification pending |
| Schema 3 science-victory progress | Yes | Yes | No | Live verification pending |
| `end_turn` | Stock API matched | Yes | Yes | Confirmed |
| `choose_research` | Stock UI matched | Yes | Yes | Confirmed |
| `set_city_production` | Stock UI matched | Yes | Yes | Confirmed |
| `skip_unit` | Stock behavior inspected | Yes | No | Live verification pending |
| Coordinate movement | No | No | No | Not implemented |
| Safety preflight/shutdown | Yes | Yes | Yes | Confirmed |
| Local IPC bounds and permissions | Yes | Yes | Indirectly | Confirmed offline |
| Command UUID/audit/idempotency | Yes | Yes | Partial | Confirmed offline; live core path observed |
| Knowledge canonical codec/index | Yes | Yes | N/A | Confirmed offline |
| Local SQLite knowledge import | Yes | Yes, including local real source | N/A | Confirmed offline |
| Civilization/trait/replacement knowledge | Source tables pending review | No | N/A | Not implemented |
| Ruleset resolver | No | No | N/A | Not implemented |
| Turn journal | Proposed contract | No | N/A | Not implemented |
| Expanded deterministic controller | Yes | Basic tests | Basic live path | In progress |

Update this file whenever an experiment changes the target-machine column or a
milestone adds/removes a capability row.
