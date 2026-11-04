# Feature Specification: Every entity value has one JSON form

**Feature Branch**: `feature/issue-407-entity-json-forms`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #407, "Entity as DTO 3/8: every entity value has one JSON form (relations, dictionary references, lifecycle)", step 3 of 8 of #399, with its cases 3.1–3.5, 4.1–4.5, 5.1–5.4 and 10.1 and their real Before outputs.

## Overview

An entity can be a field of `Params` and `Result` only if every value it holds can go out as JSON and come back in. Three kinds of value cannot today:

- a **relation** to an ordinary entity (`AssociationOne`, `CompositeMany` and the four others) has no JSON form and no JSON Schema, so dumping or publishing an entity that holds one fails;
- a **dictionary reference** (a relation whose target is a closed catalogue, such as a currency) accepts its id object only from raw JSON, which FastAPI and MCP never use, and does not accept back the reference it writes;
- a **lifecycle** (the current status of an entity's state machine) has no JSON form and no JSON Schema, so one such Result breaks the OpenAPI document of the whole application.

After this change each of the three has one JSON form, written by every path and read back by the same validator whether the value comes from JSON, from a dict or from code; the JSON Schema that FastAPI and MCP publish describes it; and FastAPI, MCP and LangGraph carry entities in `Params` and `Result` end to end.

## Clarifications

### Session 2026-11-04

The maintainer asked for the whole task without questions; these are the answers taken, each consistent with #399's rules and #405–#406.

- Q: What does a Python-mode `model_dump()` return for a relation, a dictionary reference and a lifecycle? → A: the value itself (the container, the lifecycle), as today; only JSON mode writes the JSON form. #405 keeps the container in Python mode and its documentation says so.
- Q: Is a dict accepted in code (Python mode) for a relation and a lifecycle, not only for a dictionary reference? → A: yes. Rule 1 of #399 is one validator for every path, and FastAPI and MCP validate dicts in Python mode.
- Q: What does a missing field inside `"entity"` / `"entities"` mean? → A: not loaded: the target is read as a partial entity holding the fields present (#405). A full entity's JSON has every field, so it reads back equal to the full entity.
- Q: What JSON Schema describes `"entity"`? → A: the target entity's own schema, by reference, so a recursive pair stays finite. A partial target may omit fields that schema marks required; the published schema describes a full target, and #408's projections are the tool for a declared subset.
- Q: Where is a dictionary value's reference kept once computed? → A: on the dictionary class, by code, not in a private attribute of the value: a private attribute of an entity cannot be read today (#414). Every reader gets a new dict.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An entity with relations goes out as JSON and comes back (Priority: P1)

A developer returns an entity that holds relations to other entities, and reads the same JSON back.

**Why this priority**: Without it no entity with a relation can be a Result field; this is the core of #399.

**Independent Test**: Dump, publish the schema of, and read back an order with an unloaded customer, unloaded lines, loaded lines with zero rows, a loaded partial customer, and the recursive pair customer ↔ orders; UUID ids included.

**Acceptance Scenarios**:

1. **Given** an order with an unloaded `AssociationOne` and an unloaded `CompositeMany`, **When** it is dumped in JSON mode, **Then** they are `{"id": "c1"}` and `{"ids": ["l1", "l2"]}` (case 3.1); a loaded One is `{"id": "c1", "entity": {…}}` (case 1.1 of #405), a loaded Many `{"ids": [...], "entities": [...]}`.
2. **Given** that entity class, **When** its JSON Schema is built, **Then** it builds; `customer` is an object with a required `id` and an optional `entity`, closed with `"additionalProperties": false` (case 3.2); a pair of entities that point at each other builds a finite schema.
3. **Given** the JSON of 3.1, **When** it is read back, **Then** `customer.id == "c1"`, `customer.is_loaded is False`, `lines.ids == ("l1",)`, `lines.is_loaded is False` (case 3.3).
4. **Given** a Many loaded with zero rows, **When** it goes out and back, **Then** it is `{"ids": [], "entities": []}` and comes back loaded; `{"ids": []}` comes back not loaded (case 3.4).
5. **Given** a customer whose `id` is a `UUID`, **When** an order holds `AssociationOne(id="00000000-…-0001")`, **Then** the id is a `UUID` in Python and after reading back; an id that is not a UUID raises a validation error at `customer.id`; a target without an `id` field takes only `str` or `int` ids (case 3.5).

---

### User Story 2 - A dictionary reference is accepted on every path (Priority: P1)

A developer sends a currency reference through FastAPI or MCP, or builds Params from a dict, and reads back the reference an entity writes.

**Why this priority**: Today a dictionary reference can be sent only through raw JSON, which no adapter uses.

**Independent Test**: Send `{"currency": {"id": "eur"}}` through FastAPI, MCP and `model_validate` of a dict; read back `model_dump_json()` of an entity with references, for a to-one and a to-many container.

**Acceptance Scenarios**:

1. **Given** a route taking `PriceParams`, **When** FastAPI receives `{"currency": {"id": "eur"}}`, **Then** it answers `200` (case 4.1).
2. **Given** an MCP tool taking `PriceParams`, **When** its input is `{"currency": {"id": "eur"}}`, **Then** it validates to `CompositeOne(id='eur', loaded)` (case 4.2).
3. **Given** a dict `{"currency": {"id": "eur"}}` in code, **When** `PriceParams.model_validate` runs, **Then** it is accepted; `PriceParams(currency=CompositeOne(id="eur"))` works as today (case 4.3).
4. **Given** the reference an entity writes, `{"code": "eur", "display_name": "Euro", "properties": {...}}`, **When** it is read back, **Then** it selects the declared value by `code`, taking label and properties from the catalogue: `{"code": "eur", "display_name": "Dollar"}` reads as `EUR` labelled `Euro`; the published input schema lists both the id object and the reference object (case 4.4). A to-many container takes an array of either, `[]` included.
5. **Given** an entity with ten to-one references, **When** it is dumped to JSON, **Then** the JSON is the same byte for byte and each reference costs a fraction of today's 2.53 µs, because each declared value's reference is computed once (case 4.5).

---

### User Story 3 - A lifecycle goes out as JSON and comes back (Priority: P1)

A developer returns an entity with a lifecycle from a FastAPI route and reads it back.

**Why this priority**: One such Result breaks the OpenAPI document of the whole application today.

**Independent Test**: Serve a Result holding an entity with `OrderLifecycle` through FastAPI, build `app.openapi()`, and read the lifecycle back from a dict.

**Acceptance Scenarios**:

1. **Given** a route returning such an entity, **When** it is called and the OpenAPI document is built, **Then** the response is `200` with `"lifecycle": {"code": "draft", "display_name": "Draft", "properties": {"receipt_required": false}}`, and the document builds with `lifecycle.code` an enum of the template's states (case 5.1).
2. **Given** `{"id": "o1", "lifecycle": {"code": "draft"}}`, **When** it is validated, **Then** `lifecycle == OrderLifecycle("draft")`; `{"code": "shipped"}` is refused naming `['draft', 'paid']`; a bare string is refused (case 5.2).
3. **Given** a status with its own fields, **When** the lifecycle goes out, **Then** they are under `properties`; the status's own `model_dump()` and the graph export of statuses do not change (case 5.3).
4. **Given** a lifecycle written while a declared status's list was `[]`, **When** that list is changed and the lifecycle is read back, **Then** `current_status is OrderStateEntity.PAID` and its list is the changed one (case 5.4).

---

### User Story 4 - The adapters carry entities end to end (Priority: P2)

A developer exposes actions whose Params and Result hold entities through FastAPI, MCP and LangGraph.

**Why this priority**: Proves the three forms on every real path; the adapters' code does not change.

**Independent Test**: End-to-end tests per adapter with entities holding a relation, a dictionary reference and a lifecycle in Params and Result, and a field with a serialization alias.

**Acceptance Scenarios**:

1. **Given** each adapter, **When** an action with entity fields runs through it, **Then** the request validates and the response carries the JSON forms above (cases 1.3, 4.1, 4.2, 5.1).
2. **Given** a Result field `item_id` with `serialization_alias="itemId"`, **When** it goes out, **Then** FastAPI writes `itemId`, MCP and `model_dump_json()` write `item_id`, and the tests pin each name (case 10.1).

### Edge Cases

- A container of another class in a field (an `AssociationOne` where a `CompositeOne` is declared) is refused, as today.
- An unknown key beside `id`/`entity` or `ids`/`entities` is refused.
- An `"entities"` list whose length differs from `"ids"`: refused, as the container's constructor refuses a contradiction.
- A field inside `"entity"` that the target does not declare: refused.
- A relation whose target class is not yet defined when the field is declared (a recursive pair): the schema resolves once both classes exist.
- A dictionary reference with only `display_name`, no `code`: refused.
- A lifecycle class with no template: a dict is refused with a message naming the missing template.
- A nullable relation or lifecycle field (`… | None`): `null` goes out and comes back as `None`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A relation to an ordinary entity MUST write, in JSON mode, `{"id"}` / `{"id", "entity"}` for One and `{"ids"}` / `{"ids", "entities"}` for Many, where the presence of `"entity"` / `"entities"` means loaded; Python mode MUST keep the container.
- **FR-002**: The same validator MUST read that form from JSON, from a dict and from a container instance, returning a new container of the declared class; a missing field inside `"entity"` / `"entities"` MUST mean not loaded.
- **FR-003**: The ids of a relation MUST be validated by the declared type of the target's `id` field, in every mode, with errors located at the id; a target without `id` MUST take only `str` or `int` ids.
- **FR-004**: The JSON Schema of an entity holding relations MUST build, closed (`additionalProperties: false`), with the target described by reference so that recursive pairs are finite.
- **FR-005**: A dictionary reference MUST accept, in every mode, the container, the id object `{"id": code}` and the reference object (`code` required, `display_name` and `properties` ignored in favour of the catalogue), and for Many an array of those; the published input schema MUST list the id object and the reference object.
- **FR-006**: Each declared dictionary value's reference MUST be computed once, when the dictionary declares its values, and every serializer of a dictionary value MUST return a new dict built from it, with JSON byte-identical to today's.
- **FR-007**: A lifecycle field MUST write `{"code", "display_name", "properties"}` of its current status in JSON mode and keep the lifecycle in Python mode; it MUST read `{"code"}` (other keys ignored) in every mode, choosing the declared status of the template; it MUST refuse an unknown code naming the template's states, and a bare string.
- **FR-008**: The JSON Schema of a lifecycle field MUST build, with `code` an enum of the template's state codes.
- **FR-009**: FastAPI, MCP and LangGraph MUST carry entities in `Params` and `Result` end to end without changes to their code; their tests MUST pin the field names each adapter writes for a field with a serialization alias.
- **FR-010**: Every case (3.1–3.5, 4.1–4.5, 5.1–5.4, 10.1) MUST be a test that fails before the change and passes after it, and an adversarial break of each fix MUST fail its test.
- **FR-011**: Every example, notebook, page and test that relied on the old behaviour MUST be changed in this work, and the example checks MUST pass.
- **FR-012**: The documentation (tutorial steps 22–25, the how-to pages on dictionary references and on explicit entity fields) MUST describe the delivered forms, with explanations from #401 sections 4.3, 4.4, 4.5 and 4.10 and examples whose outputs come from runs.

### Key Entities

- **JSON form**: the one shape a value takes in JSON, written by every path and read back by the same validator.
- **Relation form**: `{"id"[, "entity"]}` / `{"ids"[, "entities"]}`.
- **Reference**: `{"code", "display_name", "properties"}` — a declared dictionary value or a lifecycle status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All cases of #407 give their After output, and each gave its Before output on `main` before this work.
- **SC-002**: An entity holding relations, dictionary references and a lifecycle survives `JSON out → JSON in` with the same observable state (ids with their types, loaded state, the selected declared values) in 100% of the tested shapes.
- **SC-003**: 0 OpenAPI documents fail to build because of an entity value.
- **SC-004**: Dumping ten dictionary references to JSON is at least 4 times faster than today's 25.3 µs on the same machine, with byte-identical JSON; measured and reported, not asserted.
- **SC-005**: Every adversarial break of the change fails at least one test of this work.
- **SC-006**: The example checks and the closing check run pass with 0 remarks other than the two the constitution accepts.

## Assumptions

- Python 3.12, Pydantic 2.14 with pydantic-core 2.50; the core-schema features used (a plain validator with a published input schema, a serializer with a return schema, typed dicts) are present in that version (verified by prototype).
- The adapters validate requests in Pydantic's Python mode on parsed dicts and serialize responses in JSON mode; their code is not changed (#407 section 10).
- Ids in today's tests and examples are mostly strings matching `str` ids; where a test passes ids of another type than the target's `id`, the test changes (FR-011).
- Field names on each path (serialization aliases) are out of scope (case 10.1 pins them only).

## Out of Scope

- Projections holding entities and the graph link of entity-typed fields — #408.
- The build check and round-trip tests over every Result — #409.
- The cache — #410, #412, #413.
- Reading an entity's private attributes — #414.
