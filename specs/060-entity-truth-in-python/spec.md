# Feature Specification: An entity tells the truth in Python

**Feature Branch**: `feature/issue-405-entity-truth-in-python`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #405, "Entity as DTO 1/8: an entity tells the truth in Python (relation containers, partial)", step 1 of 8 of #399, with its cases 1.1–2.3 and their real Before outputs.

## Overview

An entity can say something untrue in Python before any JSON is involved, in two ways.

A **relation container** (`AssociationOne`, `CompositeMany` and the four others) forwards every name it does not have to the entity it holds, so that `order.customer.name` reads the customer's name. It forwards Python's and Pydantic's own protocol names too. Pydantic then serializes a loaded container as if it were the entity inside it, and Python copies it as the entity: `model_dump(mode="json")` of a loaded relation gives `{}`, `model_dump()` of an entity with a dictionary reference raises `KeyError: 'code'` (in the LangGraph node binding as well), and `copy.deepcopy` of a loaded relation returns the entity instead of the container. A container that is copied any other way, or pickled, fails because it is frozen.

A **partial entity** (`OrderCoreEntity.partial(id="o1")`) promises that a field it did not load cannot be read. Today it fills in the default of every unloaded field and runs every default factory, so an unloaded field with a default reads as that default and goes out in a dump, and a factory that depends on a missing field crashes `partial()` itself. A copy made with `model_copy(update=...)` reports a field it holds as not loaded.

After this change a container never passes itself off as its entity, copies and pickles as a container, and `order.customer.name` keeps working; a partial entity holds only what was loaded, reads nothing it did not load, and reports what it holds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Serializing an entity with relations tells the truth (Priority: P1)

A developer dumps an entity that holds relations, or a Result that holds such an entity, and gets the relation as a container — never an empty object or a crash.

**Why this priority**: Today the failure is silent (`{}`) or a crash in code that never asked for JSON (`model_dump()`, LangGraph).

**Independent Test**: Dump an entity with a loaded structural relation and an entity with a dictionary reference, in both modes, and run a LangGraph node whose Result holds such an entity.

**Acceptance Scenarios**:

1. **Given** an entity whose relation holds a loaded entity, **When** it is dumped in JSON mode, **Then** the dump never contains `{}` for that relation: until #407 gives relations a JSON form, the dump fails with `PydanticSerializationError: Unable to serialize unknown type` naming the container, as it already does for an unloaded one (case 1.1).
2. **Given** an entity with a dictionary reference, **When** `model_dump()` runs in Python mode, **Then** it returns the container, `{'primary': CompositeOne(id='eur', loaded)}` (case 1.2).
3. **Given** a LangGraph node whose action returns a Result holding that entity, **When** the node runs, **Then** it returns `{'price': {'id': 'p1', 'currency': CompositeOne(id='eur', loaded)}}` (case 1.3).
4. **Given** a loaded relation, **When** code reads `order.customer.name`, **Then** it gets the customer's name, as today.

---

### User Story 2 - Copying an entity keeps its relations (Priority: P1)

A developer copies or pickles an entity, or a relation, and gets the same kind of object back.

**Why this priority**: A deep copy of an order silently replaces its relation with the related entity; any other copy of a container, and every pickle, crashes.

**Independent Test**: Copy and pickle a loaded and an unloaded relation, and deep-copy an entity that holds one.

**Acceptance Scenarios**:

1. **Given** a loaded relation, **When** it is deep-copied, **Then** the copy is a container of the same class with the same id and a copy of the entity; today it is the entity (case 1.4).
2. **Given** an entity holding a loaded relation, **When** `model_copy(deep=True)` runs, **Then** the copy's field holds a container; today it holds the entity (case 1.4).
3. **Given** a loaded or an unloaded relation, **When** it is shallow-copied, deep-copied or pickled and unpickled, **Then** the result is an equal container that is still frozen; today it raises `AttributeError: AssociationOne is frozen` (case 1.5).

---

### User Story 3 - A partial entity never reads a field it did not load (Priority: P1)

A developer builds a partial entity and reads, dumps or inspects it. A field it did not load raises `FieldNotLoadedError` and never appears in a dump, and building the partial entity runs no code of a field it did not load.

**Why this priority**: The partial entity contradicts itself today: `is_field_loaded` says False while the field reads as its default.

**Independent Test**: Build a partial entity of a class with a default, a default factory that depends on a missing field and a default factory that counts its calls, then read and dump it.

**Acceptance Scenarios**:

1. **Given** a class with `currency: str = "RUB"`, **When** `partial(id="o1")` is built, **Then** `currency` raises `FieldNotLoadedError` and `model_dump(mode="json")` is `{'id': 'o1'}` (case 2.1).
2. **Given** a class with a default factory that reads another field, **When** `partial()` is built with no fields, **Then** it returns an instance with nothing loaded; today it raises `KeyError: 'id'` (case 2.3).
3. **Given** a default factory that counts its calls, **When** `partial(id="o1")` is built, **Then** the factory of the unloaded field runs zero times (case 2.3).

