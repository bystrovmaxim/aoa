# Tasks: A resource may work through a data source

**Input**: [spec.md](spec.md), [plan.md](plan.md)

One phase = one commit, referencing (#475). After each phase only that phase's test files run. Every new test is broken once on purpose. `src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Phase 1: The primitive

- [x] T001 `src/resources/base_data_source.py`; `@meta` without a domain for a data source, refused with one; suffix check; tests `tests/resources/test_base_data_source.py`
- [x] T002 `DataSourceGraphNode` + inspector registered in `node_graph_coordinator_factory.py`; tests of the node row and its `application` edge

## Phase 2: Resources name their data source

- [ ] T003 `resolve_data_source`, the bound and uniqueness checks in `BaseResource.__init_subclass__`; the hierarchy made generic; `_require_data_source`
- [ ] T004 `ResourceDataSourceGraphEdge` on `ResourceGraphNode`; tests

## Phase 3: PostgresDataSource

- [ ] T005 `PostgresDataSource`, `PostgresResource(connection_params= | data_source=)`; `pool=` removed; tests with a fake pool

## Phase 4: The boundary of relations

- [ ] T006 boundary in `entity_resource_validator.py`; coordinator re-check of FR-008; tests

## Phase 5: Resources of the action's domain

- [ ] T007 `resource_domain_validator.py`; tests

## Phase 6: The demo

- [ ] T008 `IdentityDataSource`, identity route; `CheckoutSubmitAction` uses resources of `StoreDomain` only

## Phase 7: Examples and tests

- [ ] T009 every `pool=` in examples, tests and adapters' tests

## Phase 8: Protocol, dependencies, graphs, versions

- [ ] T010 schema copy 1.7, `maxitor>=3.18.0`, CI action tag, `graph-builder write`, versions

## Phase 9: The closing check run

- [ ] T011 CI on the pull request taken to zero

## Phase 10: Documentation

- [ ] T012 architectural constitution page, tutorial steps on the resource and relations, intents-and-invariants

## Phase 11: Changelog

- [ ] T013 one article
