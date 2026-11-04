# Feature Specification: A JSON Schema check is built once, in the draft it checks values with

**Feature Branch**: `feature/issue-406-schema-validator-once`

**Created**: 2026-11-04

**Status**: Draft

**Input**: Issue #406, "Entity as DTO 2/8: a JSON Schema check is built once, in the draft it checks values with", step 2 of 8 of #399, with its case 6.5 and its real Before outputs.

## Overview

Two kinds of field hold plain JSON that a strict **JSON Schema** checks: a `JsonSchemaValue` field (tutorial step 17) and an entity **projection**, `OrderCoreEntity.schema(schema={...})`, a partial view of an entity on a Params or Result field (steps 17 and 18).

Both check every value by handing the value and the schema to the JSON Schema library's one-call check. That call works out, on every value, which draft of JSON Schema the schema is written in, checks the schema itself against that draft, and only then checks the value — about 550 µs per value for a three-field object. The declaration checks the schema too, but always as Draft 7, while the values are checked as the draft the schema names in `$schema`, or the newest draft (2020-12) when it names none. A schema both drafts read differently is accepted when it is declared and then refused on every value with a schema error, which is not a validation error and escapes the framework's error handling.

After this change the draft is chosen once, when the field is declared, the same way the values are checked today; the schema is checked once, in that draft; the check of a value checks only the value, in about 10 µs; and the error a refused value reports is the one it reports today.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A schema is checked once, in the draft its values are checked with (Priority: P1)

A developer declares a `JsonSchemaValue` or a projection. A schema the values cannot be checked with is refused at declaration, not on the first value; a schema that names its draft in `$schema` is checked in that draft at declaration and on every value.

**Why this priority**: Today a schema accepted at declaration can make every value fail with a schema error that escapes Pydantic's error handling; the developer learns it at run time, on a request.

**Independent Test**: Declare a `JsonSchemaValue` with a Draft 7 tuple schema (`items` as a list), without and with `"$schema"` naming Draft 7, and check values against each.

**Acceptance Scenarios**:

1. **Given** the schema `{"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}` without `$schema`, **When** `JsonSchemaValue.define(name="Pair", schema=...)` runs, **Then** it raises `SchemaError: [{'type': 'string'}, {'type': 'integer'}] is not of type 'object', 'boolean'` at declaration; today the declaration is accepted and `PairResult(pair=["a", 1])` raises that `SchemaError` (case 6.5).
2. **Given** the same schema with `"$schema": "http://json-schema.org/draft-07/schema#"`, **When** it is declared and values are checked, **Then** the declaration is accepted, `["a", 1]` is accepted and `[1, "a"]` is refused with a validation error (case 6.5).
3. **Given** the same tuple schema in a projection `OrderCoreEntity.schema(schema=...)`, **When** it is declared, **Then** the outcome is the same as for `JsonSchemaValue`: one rule for both kinds of field.

---

### User Story 2 - A value check checks only the value (Priority: P1)

A developer returns a Result whose field is a projection or a `JsonSchemaValue`. Each value is checked against a check built once, so the field costs about as much as a plain Pydantic field.

**Why this priority**: A Result with a list of projected rows pays ~550 µs per row today; this is the most expensive per-value step of #399 (see its performance table) and steps 4 and 5 build on it.

**Independent Test**: Time `ProjectionResult(order=row)` and `AuditResult(audit=row)` for `row = {"id": "o1", "status": "paid", "total": 99.5}` with the three-field strict schema of #406.

**Acceptance Scenarios**:

1. **Given** a projection field with the three-field strict schema, **When** a valid row is checked, **Then** the check takes about 10 µs instead of ~550 µs (case 6.5).
2. **Given** a `JsonSchemaValue` field with the same schema, **When** a valid row is checked, **Then** the same holds.
3. **Given** many fields declared with schemas, **When** values are checked, **Then** no value check checks the schema again.

---

### User Story 3 - Values pass and fail exactly as today (Priority: P1)

A developer whose schemas name no draft and use no form the drafts read differently sees no change in what passes, what fails and what the error says.

**Why this priority**: The change is a speed and consistency fix; it must not change a single outcome of a schema written today.

**Independent Test**: Check the same valid and invalid values through both kinds of field before and after, and compare the outcomes and the messages.

**Acceptance Scenarios**:

