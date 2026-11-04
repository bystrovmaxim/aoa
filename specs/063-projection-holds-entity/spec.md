# Feature Specification: A projection holds the entity, and a field typed by an entity carries a full one

**Feature Branch**: `feature/issue-408-projection-holds-entity`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #408, "Entity as DTO 4/8: a projection holds the entity, and a field typed by an entity carries a full one", step 4 of 8 of #399, after #405 and #407, with its cases 6.1–6.4 and 7.1 and their real Before outputs.

## Overview

A **projection**, `OrderCoreEntity.schema(schema={...})`, is a partial view of an entity on a `Params` or `Result` field: only the fields its JSON Schema lists go out. Today its value is a plain `dict`. An action that has the entity copies its fields into a dict by hand, because the projection refuses the entity; an action that receives a projection in its Params gets a dict, not an entity; and a projection's schema may list a field the entity does not have, which then travels as if it were the entity's.

A field typed by the **bare entity**, meanwhile, accepts a partial entity, so a response can omit fields its own published schema requires, and the same JSON cannot be read back.

The graph links a field to its entity only when the field is a projection; a field typed by the entity itself has no such link.

After this change a projection holds the entity — a partial entity with exactly the projection's fields — whatever it is given; a projection can name only fields of its entity; a field typed by the bare entity carries a full entity; and every field typed by an entity is linked to it in the graph.

## Clarifications

### Session 2026-11-04

The maintainer asked for the whole task without questions; the answers taken:

- Q: Does a field typed by a dictionary (an enum entity, `currency: CurrencyEnumEntity`) get the graph edge of FR-008? → A: yes. A dictionary value is an entity; the rule is one: a field typed by an entity class is linked to it.
- Q: What does a Python-mode dump of a projection give? → A: the partial entity, as every entity value gives since #407; JSON mode gives the projection's fields.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Return an entity through a projection without copying it (Priority: P1)

A developer returns the entity an action loaded through a projection field, and the projection keeps exactly its fields.

**Why this priority**: The hand copy of fields into a dict is the boilerplate #399 exists to remove; every projection result pays it today.

**Independent Test**: Build a Result with a projection field from a full entity, a partial entity and a dict; dump it; read a field inside and outside the projection.

**Acceptance Scenarios**:

1. **Given** a full order and a projection of `id`, `status`, `total`, **When** the Result is built from the order, **Then** it is accepted; its JSON is `{'order': {'id': 'o1', 'status': 'paid', 'total': 99.5}}`; `r.order.status == 'paid'`; reading `r.order.customer_email` raises `FieldNotLoadedError` (case 6.1).
2. **Given** a partial order holding the three fields, or a dict of them, **When** the Result is built, **Then** the field holds the same partial entity.
3. **Given** a partial order without `total`, **When** the Result is built, **Then** it is refused, and the message names `total`.

---

### User Story 2 - Receive a projection as an entity (Priority: P1)

A developer whose action takes a projection in its Params reads an entity, not a dict.

**Why this priority**: Without it the action re-validates and re-wraps the dict by hand; with it the same entity type flows in and out.

**Independent Test**: Validate Params with a projection field from a dict and from JSON; read attributes and dict-style keys; send a value of the wrong type for the entity's field.

**Acceptance Scenarios**:

1. **Given** `{"order": {"id": "o1", "status": "paid", "total": 99.5}}`, **When** the Params are validated, **Then** `params.order` is a partial `OrderCoreEntity`, `params.order.id == 'o1'`, and `params.order["id"] == 'o1'` (case 6.2).
2. **Given** a value the projection's schema accepts but the entity's own field type refuses, **When** the Params are validated, **Then** it is refused: each value is checked by the projection's schema and by the entity's field type.

---

### User Story 3 - A projection names only its entity's fields (Priority: P1)

A developer declares a projection whose schema lists a field the entity does not have.

**Why this priority**: Today such a field travels under the entity's name although the entity never holds it — a silent leak of data the model does not describe.

**Independent Test**: Declare `OrderCoreEntity.schema(schema=...)` with a property `secret` the entity lacks.

**Acceptance Scenarios**:

1. **Given** a projection schema listing `secret`, **When** it is declared, **Then** the declaration is refused, naming `secret` and the entity (case 6.3).

---

### User Story 4 - A field typed by the entity carries a full entity (Priority: P2)

A developer returns a partial entity in a field typed by the bare entity.

**Why this priority**: The response would break its own published schema and could not be read back; the fix is to declare a projection.

