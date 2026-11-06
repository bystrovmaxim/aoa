# Feature Specification: The demo has three databases with relations between their resources

**Feature Branch**: `feature/issue-476-demo-data-sources`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #476, "Data source 3/4: the demo has three databases with relations between their resources". It builds on bystrovmaxim/aoa#475 (the `BaseDataSource` primitive and the relation rule) and is the graph bystrovmaxim/gnomon#52 is accepted on.

## What this is

After #475 AOA can say that several resources share one database and allows relations between their entities, but the demo shows none: every demo relation stays inside one resource. This change gives the demo three databases of different sizes and relations between resources inside them, so both AOA's graph and Maxitor's ERD can be accepted on a real model.

## Clarifications

### Session 2026-11-06

- Q: Which resources share a database? → A: `ShopDataSource` — `StorefrontDatabase` (Store), `SupportStorage` (Support), `InventoryStorage` (Inventory): three resources of three domains. `MessagingDataSource` — `OutboxPrimaryDatabase` and `MessagingDeadLetterStore` (Messaging): two resources of one domain, the outbox and its dead-letter queue. `CatalogDataSource` — `CatalogObjectStore`: a database with one resource.
- Q: Why not `IdentityDataSource` as the one-resource database? → A: `IdentityStore` imports the PostgreSQL driver, so the demo imports it lazily and it is not in the graph; `IdentityDataSource` (#475) stays the runtime pool of the identity route. The graph's one-resource database is the catalog's.
- Q: Which relations? → A: `SupportTicketAggregateCoreEntity.order` → `SalesOrderCoreEntity` and `.customer` → `CustomerAccountCoreEntity` (Support → Store, between domains, inside `ShopDataSource`); `ReplayTicketCoreEntity.message` → `OutboxMessageCoreEntity` (dead-letter queue → outbox, one domain, inside `MessagingDataSource`). Each is an association with `NoInverse()` and a description.
- Q: Where do the data sources live? → A: In `aoa.demo.model.data_sources`, a package of no domain, imported first by the graph build.

## Requirements

- **FR-001**: The demo declares `ShopDataSource`, `MessagingDataSource` and `CatalogDataSource`, each with `@meta(description=...)` and no domain.
- **FR-002**: The six resources above name their data source as their type argument; every other demo resource names none.
- **FR-003**: The three relations above exist, with descriptions; no relation crosses a data source.
- **FR-004**: The demo graph has three `DataSource` nodes, six `resource_data_source` edges and the three relations, and passes `graph-builder check`.
- **FR-005**: The demo's pages name the three databases; the demo's version is raised; the changelog has one article.

## Success Criteria

- **SC-001**: `graph-builder check` passes on the rebuilt demo graph, protocol 1.7.
- **SC-002**: The graph lists exactly the rows of FR-004.
