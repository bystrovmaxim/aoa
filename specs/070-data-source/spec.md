# Feature Specification: A resource may work through a data source, and relations stay inside it

**Feature Branch**: `feature/issue-475-data-source`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #475, "Data source 2/4: a resource may work through a data source, and relations stay inside it". The issue's sections 1–4 are the requirements; this spec records the decisions taken while reading the code.

## What this is

Today a relation between entities is allowed only inside one resource. A resource is often a part of a database, so relations between entities of different resources of one database are refused although a join between them is ordinary.

After this change a resource may name the store it shares with other resources — its **data source**, a new primitive `BaseDataSource` — and relations follow it: inside the data source when the resource has one, inside the resource when it has none. A data source keeps the connection parameters and the pool; the resource keeps the transaction. The graph gets the `DataSource` node and the `resource_data_source` edge of protocol 1.7 (bystrovmaxim/gnomon#51). AOA checks every rule of the model; the schema checks only the shape of rows.

## Clarifications

### Session 2026-11-06

- Q: How does a data source carry its description, given that `@meta` requires a domain? → A: `@meta(description=...)` with no `domain`. `@meta` refuses a domain on a `BaseDataSource` subclass and still requires one on every other host.
- Q: How does a resource name its data source? → A: As the type argument of a generic resource base: `BaseResource[D: BaseDataSource]`, and so `BaseStorage`, `BaseGateway`, `BaseController`, `SqlResource`, `PostgresResource[D: PostgresDataSource]`. A resource that inherits a base without a type argument has no data source. AOA reads the data source from the class's generic bases.
- Q: When is a data source of the wrong kind refused? → A: When the resource class is created: Python does not check type-variable bounds, so `BaseResource.__init_subclass__` compares each data source argument with the bound of the parameter it fills, and refuses a second, different data source in one hierarchy.
- Q: `ExternalServiceResource` is already generic in its client type. → A: It keeps that one parameter and has no data source; a gateway that needs one derives from `BaseGateway[D]`.
- Q: Does the domain rule cover `@connection` as well as `@depends`? → A: No, `@depends` only. A connection is handed over by the caller of the action — a transport's socket channel (`SocketChannel` of `TransportDomain`), for one — not chosen by the action. Today the demo has two cross-domain `@depends` (`CheckoutSubmitAction` of `StoreDomain` on `PaymentGatewayResource` of `BillingDomain` and on `NotificationGatewayResource` of `MessagingDomain`).
- Q: Is a framework kind (`PostgresDataSource`) a node of the graph? → A: No: like `PostgresResource`, it is excluded from the graph model; only an application's data sources are nodes, so "a data source has at least one resource" holds.
- Q: Where does the pool wait bound live? → A: On the data source (`PostgresDataSource.acquire_timeout`), since the data source hands connections out.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resources of one database relate their entities (Priority: P1)

A developer declares one data source for a database and names it on the resources that work with it. Entities of those resources relate to each other; the model builds.

**Independent Test**: two resources on one data source, an association between their entities: the model builds; the same association between resources of two data sources, or with a resource without one, is refused with a message naming both entities, both resources and both boundaries.

**Acceptance Scenarios**:

1. **Given** `OrdersResource(PostgresResource[ShopDataSource])` and `SupportResource(PostgresResource[ShopDataSource])`, **When** an entity of `SupportResource` holds an association to an entity of `OrdersResource`, **Then** the model builds.
2. **Given** the same, with `SupportResource` on `BillingDataSource`, **Then** the build refuses: `... a relation stays inside one data source, or inside one resource when there is none.`
3. **Given** a resource with no data source, **When** one of its entities relates to an entity of another resource, **Then** the build refuses, as today.
4. The same for the inverse side, a dictionary field, a specialization, a generalization and a shared lifecycle state type.

### User Story 2 - A pool lives in a data source; a resource without one opens its own connection (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `async with ShopDataSource(dsn) as shop`, **When** `OrdersResource(data_source=shop)` opens, **Then** it takes a connection from the data source's pool and gives it back on close; its transaction is its own.
2. **Given** `SessionResource(connection_params={...})` with no data source, **When** it opens, **Then** it opens its own connection and closes it, as today.
3. **Given** a resource with a data source parameter, **When** it is built with `connection_params=`, with neither, with both, or with a data source of another class, **Then** it raises, naming the resource and what it needs; a resource without one built with `data_source=` raises too.
4. `pool=` is not accepted by `PostgresResource`.

### User Story 3 - The graph shows data sources (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a model with `ShopDataSource` and two resources on it, **When** the graph is built, **Then** it is protocol 1.7 and has a `DataSource` node with one `application` edge, and one `resource_data_source` edge from each of the two resources; a resource without a data source has none.
2. **Given** a graph whose rows were changed after the model build (two data source edges on a resource, a data source with no resource, a relation across boundaries), **When** the graph build checks it before writing, **Then** it refuses, naming the rows.

### User Story 4 - An action depends only on resources of its domain (Priority: P2)

**Acceptance Scenarios**:

1. **Given** an action of `SalesDomain` with `@depends` on a resource of `BillingDomain`, **When** the model is built, **Then** it is refused, naming the action, the resource and both domains.
2. **Given** an action with `@connection` on a resource of another domain, such as a transport's socket channel, **Then** the model builds: a connection is handed over by the caller.

### Edge Cases

- `class OrdersResource(PostgresResource[RedisDataSource])` → refused when the class is created, naming the resource, the data source and the kind it needs.
- A hierarchy that names two different data sources → refused when the class is created.
- `@meta(description=..., domain=X)` on a data source → refused; `@meta(description=...)` without a domain on a resource → refused, as today.
- A data source class whose name does not end in `DataSource` → refused when the class is created.
- A data source used by `@depends` → refused: a data source is not depends-eligible.
- A wrapper class of a resource (`get_wrapper_class()`) declares the same data source as the resource it wraps, by the same type argument.

## Requirements *(mandatory)*

- **FR-001**: `BaseDataSource` — `@meta(description=...)` with no domain, a name ending in `DataSource`, no methods, not depends-eligible, exported from `aoa.action_machine.resources`.
- **FR-002**: `BaseResource` and its kinds take an optional data source type argument; a resource has at most one data source; a data source argument outside the bound of its parameter is refused when the class is created.
- **FR-003**: `PostgresDataSource` keeps connection parameters and a pool, opens and closes as an async context manager, hands out and takes back a connection with its `acquire_timeout`; it accepts a ready pool for tests and for an application that creates its own.
- **FR-004**: `PostgresResource` takes exactly one of `connection_params=` and `data_source=` with the checks of US2; `pool=` is removed; transactions, rollup and the wrapper do not change.
- **FR-005**: The model build refuses a relation, an inverse side, a dictionary field, a specialization, a generalization or a lifecycle state type that joins entities of two boundaries; the boundary is the data source, or the resource without one.
- **FR-006**: The model build refuses an `@depends` from an action to a resource of another domain; an `@connection` is not judged.
- **FR-007**: The graph is protocol 1.7: `DataSource` nodes with an `application` edge, `resource_data_source` edges; AOA's copy of the schema is gnomon's `graph/1.7.json` byte for byte.
- **FR-008**: The graph build checks again, before writing, every rule a schema cannot check: at most one data source edge per resource, from a `Resource` to a `DataSource`; one `application` edge and at least one resource per data source; relations and lifecycle states inside one boundary.
- **FR-009**: Every refusal names the elements involved; every rule has a test that builds a model breaking it.
- **FR-010**: The demo's identity route builds `IdentityStore(data_source=...)` over `IdentityDataSource`; the two cross-domain `@depends` of `CheckoutSubmitAction` move into the action's own domain.
- **FR-011**: Examples, tests and documentation use `data_source=` where they used `pool=`; graph files rebuilt; versions raised; changelog.

## Success Criteria *(mandatory)*

- **SC-001**: A model with two resources on one data source and a relation between their entities builds; each refusal of the spec is produced by a test.
- **SC-002**: The demo graph is protocol 1.7 and passes `graph-builder check`.
- **SC-003**: The closing check run is zero.

## Assumptions

- The demo's three databases and their relations are bystrovmaxim/aoa#476.
- Maxitor showing data sources is bystrovmaxim/gnomon#52.
- AOA's CI uses Maxitor 3.18.0, published with schema 1.7, and the `graph-builder` action at `maxitor-v3.18.0`.
