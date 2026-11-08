# Tasks: A resource is a database, and the model knows no store

One phase = one commit, referencing (#487). After a phase only its own tests run; every new test is broken once on purpose. Nothing is committed, pushed or merged without the maintainer's instruction.

- [x] T001 [US1] Phase 1: remove the data source — `src/resources/base_data_source.py`, `src/resources/data_source_resolver.py`, `src/resources/in_memory/`, `src/resources/external_service/`, `graph/nodes/data_source_graph_node.py`, `graph/edges/resource_data_source_graph_edge.py`, `graph/validators/entity_data_source_validator.py`, the data-source half of `resource_domain_validator.py`, the `TDataSource_co` parameter of `BaseResource`, `BaseStorage`, `SqlStorage`, `PostgresStorage`, `SqlStorageWrapper` and the adapters' resources; the rules of #475 and #479; every import, test, example and page that names them; tests for each removal and for the freed `@depends`
- [x] T002 [US1] Phase 2: `@entity(description, domain=…)` — `intents/entity/entity_decorator.py`, `entity_intent.py`, `entity_intent_resolver.py`, `EntityGraphNode` and the relation validators read the entity's own domain; `resource=` is refused; the entity's `domain` edge comes from the entity; tests for a declared domain, a missing one and the removed argument
- [x] T003 [US1] Phase 3: `@entities` — `src/intents/entities/` decorator and resolver writing `_entities_info` on any resource kind; `@meta` refuses a domain on a resource and keeps it on an action; `ResourceGraphNode` stops building a domain edge; the demo's storages, the two gateways that hold entities and the test models declare their entities; the interim graph stays at protocol 1.8 and must still build between this phase and T006; tests for each refusal (a non-entity, a repeated class), the empty list and a two-resource entity
- [x] T004 [US3] Phase 4: `PostgresPool` — `resources/postgres/postgres_pool.py` from `PostgresDataSource`; `PostgresStorage` takes exactly one of `pool=` and `connection_params=`; both, neither and a non-PostgreSQL kind are refused; transactions stay inside the resource; tests for the three assembly modes and each refusal
- [x] T005 [US2] Phase 5: the check on return — `src/resources/entities/plan.py` and `walk.py`; `ResourceEntitiesError` in `exceptions/`; public methods wrapped at declaration, private ones untouched; async iterators checked per element; class methods, static methods and properties untouched; the plan kept per concrete class, attached at `NodeGraphCoordinator.build` and computed lazily without a machine; dictionary members and lifecycle states pass; a resource wrapper checked by the plan of the resource it wraps; tests for a listed entity, an unlisted one, an unloaded relation (passes) and a loaded one with an id-only partial entity (refused), a partial answer, a subclass, a subclass resource with its own `@entities`, a dictionary member and a lifecycle state, a nested action through `SqlStorageWrapper`, every container, an iterator, a resource without `@entities`, a test-bench substitute that is a resource and an entity-free answer; a `benchmark`-marked measurement of SC-004 and a loose upper-bound guard in the regular tests
- [x] T006 [US4] Phase 6: the graph at protocol 2.0 — `graph/edges/resource_entity_graph_edge.py`; `ResourceGraphNode` returns its `@entities` edges; `EntityGraphNode` keeps only its own `domain` edge; `graph_json_schema.json` and its docstring from gnomon `5d9dac89…`; `tests/scripts/test_schema_copies.py`; the coordinator's `resource_entity` check; graph tests
- [x] T007 [US5] Phase 7: the demo — merged databases in `packages/aoa-demo/src/aoa/demo/model/databases/` (`ShopDatabaseStorage` from store, support and inventory), `@entities` on every storage, `NotificationGateway` listing `RecipientDeviceSeenCoreEntity` and `CardNetworkGateway` listing `PaymentEventLogCoreEntity`, data source classes and type arguments gone; demo tests and the adapters' test models follow
- [x] T008 Phase 8: rebuild the graph files; raise the version of every changed level and its dependent minimums; refresh `uv.lock`
- [x] T009 Phase 9: take every locally runnable closing check to zero, including `graph-builder check`; retain phase evidence without unnecessary repetition; the PR CI closing run happens after T011 and PR authorization
- [x] T010 Phase 10: documentation — the model, the database and its entities, the check on return (every case and refusal), the three ways to reach a database, and the migration of every removed name; update every affected page; write and execute a script and matching notebook per case, recording exact outputs; old identifiers only in labelled migration explanations and historical material
- [x] T011 Phase 11: one plain-language changelog article describing the resulting capabilities and migration, written last

## Not included

Maxitor's logical and physical views (gnomon#67) and one transaction across two resources on one database. Writes are not bounded by domain: an action of any domain may write through any resource it uses.

## Traceability

| Requirement | Tasks |
|---|---|
| FR-001, FR-002 | T002, T003 |
| FR-003 | T003 |
| FR-004 | T002, T007 |
| FR-005, FR-008, FR-018 | T001 |
| FR-006, FR-007 | T004 |
| FR-009–FR-013 | T005 |
| FR-014 | T006 |
| FR-015 | T007 |
| FR-016 | T008 |
| FR-017 | T010, T011 |
| SC-001 | T001–T007, T010 |
| SC-002 | T001, T002 |
| SC-003 | each of T001–T007, with its adversarial break |
| SC-004 | T005 |
| SC-005 | T006–T008 |
| SC-006 | T009, then CI on the PR |

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011. The last three are the tail in order: the check run, the documentation, the changelog. No task authorizes a commit, push or PR. T001–T011 are marked complete and remain uncommitted.
