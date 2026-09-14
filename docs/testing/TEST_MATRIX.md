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
| Knowledge schema 1 compatibility / schema 2 reference attributes | ADR and contract reviewed | Round-trip, canonical shape, invalid schema, and non-finite attribute tests | N/A | Implemented offline |
| Knowledge schema 3 typed reference context | ADR and contract reviewed | Round-trip, legacy-shape, identity, ordering, and missing-entity tests | N/A | Implemented offline |
| Local SQLite knowledge import | Yes | Yes, including local real source | N/A | Confirmed offline |
| Civilization/trait/replacement knowledge | Real merged database imported; counts and class consistency checked | Synthetic schema, allowlist, relation, duplicate-slot, and mismatch tests | N/A | Implemented offline |
| Religion/belief/specialist knowledge | Real merged database imported; counts and canonical repeatability checked | Synthetic scalar, reference, and invalid-number tests | N/A | Implemented offline |
| Terrain/feature/improvement/route/yield/build knowledge | Real merged database imported; counts, references, and canonical repeatability checked | Synthetic allowlist, optional scalar, validity, unlock, and creation relations | N/A | Core slice implemented offline |
| Binary quantity-bearing knowledge | Real merged database imported twice with 576 attributed binary references across 82 single-value families, four multi-attribute promotion families, and project thresholds with equal hashes | Synthetic coverage of every configured table plus negative, invalid-integer/boolean, duplicate-reference, threshold, and fake-feature cases | N/A | Implemented offline |
| Single-context effects | Real merged database imported twice with 212 contextual references, including technology-conditioned promotion passability, and equal hashes | Synthetic coverage of every configured table, same-edge/different-context identity, plain and attributed context, and invalid-integer cases | N/A | Implemented offline |
| Expanded quantified rules | Real merged database imported twice with 157 new binary and 15 new contextual quantity references and equal hashes | Synthetic schema, integer, target-kind, and context-kind coverage through declarative fixtures | N/A | Implemented offline |
| Improvement resources / enhanced building yields | Real merged database imported twice with 68 multi-attribute resource rules, one technology-conditioned yield, and equal hashes | Synthetic attributes and derived context plus missing-technology rejection | N/A | Implemented offline |
| Hurry-method knowledge | Real merged database imported twice with 2 hurry entities, 2 cost-modifier references, and equal hashes | Synthetic scalar, policy-gate, building-modifier, and policy-modifier coverage | N/A | Implemented offline |
| Promotion environment modifiers | Real merged database imported twice with 33 domain/feature/terrain/unit-class modifier references and one technology-conditioned passability reference | Synthetic multi-attribute, optional-value, boolean-validation, and typed-context coverage | N/A | Implemented offline |
| Expanded plain knowledge relations | Real merged database imported twice with 253 links across 14 table families and equal hashes | Synthetic schema and typed source/target coverage for every configured family | N/A | Implemented offline |
| Project/process/victory knowledge | Real merged database imported twice with 16 entities and 19 outgoing project/process references and equal hashes | Synthetic scalar, direct-reference, quantified prerequisite/conversion, threshold, and invalid-threshold cases | N/A | Implemented offline |
| Unit-combat knowledge | Real merged database imported twice with 14 entities, 444 unit-combat targets, 37 contextual promotion grants, and equal hashes | Synthetic entity, membership, applicability, quantity-table, and contextual-table coverage | N/A | Implemented offline |
| Unit domain/special classifications | Real merged database imported twice with 5 domains, 4 special-unit categories, 148 domain links, 22 special links, and equal hashes | Synthetic entities, scalar flags, and typed-link coverage | N/A | Implemented offline |
| Typed unit identifier relations | Real merged database imported twice with 323 links across 11 allowlisted identifier columns and equal hashes | Synthetic coverage of every mapping plus bundle-level target validation | N/A | Implemented offline |
| Ruleset resolver | No | No | N/A | Not implemented |
| Turn journal | Proposed contract | No | N/A | Not implemented |
| Expanded deterministic controller | Yes | Basic tests | Basic live path | In progress |

Update this file whenever an experiment changes the target-machine column or a
milestone adds/removes a capability row.