**Independent Test**: Build a Result whose field is typed by the bare entity from a partial entity, alone, in `| None` and in `list[...]`.

**Acceptance Scenarios**:

1. **Given** `PlainOrderCoreEntity.partial(id="o2")`, **When** a Result field typed `PlainOrderCoreEntity` takes it, **Then** it is refused: the message says the entity is partial, lists what it holds and points to a projection (case 6.4).
2. **Given** a full entity, **When** the same field takes it, **Then** it is accepted as today.

---

### User Story 5 - Every field typed by an entity is linked to it in the graph (Priority: P2)

A developer reads the graph of an action whose Result holds an entity.

**Why this priority**: The graph shows which entities an action exposes; today it shows that only for projections.

**Independent Test**: Build the graph of an action whose Result has fields typed `CustomerCoreEntity`, `CustomerCoreEntity | None` and `list[CustomerCoreEntity]`.

**Acceptance Scenarios**:

1. **Given** those fields, **When** the graph is built, **Then** each field node has an `entity_schema` edge to `CustomerCoreEntity`, as a projection field has (case 7.1).

### Edge Cases

- A projection whose schema lists a field as optional and a value that omits it: the partial entity does not hold that field.
- A projection field in `| None`: `None` stays `None`.
- A projection listing a relation field: the value takes the relation's JSON form (#407) and is checked by the relation's type.
- A full entity whose field is outside the projection: that field is dropped, never sent.
- A dictionary value (an enum entity) in a field typed by its dictionary: it is never partial, so nothing changes for it.
- A projection given an entity of another class: refused.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A projection field MUST hold a partial entity of its class holding exactly the projection's fields present in the value, whether it is given a full entity, a partial entity or a dict, in every mode.
- **FR-002**: Each projected value MUST be checked by the projection's JSON Schema and by the type of the entity's own field.
- **FR-003**: A value missing a field the projection's schema requires MUST be refused with a message naming the field.
- **FR-004**: A projection's JSON form MUST be its fields only; a Python-mode dump MUST keep the entity, as for every other entity value since #407.
- **FR-005**: A projected entity MUST keep the dict-style reads entities already have (`value["id"]`).
- **FR-006**: Declaring a projection whose schema lists a property that is not a field of the entity MUST be refused, naming the property and the entity.
- **FR-007**: A field typed by an entity class (bare, `| None`, `list[...]`) MUST refuse a partial entity of that class, with a message that names what the entity holds and points to a projection.
- **FR-008**: Every `Params`/`Result` field typed by an entity (bare, `| None`, `list[...]`) MUST get an `entity_schema` edge to that entity in the graph, as a projection field does.
- **FR-009**: Every case (6.1–6.4, 7.1) MUST be a test that fails before the change and passes after it, with an adversarial break for each fix.
- **FR-010**: Every example, notebook, page and test that relied on a projection holding a dict MUST change in this work, and the example checks MUST pass.
- **FR-011**: The documentation (tutorial steps 17, 18 and 22) MUST describe the delivered behaviour, with explanations from #401 sections 4.6 and 4.7 and examples from runs.

### Key Entities

- **Projection**: a field declared with `Entity.schema(schema=...)`; it holds a partial entity of exactly its fields.
- **Field typed by an entity**: a field whose annotation is an entity class, `Entity | None` or `list[Entity]`; it holds full entities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All cases of #408 give their After output, and each gave its Before output on `main` before this work (re-measured on `f35ce11e8`).
- **SC-002**: 0 actions need to copy an entity's fields into a dict to return it through a projection.
- **SC-003**: 0 responses of a field typed by a bare entity omit a field its published schema requires.
- **SC-004**: A projected value costs at most about 13 µs on the machine of #406 (9.4 µs for the check, the rest for the partial entity); measured and reported, not asserted.
- **SC-005**: Every adversarial break of the change fails at least one test of this work.
- **SC-006**: The example checks and the closing check run pass with 0 remarks other than the two the constitution accepts.

## Assumptions

- No `Params` or `Result` in this repository holds a partial entity in a field typed by the bare entity today (#408); the closing check run confirms it.
- Code that reads a projection value as a dict by key keeps working through the entity's dict-style reads; code that relies on it being exactly a `dict` (`isinstance`, `==` with a dict) changes in this work.
- The projection's schema stays what OpenAPI and MCP publish for the field.

## Out of Scope

- The build check and round trip over every Result — #409.
- The cache — #410, #412, #413.
