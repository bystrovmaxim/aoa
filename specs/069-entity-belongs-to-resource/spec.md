# Feature Specification: An entity belongs to one resource, and its relations stay inside it

**Feature Branch**: `feature/issue-469-entity-belongs-to-resource`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Issue #469, "An entity belongs to one resource, and its relations stay inside it" — step 2 of 4 of one change: bystrovmaxim/gnomon#45 (protocol 1.6, the `entity_resource` edge, published) → this issue → bystrovmaxim/gnomon#46 (Maxitor) → bystrovmaxim/gameoffer#146.

## Overview

An entity is a row that is stored somewhere. Today an entity names only a domain, so nothing says where it is stored, and nothing stops a model from relating two entities that live in different stores as if they were two tables of one database. A relation is a join or a foreign key, and a join exists only inside one database.

After this change an entity names the resource that stores it, and only that:

```python
@entity(description="Customer order", resource=StorefrontDatabase)
class SalesOrderCoreEntity(BaseCoreEntity): ...
```

The entity's domain is its resource's domain. Every relation joins two entities of one resource; a relation across resources is refused when the model is built. The graph carries an `entity_resource` edge from every entity to its resource, and the graph build refuses a document that breaks either rule. Every check lives in AOA: gnomon only describes the edge, Maxitor only reads it.

## Clarifications

### Session 2026-11-05

- Q: How does a state type (`BaseStateEntity`) get a resource, given it carries no `@entity`? → A: It declares none; its resource is the resource of the entities whose `Lifecycle[...]` uses it, and a state type used by entities of two resources is refused.
- Q: What happens to the 48 demo associations that cross domains? → A: `CurrencyEnumEntity` moves to Billing's database and its 25 associations stay; `DictionariesDomain` goes; the other 23 are removed.
- Q: How are entities spread over the resources of a demo domain that has several? → A: By what each entity plausibly is, so gateways and caches own entities too. The demo exists for volume: an entity, a relation or a domain may be removed, moved or added wherever that is the logical way to satisfy the rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare where an entity is stored (Priority: P1)

A model author declares an entity with the resource that stores it. The entity's domain is no longer written on the entity; it is read from the resource.

**Why this priority**: Every other rule of this change reads the entity's resource. Without it nothing else can be checked.

**Independent Test**: Declare a resource with `@meta(domain=StoreDomain)` and an entity with `resource=` that resource; the entity's domain reads `StoreDomain`. Each wrong declaration below is refused at class definition.

**Acceptance Scenarios**:

1. **Given** `StorefrontDatabase` with `@meta(domain=StoreDomain)`, **When** `@entity(description="Customer order", resource=StorefrontDatabase)` decorates `SalesOrderCoreEntity`, **Then** the class is accepted and its domain is `StoreDomain` (case 2.6).
2. **Given** `@entity(description="Customer order")` with no resource, **Then** the class is refused: `EntityDecoratorError: SalesOrderCoreEntity — @entity needs resource=: an entity is stored by a resource.` (case 2.1; Before: accepted).
3. **Given** `@entity(description="Customer order", domain=StoreDomain, resource=StorefrontDatabase)`, **Then** Python refuses the call with `TypeError`: `@entity` has no `domain` parameter (case 2.2).
4. **Given** `resource=StoreDomain` or `resource=SomeAction`, **Then** the class is refused, naming the entity and what was given (case 2.3).
5. **Given** `resource=(StorefrontDatabase, StorefrontSessionCache)`, **Then** the class is refused, naming the entity and both resources: an entity has one resource (case 2.5).
6. **Given** a resource of each kind — a storage, a gateway, a controller — **Then** each is accepted as an entity's resource.

---

### User Story 2 - A relation stays inside one resource (Priority: P1)

A model author relates two entities. When both are stored by one resource the model builds; when they are stored by two, the model build refuses it and names both entities and both resources.

**Why this priority**: This is the rule the change exists for: a model cannot claim a join that no database can perform.

**Independent Test**: Build a model with `SupportTicketCoreEntity` (resource `SupportDatabase`) holding `AssociationOne[SalesOrderCoreEntity]` (resource `StorefrontDatabase`); the build fails with the message below. Move both into one resource; the build passes.

**Acceptance Scenarios**:

1. **Given** the association above, **When** the model is built, **Then** it is refused: `SupportTicketCoreEntity.order relates SupportTicketCoreEntity (SupportDatabase) to SalesOrderCoreEntity (StorefrontDatabase): a relation stays inside one resource.` (case 2.4; Before: accepted).
2. **Given** the same pair related by an aggregation or a composition, on either side, **Then** the build is refused the same way.
3. **Given** an inverse side whose two ends have different resources, **Then** the build is refused the same way.
4. **Given** a specialization or a generalization between entities of two resources, **Then** the build is refused the same way.
5. **Given** a field referencing a dictionary of another resource, **Then** the build is refused the same way: a dictionary is an ordinary entity of its resource.
6. **Given** a state type (`BaseStateEntity`) used by the `Lifecycle[...]` fields of entities of two resources, **When** the model is built, **Then** it is refused, naming the state type, both entities and both resources. A state type declares no resource of its own: its resource is the resource of the entities whose lifecycle uses it.
7. **Given** every relation of a model inside one resource, **Then** the build passes and nothing else about the relations changes.

