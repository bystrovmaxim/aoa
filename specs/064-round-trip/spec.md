# Feature Specification: What goes out comes back in

**Feature Branch**: `feature/issue-409-round-trip`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #409, "Entity as DTO 5/8: what goes out comes back in (the build check and the round-trip tests)", step 5 of 8 of #399, after #407 and #408, with its cases 8.1 and 8.2 and their real Before outputs.

## Overview

After #407 and #408 every value an entity holds has a JSON form, and rule 2 of #399 promises that a Result read back from its own JSON has the same **observable state**: the same values; for every entity, the same loaded fields; for every relation, the same ids, the same loaded state and the same loaded entities in the same order; for a declared value (a status or a dictionary value), the same declared object.

Nothing checks that promise today. A Result may declare a field whose type has no JSON form at all; the graph builds and the action runs, and the failure appears only when something writes the Result as JSON — an adapter on a live request, or the cache of #410. And equality cannot see what rule 2 is about: a relation loaded with zero rows equals one never loaded.

After this change the graph build refuses a Params or Result without a JSON Schema and names the field; one comparison of observable state exists, the one the cache write of #410 will use; and tests read back every Result the examples build, every Result class of the demo and AOA's own value types, and compare them by that comparison.

## Clarifications

### Session 2026-11-04

The maintainer asked for the whole task without questions; the answers taken:

- Q: Which Results are "every Result of the examples"? → A: every Result an example builds when it runs. A class an example declares but never builds has no value to read back; its types are still covered by the build check of FR-001.
- Q: The demo's actions need a database to run; how is "every Result of the demo" read back? → A: each Result class of the demo is built from a sample generated from its own published JSON Schema, then read back.
- Q: Is a Params read back too? → A: no; the issue reads back Results. A Params is covered by the build check.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Result without a JSON form fails at start, not on a request (Priority: P1)

A developer declares a Result field of a plain Python class; the application refuses to start and names the field.

**Why this priority**: Today the mistake is found by a user's request or by the first cache write; at start it costs nothing.

**Independent Test**: Declare an action whose Result (or Params) has a field of a plain class; build the graph.

**Acceptance Scenarios**:

1. **Given** `OpaqueAction.Result` with `raw: Opaque`, **When** the graph is built, **Then** the build is refused, and the message names `OpaqueAction.Result.raw` (case 8.1).
2. **Given** the same field on Params, **When** the graph is built, **Then** the build is refused and names the Params field.
3. **Given** a field whose JSON Schema builds in validation mode but not in serialization mode, **When** the graph is built, **Then** it is refused as well.
4. **Given** every action of the repository's packages, examples and demo, **When** their graphs are built, **Then** none is refused.

---

### User Story 2 - One comparison says whether a read-back Result is the same (Priority: P1)

A test, and later the cache, compares a Result with its read-back copy and learns the first place they differ.

**Why this priority**: `==` cannot see a lost loaded state, so a broken read-back stays green; the cache of #410 needs this comparison to refuse such a Result.

**Independent Test**: Compare pairs of values that are equal by `==` but differ in observable state, and pairs that are the same.

**Acceptance Scenarios**:

1. **Given** `AssociationMany(ids=())` and `AssociationMany(ids=(), entities=(), entities_loaded=True)`, **When** compared, **Then** they differ, and the difference names the loaded state (case 8.2).
2. **Given** a One relation with and without its loaded entity, **Then** they differ.
3. **Given** a partial entity and the same entity with one more field loaded, **Then** they differ, naming the field.
4. **Given** two values of different types that are equal by `==` (a UUID and its string), **Then** they differ.
5. **Given** a declared status and an equal object that is not the declared one, **Then** they differ.
6. **Given** a value and itself, or a value and an independent copy with the same observable state, **Then** they are the same.

---

### User Story 3 - Every known Result reads back with the same observable state (Priority: P1)

The tests prove rule 2 on AOA's value types and on every Result the examples and the demo produce.

**Why this priority**: It is the promise #399 makes; the cache of #410 relies on it.

**Independent Test**: Read back `Result → JSON → Result` and compare by the comparison of User Story 2.

**Acceptance Scenarios**:

1. **Given** Results holding relations (One and Many, loaded, not loaded, loaded with zero rows), a lifecycle, a dictionary reference, a partial entity in a relation and a projection, **When** each is read back from its JSON, **Then** the observable state is the same.
2. **Given** every example, **When** it runs, **Then** every Result it builds reads back with the same observable state, and the run fails naming the Result and the difference otherwise.
3. **Given** every Result class of the demo, **When** a sample built from its JSON Schema is read back, **Then** the observable state is the same.
4. **Given** a relation that reads back as not loaded (the adversarial break), **When** the tests run, **Then** they fail.

### Edge Cases

- A Result whose JSON dump itself fails is reported as a failed read-back, naming the Result.
- A field declared `JsonSchemaValue` or a projection has a JSON Schema and passes the build check.
- An example that builds no Result passes; one that builds many has each read back.
- An example that builds a Result and then fails on purpose (a refused value it prints) still has its built Results read back.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The graph build MUST refuse a Params or Result class whose JSON Schema cannot be built in validation mode or in serialization mode.
- **FR-002**: The refusal MUST name the field, as `<Class qualname>.<field>`, and say how to fix it (`JsonSchemaValue`, or leaving it out); when no single field can be named, it MUST name the class.
- **FR-003**: There MUST be one comparison of observable state that returns the first difference with its path, or nothing when the two values are the same, covering: models (same class, same loaded fields, each compared), relations (class, ids, loaded state, loaded entities in order), declared values (the same object), lifecycles (the same declared current status), sequences and mappings item by item, and other values (same type and equal).
- **FR-004**: A test MUST read back AOA's value types (FR-003's kinds) from a Result's JSON and find no difference.
- **FR-005**: Running an example MUST read back every Result it builds and fail, naming the Result and the difference, when one is found.
- **FR-006**: A test MUST read back a sample of every Result class of the demo, built from its JSON Schema.
- **FR-007**: Equality (`==`) of every value type MUST NOT change.

### Key Entities

- **Observable state**: what rule 2 compares — the values, the loaded fields, the relations' ids, loaded state and loaded entities, the declared objects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Case 8.1 fails at graph build with a message naming `OpaqueAction.Result.raw`.
- **SC-002**: Case 8.2's pair is reported as different.
- **SC-003**: Every example and every demo Result class reads back with no difference; the adversarial break makes the tests fail.
- **SC-004**: The examples are not run a second time: the existing run of each example does the read-back.

## Assumptions

- The cache of #410 will call the comparison of FR-003 on its write; this step only provides it.
- A Result built with `model_construct()` skips validation and is not recorded by the example run.
