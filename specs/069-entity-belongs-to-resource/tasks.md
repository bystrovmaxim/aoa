# Tasks: An entity belongs to one resource, and its relations stay inside it

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/entity-decorator.md](contracts/entity-decorator.md)

One phase = one commit, referencing (#469). After each phase only that phase's test files run; CI runs the closing check run. `src` below means `packages/aoa-action-machine/src/aoa/action_machine`, `tests` means `packages/aoa-action-machine/tests/action_machine`.

## Phase 1: `@entity(resource=...)` — US1 (P1)

Goal: an entity names its resource; its domain is read from it (2.1–2.3, 2.5, 2.6).

- [ ] T001 [US1] Write `tests/intents/entity/test_entity_resource_decorator.py`: every declaration row of contracts/entity-decorator.md word for word (2.1 no resource; 2.2 `domain=` → `TypeError`; 2.3 a domain, an action, a non-class, `BaseStorage`, a resource without `@meta`; 2.5 a tuple of two; 2.6 accepted, domain `StoreDomain`; one storage, one gateway, one controller accepted; a subclass without `@entity` inherits the resource).
- [ ] T002 [US1] In `src/intents/entity/entity_decorator.py`: signature `entity(description, *, resource)`; `_entity_info = {"description", "resource"}`; the resource checks inside `decorator(cls)` so the messages name the entity (research R2); module docstring, `EXAMPLE`, AI-CORE block updated.
- [ ] T003 [US1] In `src/intents/entity/entity_intent_resolver.py`: `resolve_resource_type(host)`; `resolve_domain_type(host)` reads the resource's `@meta` domain; `resolve_domain_optional` removed with its callers; `MissingEntityInfoError` key `resource`.
- [ ] T004 [US1] In `src/graph/edges/domain_graph_edge.py`: `from_entity_declared_host` docstring says the domain comes from the resource.
- [ ] T005 [US1] Run T001; adversarial: drop the excluded-class check → the `BaseStorage` case fails alone; read the domain from `_entity_info` → the 2.6 case fails alone; restore. Commit.

## Phase 2: the model build refuses links across resources — US2 (P1)

Goal: case 2.4 for every link kind and the shared state type.

- [ ] T006 [US2] Create `src/exceptions/entity_resource_error.py` (`EntityResourceError`), export it from `src/exceptions/__init__.py`.
- [ ] T007 [US2] Write `tests/graph/test_entity_resource_validator.py`: association, aggregation, composition (owner side and the other side), inverse side, specialization, generalization, dictionary field, shared state type across two resources — each refused with the contract's message; a self-relation, a same-resource model and a state type shared inside one resource accepted.
- [ ] T008 [US2] Create `src/graph/validators/entity_resource_validator.py` with `validate_entity_resources(entities=None)` (research R3, R6); call it in `src/graph/core/node_graph_coordinator.py` `build` right after `validate_entity_fields()`; add `EntityResourceError` to `build`'s `Raises`.
- [ ] T009 [US2] Run T007; adversarial: skip the lifecycle grouping → the state-type case fails alone; skip generalization targets → the generalization case fails alone; restore. Commit.

## Phase 3: the graph — US3 (P2)

Goal: `entity_resource` edge, domain from the resource, protocol 1.6, graph-build refusals (2.5).

- [ ] T010 [US3] Copy `/Users/bystrovmaxim/PythonDev/gnomon/packages/open-gnomon-protocol/graph/1.6.json` (gnomon `main` `2d6159df`) over `src/graph/graph_json_schema.json` byte for byte; `src/graph/graph_json_schema.py` docstring → 1.6; `tests/scripts/test_schema_copies.py` → 1.6's `$id` and SHA-256.
- [ ] T011 [US3] Create `src/graph/edges/entity_resource_graph_edge.py` (`EntityResourceGraphEdge(AggregationGraphEdge)`, `edge_name="entity_resource"`, `is_dag=True`, `properties` `{}`, default id); export from `src/graph/edges/__init__.py` if edges are exported there.
- [ ] T012 [US3] In `src/graph/nodes/entity_graph_node.py`: `resource` field, built in `__init__`, first in `get_all_edges` after `domain`; docstrings.
- [ ] T013 [US3] In `src/graph/core/node_graph_coordinator.py`: `_validate_entity_resource_edges(nodes)` after `_single_pass_validate_and_wire` (research R4); `to_json` writes `"1.6"`; docstrings.
- [ ] T014 [US3] Write `tests/graph/test_entity_resource_graph.py`: the edge row; the domain edge's target is the resource's domain; a built graph validates against `GRAPH_JSON_SCHEMA`; `schema_version` `1.6`; zero and two edges refused; on hand-built nodes past the class pass, each of `entity_relation`, `entity_reference`, `entity_specialization`, `parent_entity` and a state group across resources refused (SC-005). Move every test asserting `"1.5"` to `"1.6"`.
- [ ] T015 [US3] Run T014, the moved tests and `tests/scripts/test_schema_copies.py`; adversarial: emit the edge twice → the count case fails alone; drop the node check → the hand-built case fails alone; restore. Commit.

## Phase 4: the demo — US4 (P2)

Goal: every demo entity stored by one resource, none related across resources (research R8).

- [ ] T016 [US4] Create one storage resource per demo domain with no resource (13 domains) under `packages/aoa-demo/src/aoa/demo/model/<domain>/resources/`.
- [ ] T017 [US4] Move `CurrencyEnumEntity` into `packages/aoa-demo/src/aoa/demo/model/billing/entities/`, stored by `BillingWarehouse`; remove `DictionariesDomain` and its package; update imports.
- [ ] T018 [US4] Remove the 23 other cross-domain associations (both sides where an inverse exists).
- [ ] T019 [US4] Rewrite every demo `@entity` to `resource=`; spread Store, Billing, Messaging, Catalog by meaning (at least one gateway and one cache own entities); remove or move any relation that then crosses resources; split `CatalogDenseLifecycle` per resource.
- [ ] T020 [US4] Update `packages/aoa-demo/tests` (the dictionary graph test, counts); run them; build the graph and check SC-002. Commit with the list of what moved.

## Phase 5: examples and tests — US4 (P2)

- [ ] T021 [US4] Script in the scratchpad (research R7) over `packages/aoa-action-machine/tests`, `packages/aoa-{fastapi-adapter,mcp-adapter,langgraph,ocel,otel}/tests`, `examples/`; then fix by hand what it cannot (relations that cross, domains imported from elsewhere, tests that asserted the old `domain` behaviour).
- [ ] T022 [US4] Run the test files and examples the phase changed. Commit.

## Phase 6: graph files and versions

- [ ] T023 Rebuild `packages/aoa-demo/graph.json` (`graph-builder write`, or the build command of `graph-builder.toml`); raise each changed level's `version.toml` as `version-gate` requires (research R9). Commit.

## Phase 7: the closing check run

- [ ] T024 Take every check this machine can run to zero (`bash scripts/run_checks_with_log.sh`); fix every remark. Commit.

## Phase 8: documentation — US5 (P3)

- [ ] T025 [US5] Tutorial steps 21–25 (`docs/tutorials/step-2{1..5}-*.md`) and every how-to page declaring entities: declarations name a resource; new cases (2.1, 2.3, 2.4, 2.5 graph, 2.6) as scripts in `examples/step_22_entity/` and `examples/step_24_relations/` with notebooks beside them, each run and its output pasted.
- [ ] T026 [US5] `docs/reference/intents-and-invariants.md` ("Mandatory domain", "Entity relations"); `README.md`. Russian drafts beside every page written. Commit.

## Phase 9: changelog

- [ ] T027 One article in `docs/CHANGELOG.md` and its `.ru_draft.md`. Commit.

## Dependencies

Phase 1 → 2 → 3 (the validator and the edge read the resource) → 4, 5 (in either order; both need 1–3) → 6 → 7 → 8 → 9. No task inside a phase is parallel: each touches files the next reads.

## Implementation strategy

MVP is phases 1–3 (the rule and the graph); phases 4–5 make the repository build again; 6–9 are the tail the constitution requires. The pull request opens only after phase 9, then merges once every check of CI has passed.