---

### User Story 4 - A changed copy of a partial entity knows what it holds (Priority: P2)

A developer updates a partial entity with `model_copy(update=...)` and the copy reports every field it holds as loaded.

**Why this priority**: The copy is readable but says it is not loaded, so code that checks before reading takes the wrong branch.

**Independent Test**: Copy a partial entity with an update and ask which fields are loaded.

**Acceptance Scenarios**:

1. **Given** `p = partial(id="o1")`, **When** `c = p.model_copy(update={"total": 2.0})`, **Then** `c.is_field_loaded("total")` is True and `c.total` is 2.0 (case 2.2).
2. **Given** the same copy, **When** a field that is still not loaded is read, **Then** it raises `FieldNotLoadedError`.

---

### Edge Cases

- A name that starts with a single underscore, or any ordinary name, is still forwarded to the loaded entity; only names that start and end with `__` are not.
- A protocol name the container itself does not define (`__foo__`) raises `AttributeError`, never `RelationNotLoadedError` and never the entity's attribute.
- An unloaded container still raises `RelationNotLoadedError` for an ordinary name.
- A partial entity built with every field behaves like a full one: every field is loaded and readable.
- Equality does not change: a partial entity built with every field equals the full entity with the same values, as it does today; a relation's equality still compares its class and ids.
- A full entity is not affected: its defaults and default factories apply as today, and every field reports loaded.
- The public API of a partial entity stays: `partial(**fields)`, `is_field_loaded`, `get_field_value`, `get_primary_key`, `get_scalar_fields` and the other getters keep their signatures.
- Code in the repository that read a default from an unloaded field of a partial entity now gets `FieldNotLoadedError`; every such place is found and changed in this work.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A relation container MUST NOT forward a name that starts and ends with `__` to the entity it holds; every other name it does not have MUST still be forwarded, so `order.customer.name` reads the entity's field.
- **FR-002**: Dumping an entity with a loaded structural relation MUST never produce `{}` for the relation; until #407, the JSON-mode dump fails with Pydantic's serialization error naming the container.
- **FR-003**: `model_dump()` in Python mode of an entity with a dictionary reference MUST return the reference's container, and the LangGraph node binding MUST return a node's Result fields without error for such an entity.
- **FR-004**: Deep-copying a relation container, directly or through `model_copy(deep=True)` of the entity holding it, MUST return a container of the same class with the same ids and a copy of the loaded entity.
- **FR-005**: A relation container MUST support `copy.copy`, `copy.deepcopy` and `pickle`, loaded or not, and the result MUST be an equal, frozen container.
- **FR-006**: `partial(**fields)` MUST set only the given fields: no default and no default factory of a field it was not given runs.
- **FR-007**: Reading, getting or dumping a field a partial entity did not load MUST behave as for a field with no default: reading raises `FieldNotLoadedError`, and the field is absent from `model_dump()` in both modes.
- **FR-008**: After `model_copy(update=...)` of a partial entity, every updated field MUST report loaded, and every field that was not loaded and not updated MUST still raise `FieldNotLoadedError`.
- **FR-009**: Equality of entities and of relation containers MUST stay as it is today.
- **FR-010**: Every case of the issue (1.1–1.5, 2.1–2.3) MUST be a test that fails before the change and passes after it, and an adversarial break of each fix MUST fail its test.
- **FR-011**: Every example, notebook, page and test of the repository that relied on the old behaviour MUST be changed in this work, and the example checks MUST pass.
- **FR-012**: The documentation (tutorial steps 22 and 24, the how-to page on dictionary references) MUST describe the delivered behaviour, with explanations taken from #401 sections 4.1 and 4.2 and examples whose outputs come from runs of the code.

### Key Entities

- **Relation container**: one of the six classes that link an entity to another one; holds the id(s) always and the loaded entity or entities sometimes.
- **Partial entity**: an entity built with `partial(**fields)`, holding only the fields it was given.
- **Loaded field**: a field a partial entity was given, or was given later through `model_copy(update=...)`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 8 cases (1.1–1.5, 2.1–2.3) give their After output, and each of them gave its Before output on `main` at `9e893a2cb`.
- **SC-002**: 0 dumps of a loaded relation produce `{}`, and 0 copies of an entity replace a relation with its entity.
- **SC-003**: A partial entity runs 0 default factories of fields it was not given.
- **SC-004**: Every adversarial break of the two fixes (forwarding dunder names again; filling defaults again) fails at least one test of this work, and no other test of the work.
- **SC-005**: The example checks and the closing check run pass with 0 remarks other than the two the constitution accepts.

## Assumptions

- The JSON form of relations is #407's work; here a loaded relation in JSON mode fails loudly instead of silently giving `{}`.
- Equality keeps today's semantics (FR-009); how the partial state is kept without changing equality is decided in the plan's research, and the wording of #405's phase 2 follows that decision.
- The LangGraph node binding's own code does not change; it works once `model_dump()` does.
- Python 3.12 and 3.14 are both supported, as the rest of the repository is.
