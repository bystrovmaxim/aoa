# Feature Specification: The cache is declared like an access check, and the graph shows it

**Feature Branch**: `feature/issue-412-cache-declared`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Issue #412, "Entity as DTO 6/8: the cache is declared like an access check, and the graph shows it", step 6 of 8 of #399, before #410, with its cases 11.1–11.6 and their real Before outputs.

## Overview

The **cache** keeps an action's Result so that a repeated call returns it without running the action. Today an action decides what to cache by overriding four methods of `BaseAction` — `cache_key`, `read_cache`, `on_cache_write`, `on_cache_invalidate`. Nothing checks their shape: the key is synchronous, the order of parameters differs between them, none receives `box` or `connections`. A key without a write silently caches nothing, an invalidation of a type nobody caches silently drops nothing, a tag without a type matches every type, and the graph does not know the cache exists.

After this change the cache is four declarations built like `@access_decide`: `@cache_key`, `@cache_read`, `@cache_write`, `@cache_invalidate`. Each has a description, a suffixed `async` method, a fixed signature starting with `self, params, box, connections`, at most one of a kind per action, never inherited. A declaration that can never have an effect is refused at the earliest moment that can see it. Tag types are declared in the decorators, and the graph shows each declaration and which entities an action caches and invalidates.

## Clarifications

### Session 2026-11-05

The maintainer asked for the whole task without questions; the answers taken:

- Q: What may a tag type be? → A: an entity class. The graph links an action to each tag type, and only an entity is a node it can link to.
- Q: May `@cache_write` declare no tag types? → A: yes; its method then returns no tags (`[]`), and only the key finds the entry. The issue refuses an empty list only on `@cache_invalidate`, which would drop nothing.
- Q: Does a key-only `CacheTag(key=...)` remain valid outside declarations? → A: the class is unchanged; a declaration may not return one (11.4).
- Q: Is a cache declaration one graph node type or four? → A: one, `Cache`, with its kind among its properties; each is reached from its action by an edge named after the declaration (`@cache_key`, …).
- Q: Does a declaration announce plugin events, as the object check does? → A: no; this step changes how the cache is declared and seen, not what it tells plugins.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare what an action caches (Priority: P1)

A developer declares the key, the write, the read and the invalidation of an action as four declarations with fixed signatures, and the machine calls them.

**Why this priority**: It replaces the four unchecked methods every caching action uses; everything else in this step builds on it.

**Independent Test**: Declare an action with all four, run it twice through a machine with a cache; misdeclare each rule and see the refusal.

**Acceptance Scenarios**:

1. **Given** `GetOrderAction` with `@cache_key` (asking `tenant_id` through `@context_requires`) and `@cache_write(tags=(OrderCoreEntity,))`, **When** it runs twice with the same params, **Then** the second run is a hit, and the key received `ctx` (case 11.1).
2. **Given** a declaration with an empty description, a name without its suffix, a plain `def`, renamed or reordered parameters, or a missing annotation, **When** the class body runs, **Then** it is refused with the matching error.
3. **Given** a parameter annotated with a wrong type, **When** the graph is assembled, **Then** `AspectSignatureError` names it.
4. **Given** two `@cache_key` on one action, **When** the class is created, **Then** it is refused, naming both methods.
5. **Given** a subclass of a caching action that declares nothing, **When** it runs, **Then** it does not cache.
6. **Given** `@cache_read` returning `None`, **When** the entry is found, **Then** it is dropped and the action runs, as `read_cache` did.

---

### User Story 2 - A declaration without an effect is refused (Priority: P1)

A developer who declares a key without a write, or an old hook without a declaration, learns it when the class is created.

**Why this priority**: "I turned the cache on and it does nothing" is the trap this step removes.

**Independent Test**: Declare each incomplete combination and each old method name.

**Acceptance Scenarios**:

1. **Given** `@cache_key` without `@cache_write`, **When** the class is created, **Then** `DeclarationStructureError: KeyOnlyAction declares @cache_key without @cache_write; a key without a write never stores anything.` (case 11.2)
2. **Given** `@cache_write` without `@cache_key`, or `@cache_read` without the pair, **Then** each is refused.
3. **Given** `@cache_invalidate` alone, **Then** it is accepted.
4. **Given** a method named `cache_key`, `read_cache`, `on_cache_write` or `on_cache_invalidate` without a declaration, **When** the class is created, **Then** it is refused, naming the declaration that replaces it (case 11.6).
5. **Given** `BaseAction`, **Then** it has none of the four methods.