---

### User Story 3 - The graph shows where every entity is stored (Priority: P2)

A reader of the graph — Maxitor, a script, a reviewer — sees for each entity the resource that stores it and, through it, the domain.

**Why this priority**: The graph is how the rule leaves AOA; bystrovmaxim/gnomon#46 cannot start without it. It follows from Stories 1 and 2.

**Independent Test**: Build the graph of a model with `SalesOrderCoreEntity` stored by `StorefrontDatabase`; it validates against protocol 1.6 and holds the two edges below. Hand the graph check a document that breaks either rule; it is refused before anything is written.

**Acceptance Scenarios**:

1. **Given** the model of Story 1, **When** its graph is built, **Then** it holds `entity_resource` from `SalesOrderCoreEntity` to `StorefrontDatabase` (`Aggregation`, `is_dag` true, no properties) and `domain` from `SalesOrderCoreEntity` to `StoreDomain`, and its `schema_version` is `1.6`.
2. **Given** a graph in which an entity has no `entity_resource` edge, or two, **When** the graph is built, **Then** the build fails naming the entity, before a graph is written.
3. **Given** a graph in which a relation edge, an inverse side, a specialization, a generalization or a lifecycle state joins entities of two resources, **When** the graph is built, **Then** the build fails naming both entities and both resources, before a graph is written.
4. **Given** AOA's copy of the protocol schema, **Then** it equals the published `graph/1.6.json` byte for byte.

---

### User Story 4 - The demo, the examples and the tests follow the rule (Priority: P2)

Everything this repository ships declares its entities with resources, and none of it relates entities across resources.

**Why this priority**: Without it the repository does not build; with it the demo becomes the first model that shows a database with all its entities.

**Independent Test**: Build the demo's graph; every one of its entities has exactly one resource, no relation crosses resources, and the saved `graph.json` is rebuilt from it. Every example runs; every test passes.

**Acceptance Scenarios**:

1. **Given** the demo (213 entities in 18 domains, 16 resources in 4 of them), **Then** every entity names a resource; each of the 13 other domains with no resource gets a storage resource of its own; in a domain with several resources each entity names the one it plausibly lives in, so that at least one gateway and one cache own entities.
2. **Given** the 48 demo associations that cross domains today, **Then** the 25 from Billing to `CurrencyEnumEntity` stay, because `CurrencyEnumEntity` is stored by Billing's database and `DictionariesDomain` goes; the other 23 are removed.
3. **Given** the 232 demo relations inside one domain, **Then** each is checked again once resources are chosen; one that would cross resources is removed, or one of its entities moves.
4. **Given** every example and every test that declares an entity, **Then** each names a resource and runs.

---

### User Story 5 - The documentation tells the new rule (Priority: P3)

A reader of the tutorial and the reference learns that an entity is stored by a resource, takes its domain from it, and relates only to entities of the same resource — with each refusal shown as a case.

**Why this priority**: Documentation ships with the change (Principle VI); it is written once the code is settled.

**Independent Test**: Every case of this specification appears in the tutorial or the reference as a script and a notebook, and each runs and prints what the page shows.

**Acceptance Scenarios**:

1. **Given** tutorial steps 21 (resource) and 22–25 (entity, dictionaries, relations, lifecycle), **Then** every declaration names a resource, and each refusal of this change is a case with its real output.
2. **Given** `docs/reference/intents-and-invariants.md`, **Then** "Mandatory domain" says an entity takes its domain from its resource, and "Entity relations" carries the one-resource rule.
3. **Given** `README.md`, **Then** its entity declarations name a resource.

---

### Edge Cases

