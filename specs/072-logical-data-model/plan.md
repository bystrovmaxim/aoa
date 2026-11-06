# Implementation Plan: The logical data model

**Branch**: `feature/issue-479-logical-data-model` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

`src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Design

- **Model build** — `graph/validators/entity_resource_validator.py` loses the boundary rules and gains FR-002: for each `@entity` host, its resource names a data source, or `EntityResourceError` names the resource and the entities it stores. It is still called per entity by `EntityGraphNode` and once by the coordinator.
- **One resource per domain and data source** — `graph/validators/resource_domain_validator.py` gains a pass over every loaded resource class with a domain and a data source (`ResourceDataSourceError`, a new exception beside `EntityResourceError`), called by the coordinator.
- **Graph build** — `NodeGraphCoordinator._validate_entity_resource_edges` loses the boundary re-check; it keeps one `entity_resource` edge per entity, and gains: a resource with an incoming `entity_resource` edge has exactly one `resource_data_source` edge; no two resources with one `domain` edge share a data source.
- **Data sources** — `resources/in_memory/in_memory_data_source.py` (`InMemoryDataSource`: a process-local store the resources of it share, `open`/`close`, `async with`) and `resources/external_service/external_service_data_source.py` (`ExternalServiceDataSource`: `base_url`, `credentials`, `client`); both exported from `aoa.action_machine.resources`.
- **PostgreSQL** — `PostgresResource.__init__(*, data_source, rollup=False)`; `open` takes from the data source only.
- **Tests and examples** — every resource class an `@entity` names gets its own data source: in tests and examples an `InMemoryDataSource` subclass declared beside it, named after it; adapters' test models likewise. A mechanical pass, checked by the model build of each test module.
- **The demo** — each of its 16 resources without a data source gets the data source of its kind; `MessagingDeadLetterStore` merges into `OutboxPrimaryDatabase`.
- **Protocol 1.8** — `graph/graph_json_schema.json` is gnomon's `graph/1.8.json`; the coordinator writes `1.8`; `maxitor[all]` from git at the pinned commit (`[tool.uv.sources]`), CI's action `@<commit>`.

## Constitution Check

One phase = one commit; adversarial verification; the tail (check run, documentation, changelog); every changed level raises its version.