---

### User Story 3 - Tags carry declared types (Priority: P1)

A developer declares the entity types an action's tags may name; a tag of another type, or without a type, fails the call.

**Why this priority**: A type-less tag matches every entry (case 11.4); a declared type is what the graph can show.

**Independent Test**: Return tags of a declared type, an undeclared type and no type.

**Acceptance Scenarios**:

1. **Given** `@cache_write(tags=(OrderCoreEntity,))` returning `CacheTag(type=OrderCoreEntity, key="o1")`, **Then** the entry is written with that tag.
2. **Given** it returns `CacheTag(type=CustomerCoreEntity, key="c1")` or `CacheTag(key="o1")`, **When** the action runs, **Then** `CacheContractError` names the action and the tag (case 11.4).
3. **Given** `@cache_invalidate` with no tag types, or a tag type that is not an entity class, **When** the class body runs, **Then** it is refused.

---

### User Story 4 - The graph shows the cache (Priority: P2)

An architect sees in the graph and in Maxitor which actions cache which entities and which drop them; a dead invalidation or a dead tag fails the build.

**Why this priority**: It makes the cache part of the visible architecture, and lets the build check the tags across actions.

**Independent Test**: Build a graph with a reading, a listing and an updating action; read the nodes and edges; add a dead invalidation and a dead tag.

**Acceptance Scenarios**:

1. **Given** `GetOrderAction`, `ListOrdersAction` and `UpdateOrderAction`, **When** the graph is built, **Then** each declaration is a `Cache` node of its action with its kind and description, `caches` edges go from the two readers to `OrderCoreEntity`, and an `invalidates` edge from the updater (case 11.5).
2. **Given** `DropInvoiceAction` invalidating `InvoiceCoreEntity` that no action caches, **When** the graph is built, **Then** it is refused: `DropInvoiceAction drops InvoiceCoreEntity, but no action caches it` (case 11.3).
3. **Given** an action caching a type no action invalidates, **Then** the build is refused, naming the action and the type.
4. **Given** the graph's JSON, **Then** it validates against the protocol, which knows the new node and edge types, and Maxitor loads it.

### Edge Cases

- An action that only invalidates caches nothing and needs no key.
- `@context_requires` above the cache decorator instead of under it is explained in the refusal, as for `@access_decide`.
- A key returning `None` skips the read and the write for that call; the invalidation still runs.
- A Result from `@on_error` is neither written nor invalidated, as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: AOA MUST provide `@cache_key`, `@cache_read`, `@cache_write(…, tags=…)` and `@cache_invalidate(…, tags=…)`, each taking a non-empty description, on an `async` method whose name ends with its kind.
- **FR-002**: Each declaration's parameters MUST be `self, params, box, connections`, then its own (`entry`; `result, duration_ms`; `result`), then `ctx` when `@context_requires` is under it; names, order and annotations checked at declaration, types at assembly.
- **FR-003**: An action MUST declare at most one of each kind, in its own namespace; a second is refused naming both; declarations are not inherited.
- **FR-004**: `@cache_key` and `@cache_write` MUST come together, `@cache_read` only with them; `@cache_invalidate` may stand alone.
- **FR-005**: `BaseAction` MUST NOT have the four old methods; a method with an old name and no declaration MUST be refused when the class is created, naming its replacement.
- **FR-006**: Tag types MUST be declared as a tuple of entity classes, non-empty on `@cache_invalidate`; a returned tag of an undeclared type or without a type MUST raise `CacheContractError` naming the action and the tag.
- **FR-007**: The graph MUST hold each declaration as a `Cache` node of its action and an edge from the action to each tag type, `caches` for a write and `invalidates` for an invalidation.
- **FR-008**: The graph build MUST refuse an invalidated type no action caches and a cached type no action invalidates.
- **FR-009**: The graph protocol, the graph builder and Maxitor MUST accept the new node and edge types.

### Key Entities

- **Cache declaration**: kind (key, read, write, invalidate), description, method, tag types (write, invalidate).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each case 11.1–11.6 gives its After output in a test.
- **SC-002**: Every caching action of the repository is written with declarations, and every graph file validates and loads in Maxitor.

## Assumptions

- The cache store stays per service, so one graph sees every writer and invalidator (#412, 11.3).
- #410 builds on these declarations; this step does not change what is stored.
