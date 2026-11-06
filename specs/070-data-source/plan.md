# Implementation Plan: A resource may work through a data source

**Branch**: `feature/issue-475-data-source` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

## Summary

A new primitive `BaseDataSource` (description only, no domain) and a generic resource hierarchy `BaseResource[D: BaseDataSource]` whose type argument names the data source. `PostgresDataSource` holds the pool; `PostgresResource` takes `connection_params=` or `data_source=`. The relation validator's boundary becomes "the data source, or the resource without one"; a new validator refuses an action using a resource of another domain. The graph gets `DataSource` nodes (application edge) and `resource_data_source` edges (protocol 1.7) and re-checks every rule before writing.

## Technical Context

Python 3.12 (CI 3.14); PEP 695 generics; pydantic; asyncpg; pytest. `src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Design

- `src/resources/base_data_source.py`: `BaseDataSource(ABC, MetaIntent)`, `@exclude_graph_model`; `__init_subclass__` checks the `DataSource` suffix.
- `src/intents/meta/meta_decorator.py`: `domain` optional in the signature; required for every host but a `BaseDataSource` subclass, refused on it.
- `src/resources/data_source_resolver.py`: `resolve_data_source(resource_cls)` walks `__orig_bases__` of the MRO and returns the one `BaseDataSource` subclass among type arguments, or `None`; `check_data_source_arguments(cls)` refuses an argument outside its parameter's bound and two different data sources. `BaseResource.__init_subclass__` calls the check; `BaseResource._require_data_source(value)` is the run-time check.
- `BaseResource[D]`, `BaseStorage[D]`, `BaseGateway[D]`, `BaseController[D]`, `SqlResource[D]`, `PostgresResource[D: PostgresDataSource]`, `WrapperSqlResource[D]`.
- `src/resources/postgres/postgres_data_source.py`: `PostgresDataSource` — `dsn`/options or a ready `pool`; `open/close`, `__aenter__/__aexit__`, `acquire()/release(conn)`, `acquire_timeout`.
- Graph: `DataSourceGraphNode` (+ inspector in the factory), `ResourceDataSourceGraphEdge` on `ResourceGraphNode`; coordinator writes `"1.7"` and re-checks the rules of FR-008; `graph_json_schema.json` = gnomon 1.7.
- Validators: `entity_resource_validator.py` boundary; `resource_domain_validator.py` for FR-006, called in `build`.

## Phases (one commit each, as in issue #475)

1. `BaseDataSource`, `@meta` without a domain for it, `DataSourceGraphNode` with its `application` edge.
2. The generic resource hierarchy, `resource_data_source` edge, bound and uniqueness refusals, the run-time check.
3. `PostgresDataSource`, `PostgresResource` with `connection_params=` / `data_source=`, fake data source.
4. Relations and lifecycle states follow the boundary; the graph build re-checks every rule.
5. An action uses only resources of its domain.
6. The demo: identity route, `CheckoutSubmitAction`.
7. Examples and tests that used `pool=`.
8. Protocol copy 1.7, `maxitor>=3.18.0`, the CI action tag, graph files, versions.
9. The closing check run.
10. Documentation.
11. Changelog.
