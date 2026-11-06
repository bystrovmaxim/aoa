# Feature Specification: The logical data model — relations across stores, a data source required, one resource per domain and data source

**Feature Branch**: `feature/issue-479-logical-data-model`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #479, "Logical data model 2/4". Protocol 1.8 (bystrovmaxim/gnomon#59) states the rules; this spec makes AOA keep them.

## What this is

The model has two axes. The logical one says what things are: domains, entities, relations. The physical one says where they live: a resource and its data source. A relation is a fact of the logical model: it promises no foreign key, no join and no shared transaction, so AOA allows it between any two entities. In exchange every stored entity gets a physical place: its resource names a data source, and a domain reaches a data source through one resource.

## Clarifications

### Session 2026-11-06

- Q: Which links lose the boundary check? → A: All the links #475 held inside one boundary: a relation and its inverse side, a dictionary field, a specialization, a generalization and a lifecycle state type shared by several entities — at model build and at graph build.
- Q: Which resources must name a data source? → A: Every resource class an `@entity(resource=...)` names. A resource that stores no entity (a gateway that only calls out) may name none.
- Q: Where do connection parameters live? → A: Only in a data source. `PostgresResource(connection_params=...)` is gone; a PostgreSQL resource takes only `data_source=`.
- Q: Which data sources does AOA give? → A: `PostgresDataSource` (as today), `InMemoryDataSource` for a store that lives in the process, and `ExternalServiceDataSource` for an external service: its base address, credentials and client.
- Q: What does "one resource per domain and data source" compare? → A: The domain of each resource class (`@meta(domain=...)`) and the data source it names. Two resource classes with one domain and one data source are refused, naming the domain, the data source and both resources. Resources of different domains may share a data source.
- Q: When are the rules checked? → A: When the model is built, and again when the graph is built (the graph at protocol 1.8), so a graph AOA writes always keeps them.
- Q: Does the demo follow the rules in this change? → A: Yes, as far as the rules require: every demo resource that stores an entity names a data source, and `MessagingDomain` reaches `MessagingDataSource` through one resource; otherwise the demo could not be built and this change could not pass its checks. What the demo shows on top — a relation across data sources, a service shared by two domains, the demo's pages — is bystrovmaxim/aoa#480.
- Q: Which Maxitor checks the graphs? → A: `maxitor` from bystrovmaxim/gnomon at commit `9ecc198834cc7df462a729f751ddf4870874cc35` (Maxitor 3.22.0, which reads protocol 1.8), pinned by that commit in the dependencies and in CI's `graph-builder` action, with no PyPI release.

## User Scenarios & Testing

### User Story 1 - Relate entities of any stores (Priority: P1)

A developer declares `InvoiceCoreEntity` on `BillingResource` (`BillingDataSource`) with an association to `SalesOrderCoreEntity` on `OrdersResource` (`ShopDataSource`). The model builds; the graph has the `entity_relation` edge.

**Acceptance Scenarios**:

1. **Given** a relation, an inverse side, a dictionary field, a specialization, a generalization or a shared lifecycle state type across two data sources, **When** the model and the graph are built, **Then** both succeed.

### User Story 2 - Every stored entity has a physical place (Priority: P1)

**Acceptance Scenarios**:

1. **Given** an entity whose resource names no data source, **When** the model is built, **Then** it is refused, naming the resource and the entities it stores.
2. **Given** `PostgresResource(connection_params=...)`, **When** it is called, **Then** it is refused: a PostgreSQL resource takes only `data_source=`.
3. **Given** a resource on `InMemoryDataSource` or on `ExternalServiceDataSource`, **When** the model is built, **Then** it succeeds, and the graph has its `resource_data_source` edge.

### User Story 3 - A domain reaches a data source through one resource (Priority: P1)

**Acceptance Scenarios**:

1. **Given** two resources of `SalesDomain` naming `ShopDataSource`, **When** the model is built, **Then** it is refused: `SalesDomain reaches ShopDataSource through OrdersResource and CartResource: a domain reaches one data source through one resource.`
2. **Given** two resources of two domains naming one data source, **When** the model is built, **Then** it succeeds.

### Edge Cases

- A resource that stores no entity and names no data source is allowed.
- A data source is still never a dependency of an action.
- A graph written by AOA declares `schema_version` 1.8.

## Requirements

### Functional Requirements

- **FR-001**: No link between entities is refused for joining entities of two resources or two data sources, at model build or at graph build.
- **FR-002**: A resource named by an `@entity` names a data source; otherwise model build and graph build refuse it, naming the resource and its entities.
- **FR-003**: `PostgresResource` takes only `data_source=`; connection parameters live only in `PostgresDataSource`.
- **FR-004**: `InMemoryDataSource` and `ExternalServiceDataSource` exist, exported beside `PostgresDataSource`.
- **FR-005**: Two resources with one domain and one data source are refused at model build and at graph build, naming the domain, the data source and both resources.
- **FR-006**: AOA writes graphs at protocol 1.8, its schema copy is gnomon's `graph/1.8.json`, and Maxitor 3.22.0 from the pinned gnomon commit checks them.
- **FR-007**: Every test, example and adapter of this repository, and the demo, follow FR-002 and FR-005.
- **FR-008**: The documentation of the data source carries the frame on the connection policy (issue, 1.4); the pages on relations and resources say relations know no store.
- **FR-009**: Rebuilt graphs, raised versions, changelog.

## Success Criteria

- **SC-001**: The closing check run on the pull request is green, the demo's graph included.
- **SC-002**: Each refusal of FR-002, FR-003 and FR-005 has a test, broken once on purpose.
- **SC-003**: A relation across data sources builds into a graph that `graph-builder` 3.22.0 accepts at 1.8.

## Assumptions

- Maxitor shows these models through bystrovmaxim/gnomon#60; nothing here depends on it.