- **A resource with no `@meta`**: the entity has no domain to take. The declaration is refused, naming the entity and the resource.
- **A base class given as the resource** (`BaseResource`, `BaseStorage`, `BaseGateway`, `BaseController` itself): refused like any non-resource — an entity is stored by a concrete resource, not by a kind.
- **An entity related to itself** (a tree): one resource on both ends; accepted.
- **A subclass of an entity**: without its own `@entity` it inherits its parent's declaration, resource included; with its own `@entity(resource=...)` naming another resource, a specialization to that parent is refused (Story 2, scenario 4).
- **A resource that no action depends on**: the graph still holds its node, because an entity names it; the `entity_resource` edge never points at a missing node.
- **An entity class without `@entity`** (a plain Pydantic shape used inside an example, a state type): not asked for a resource by the decorator. A state type takes its resource from the entities that use it (Story 2, scenario 6).
- **A state type used by no entity**: it has no resource, and nothing asks it for one.
- **Two entities of one domain stored by two resources** (Store, Billing, Messaging, Catalog in the demo): accepted as long as no relation joins them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `@entity` MUST require `resource=`, and MUST refuse a declaration without it with the message of case 2.1, naming the entity.
- **FR-002**: `@entity` MUST have no `domain` parameter.
- **FR-003**: `@entity` MUST accept as `resource` exactly one concrete subclass of `BaseResource` of any kind (storage, gateway, controller), and MUST refuse anything else — a domain, an action, a non-class, a tuple or other collection of resources, a base kind — naming the entity and what was given.
- **FR-004**: An entity's domain MUST be read from its resource's `@meta(domain=...)`. There MUST be one source for it: nothing compares an entity's domain with its resource's domain.
- **FR-005**: The model build MUST refuse every association, aggregation and composition (either side), every inverse side, every specialization, every generalization, every dictionary reference and every lifecycle state that joins entities of two resources, naming the field or the link, both entities and both resources, with the message shape of case 2.4.
- **FR-006**: The graph MUST hold exactly one `entity_resource` edge from every entity to its resource — `Aggregation`, `is_dag` true, no properties — and the entity's `domain` edge MUST point at its resource's domain.
- **FR-007**: The graph build MUST refuse, before a graph is written, an entity without exactly one `entity_resource` edge and any relation edge, dictionary reference, inverse side, specialization, generalization or lifecycle state whose ends have different resources, naming the entity or entities and their resources.
- **FR-008**: The graph MUST be written as protocol 1.6, and AOA's copy of the schema MUST equal the published `graph/1.6.json` byte for byte.
- **FR-009**: Every entity of the demo MUST name a resource, no demo relation may cross resources, and the demo's saved graph MUST be rebuilt from the result.
- **FR-010**: Every entity declared in `examples/`, in the tests of every package, in `docs/` and in `README.md` MUST name a resource. `specs/` keeps its history and is not changed.
- **FR-011**: The documentation MUST show every case of this specification — each acceptance and each refusal — as a script and a notebook, with the output a run of this code prints.
- **FR-012**: Every package level this change touches MUST raise its version, and `docs/CHANGELOG.md` MUST carry one article about the change.

### Key Entities

- **Entity**: a row stored by exactly one resource. Declares a description and a resource; its domain is derived.
- **Resource**: a storage, a gateway or a controller. Declares its domain with `@meta`; owns zero or more entities.
- **Domain**: the bounded context; reached from an entity only through its resource.
- **Relation**: an association, aggregation or composition, its inverse side, a specialization, a generalization, a dictionary reference or a lifecycle state; joins two entities of one resource.
- **`entity_resource` edge**: the graph's statement that an entity is stored by a resource; one per entity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each case 2.1–2.6 of the issue gives its After output in a test, word for word.
- **SC-002**: In the demo's rebuilt graph, every entity has exactly one `entity_resource` edge, 0 relation edges join entities of two resources, at least one gateway and one cache own entities, and the demo still holds at least 200 entities and 200 relations.
- **SC-003**: 0 entity declarations in `packages/`, `examples/`, `docs/` and `README.md` lack a resource; 0 pass `domain=`.
- **SC-004**: Every example script and notebook of the documentation runs and prints what its page shows; the closing check run reports 0 remarks beyond the one accepted LangGraph warning.
- **SC-005**: A graph document that breaks either rule of FR-007 never reaches disk: the build fails in each of the five link kinds and for zero and two `entity_resource` edges.

## Assumptions

- Measured on `main` at `fea32db3c`, 2026-11-05: the demo has 213 entities in 18 domains and 16 resources in 4 of them (Store 45 entities / 2 resources, Billing 27 / 5, Messaging 18 / 5, Catalog 17 / 4); 106 entities in 14 domains with no resource; 280 relation edges, 48 of them across domains, all associations, 25 to `CurrencyEnumEntity`; the saved `graph.json` is protocol 1.5.
- Measured at the same commit: 373 `@entity` declarations in 61 test files of `aoa-action-machine`, 18 in the adapters' tests, 364 in 115 files of `examples/`, 52 in 14 pages of `docs/`, 4 in `README.md`. (The issue counted 202 in 46 and 16 for the tests; the plan works from this count.)
- The demo exists for volume, not for a story: its entities, relations and domains may be removed, moved or added wherever that is the logical way to satisfy the rule; the plan lists what moved. Each demo domain with no resource, other than `DictionariesDomain`, gets one storage resource of its own.
- One lifecycle class, `CatalogDenseLifecycle`, is used by entities of Catalog and Inventory today; in the demo it is split in two, one per resource.
- In the demo, `CurrencyEnumEntity` moves to Billing's database, `DictionariesDomain` goes, and the 23 other associations that cross domains are removed.
- A field that references an entity of another resource has no allowed form in this change; a separate kind of field for it may come later (out of scope).
- Protocol 1.6 is published (bystrovmaxim/gnomon#45, closed): `entity_resource` from `Entity` to `Resource`, `Aggregation`, `is_dag` true, empty properties; the schema leaves "exactly one per entity" to the exporter, which is why AOA checks it.
- Out of scope: Maxitor (bystrovmaxim/gnomon#46) and the game offers (bystrovmaxim/gameoffer#146).
