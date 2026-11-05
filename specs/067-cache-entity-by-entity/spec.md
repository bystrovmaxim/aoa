# Feature Specification: A collection is cached entity by entity

**Feature Branch**: `feature/issue-413-cache-entity-by-entity`

**Created**: 2026-11-05

**Status**: Draft

**Input**: Issue #413, "Entity as DTO 8/8: a collection is cached entity by entity", step 8 of 8 of #399, after #408, #412 and #410, with its cases 12.1–12.7.

## Overview

The cache keeps one entry per call, with full copies of the entities inside it: two actions that return the same order keep two copies, and changing that order drops both entries, the whole list included. This step adds a second layout, **entity by entity**: every entity is stored once under a key the action builds, and an entry for a collection keeps the keys of its entities and the Result's other fields — a library card that lists shelf numbers, not books. Two actions that build the same key for an entity share its entry; changing one entity drops one entry.

## Clarifications

### Session 2026-11-05

The maintainer asked for the whole task without questions; the answers taken:

- Q: Where do entity entries live, so that two actions share them? → A: in the store under one namespace for entities, not under the action's class; the store's existing four methods do the work, with `CachedEntity` as the namespace class, and one more method reads several keys at once.
- Q: Is `@cache_entity_key` a graph node? → A: yes, as every cache declaration (#412): a `Cache` node of kind `entity_key` reached by `@cache_entity_key`. Published protocol versions never change, so this is Open Gnomon Protocol 1.5.
- Q: Which types does an entity-by-entity write cache, for the graph and for the dead-tag check? → A: its declared tags and the entity types of the Result fields it stores entity by entity; a `caches` edge goes to each.
- Q: When is rule 12.7.1 checked? → A: when the graph is assembled, where the Result type resolves; the pairing of 12.7.2 when the class is created.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare an entity-by-entity cache (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `@cache_write(..., layout=CacheLayout.ENTITIES)` and `@cache_entity_key` on an action whose Result has a field typed by an entity with an `id`, **Then** it is accepted, and the graph shows the `entity_key` node and a `caches` edge to the entity type.
2. **Given** `layout=CacheLayout.ENTITIES` without `@cache_entity_key`, or the other way round, **Then** the class is refused when it is created (12.7.2).
3. **Given** `@cache_entity_key` misdeclared (description, suffix, `async`, parameters `self, params, box, connections, entity` (+ `ctx`), return `str`), **Then** it is refused as the other declarations are.
4. **Given** a Result with no field typed by an entity, or an entity without `id`, **Then** the graph build refuses the layout (12.7.1).

---

### User Story 2 - One entity, one entry (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `ListOrdersAction(c1)` and `GetOrderAction(o1)` building the key `a:order:o1:row` for `o1`, **When** both run, **Then** `o1` is stored once, and the list entry holds the keys of `o1` and `o2` and `total_count` (12.1, 12.2).
2. **Given** the list cached, **When** it runs again, **Then** the Result is assembled from the entries and the pipeline does not run (12.2).
3. **Given** `UpdateOrderAction(o1)` dropping `(OrderCoreEntity, "o1")`, **Then** only the entry of `o1` goes; `GetOrderAction(o2)` keeps hitting; the list misses once, runs whole and writes `o1` again (12.1, 12.3).
4. **Given** `CreateOrderAction` dropping `(CustomerCoreEntity, "c1")`, **Then** the list entry goes and the next list shows the new order (12.4).

---

### User Story 3 - A hit never returns part of a Result (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a list entry whose entity entry is gone, **Then** the call is a miss: the list entry is dropped, the pipeline runs whole, `@cache_read` is not called (12.3).
2. **Given** an entity entry whose form the reader refuses (a partial entity where a full one is required), **Then** the call is a miss (12.5).
3. **Given** every entity present, **Then** `@cache_read` receives the assembled Result.

---

### User Story 4 - One round trip (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a hit on a list of two orders, **Then** the store is asked for both entity entries in one `get_entries` call (12.7.4); the shipped store and the how-to's store implement it.

## Requirements *(mandatory)*

- **FR-001**: `@cache_write` MUST take `layout=CacheLayout.WHOLE | CacheLayout.ENTITIES` (default `WHOLE`); `@cache_entity_key` MUST follow the rules of #412's declarations with the parameters `self, params, box, connections, entity` (+ `ctx`) and return `str`.
- **FR-002**: The pairing of FR-001's two MUST be checked when the class is created; the Result's entity fields and their `id` when the graph is assembled.
- **FR-003**: An entity-by-entity write MUST store each entity of the Result's entity fields under the key `@cache_entity_key` builds, tagged `(type, id)`, and the collection entry with the keys and the other fields, tagged with the write's tags.
- **FR-004**: A hit MUST read the entity entries in one call, assemble the Result and read it with the Result type; a missing or unreadable entity MUST make a miss that drops the collection entry; `@cache_read` only when every entity is present.
- **FR-005**: The graph MUST show the `entity_key` declaration and `caches` edges to the entity types; the dead-tag check MUST count them; protocol 1.5, the graph builder, the comparison and Maxitor MUST read it.

## Success Criteria *(mandatory)*

- **SC-001**: Each case 12.1–12.7 gives its After output in a test; the adversarial break of phase 5 (one entity entry removed) gives a miss, not a shorter list.

## Assumptions

- Measured on `main` at `256ea6ef2`: the issue's Before outputs (12.1, 12.4) describe today's one-entry-per-call cache, unchanged by #410 apart from the entry being JSON.