1. **Given** the projection of #406 and the value `{"id": 1, "status": "paid", "secret": "x"}`, **When** it is checked, **Then** the error reads `OrderCoreEntity wire projection: 'total' is a required property`, as today: the reported error is chosen among all of the value's errors the way the one-call check chooses it.
2. **Given** a value with one error, **When** it is checked through a `JsonSchemaValue` field, **Then** its message is the one it is today.
3. **Given** every schema declared in this repository, **When** the repository's tests and examples run, **Then** every one passes as before: none names a draft or uses a form the drafts read differently.

### Edge Cases

- A schema that names a draft the library does not know: it is handled the way the one-call check handles it today — the newest draft is used, with the library's `DeprecationWarning` — but the warning comes once, at declaration, instead of on every value.
- A schema the chosen draft refuses: the declaration raises the JSON Schema library's schema error, as `JsonSchemaValue.define` does today for an invalid schema; the error is raised at declaration and never on a value.
- `JsonSchemaValue`'s own shape rules, raised as `ValueError` before the schema is checked: unchanged, and still raised first.
- A value with several errors: the one reported is the one the one-call check reports today.
- A projection and a `JsonSchemaValue` with the same schema: both build the check the same way, through one shared place, so they never disagree.
- A field declared but never used: building its check costs nothing on any value.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The draft a schema is checked in MUST be chosen once, when the field is declared, by the same rule the one-call check uses today: the draft named by the schema's `$schema`, or the newest draft when it names none or names one the library does not know.
- **FR-002**: The schema MUST be checked at declaration in that draft, for both `JsonSchemaValue.define()` and `BaseEntity.schema()`; a schema the draft refuses MUST raise the schema error at declaration.
- **FR-003**: Every value MUST be checked in the same draft the schema was checked in, by a check built once per declared field, and the value check MUST NOT check the schema again.
- **FR-004**: A value that passes or fails today MUST pass or fail the same way, for every schema that names no draft or names the newest one.
- **FR-005**: The error a refused value reports MUST be the one the one-call check reports today for the same value and schema, and it MUST keep today's wording and error types for both kinds of field (`OrderCoreEntity wire projection: …` for a projection).
- **FR-006**: `JsonSchemaValue` and projections MUST build their check through one shared place, so that the draft rule and the error choice are written once.
- **FR-007**: Case 6.5 MUST be a test of each of its parts — declaration refused without `$schema`, accepted with Draft 7, values checked in Draft 7, the error choice, and a value check that does not check the schema — that fails before the change and passes after it; an adversarial break of each part MUST fail its test.
- **FR-008**: The documentation (tutorial steps 17 and 18) MUST say when the check runs and which draft it uses, with explanations taken from #401 section 4.6 (case 6.5) and examples whose outputs come from runs of the code.

### Key Entities

- **Schema field**: a `JsonSchemaValue` field or a projection field; it holds plain JSON that a strict JSON Schema checks.
- **Draft**: the version of the JSON Schema standard a schema is read in, named by its `$schema` or the newest one.
- **Check**: what a declared schema field uses to check its values; built once, in the field's draft.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Checking one valid three-field row through a projection or a `JsonSchemaValue` field takes at most 20 µs on the machine that measured ~550 µs (target ~10 µs), a speed-up of at least 25 times. It is measured and reported with the phase, not asserted by a test; SC-003 is the test that proves its cause.
- **SC-002**: 0 schemas are accepted at declaration and then refused with a schema error on a value.
- **SC-003**: 0 value checks check the schema again.
- **SC-004**: For every refused value in the tests of both kinds of field, the reported message is the same before and after.
- **SC-005**: Every adversarial break of the change (the schema checked as Draft 7 again; the one-call check per value again; the first error instead of the best one) fails at least one test of this work.
- **SC-006**: The example checks and the closing check run pass with 0 remarks other than the two the constitution accepts.

## Assumptions

- No schema in the repository names a draft in `$schema` or uses a form Draft 7 and the newest draft read differently, so no declaration here changes its outcome; this is checked again during planning by searching the repository.
- The JSON Schema library's rule for choosing a draft and for choosing the reported error stays as it is in the version the repository pins; the work reuses that rule rather than writing its own.
- The timings are medians on one machine with Python 3.12, Pydantic 2.14.1 and jsonschema 4.26.0; the criterion is relative to the ~550 µs measured there.
- The partial entity a projection will hold (case 6.1) is #408, not this step; this step changes only how the schema is checked.
- Documentation and the changelog ship in the same pull request as the code.

## Out of Scope

- What a projection holds (a partial entity instead of a dict) and the graph link of an entity-typed field — #408.
- JSON forms of relations, dictionary references and lifecycles — #407.
- Any change to the strict-shape rules of `JsonSchemaValue`.
