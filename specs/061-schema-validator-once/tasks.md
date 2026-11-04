# Tasks: A JSON Schema check is built once, in the draft it checks values with

**Input**: `specs/061-schema-validator-once/` — spec.md, plan.md, research.md, data-model.md, contracts/schema-fields.md, quickstart.md

**Tests**: required — every part of case 6.5 is a test (FR-007), and every fix has an adversarial break.

**Commits**: one phase = one commit. After a phase only that phase's test files run; an adversarial break runs against them alone. Nothing is committed without the maintainer's instruction.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US3 from spec.md

---

## Phase 1: The shared check and its two users (US1, US2, US3) — one commit

**Goal**: a schema is checked once, at declaration, in the draft its values are checked with; a value check checks only the value and reports today's error (case 6.5).

**Independent test**: `uv run --extra dev pytest packages/aoa-action-machine/tests/action_machine/model/test_json_schema_check.py packages/aoa-action-machine/tests/action_machine/model/test_json_schema_value.py packages/aoa-action-machine/tests/action_machine/domain/test_entity_schema_pydantic.py packages/aoa-action-machine/tests/action_machine/domain/test_entity_schema_projection.py -q`

### Tests first

- [X] T001 [P] [US1] Write `packages/aoa-action-machine/tests/action_machine/model/test_json_schema_check.py` with tests through the public declarations: the Draft 7 tuple schema `{"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}` without `$schema` raises `jsonschema.SchemaError` with `[{'type': 'string'}, {'type': 'integer'}] is not of type 'object', 'boolean'` at `JsonSchemaValue.define(...)` and at `OrderCoreEntity.schema(schema=...)`; the same schema with `"$schema": "http://json-schema.org/draft-07/schema#"` is accepted through both, `["a", 1]` passes and `[1, "a"]` raises a Pydantic `ValidationError`; an unknown `$schema` emits exactly one `DeprecationWarning`, at declaration, and none while values are checked.
- [X] T002 [P] [US2] Add to the same file a test that counts calls of the validator class's `check_schema` while ten valid and ten invalid values are checked through a `JsonSchemaValue` field and a projection field with the three-field strict schema of #406, and requires zero (SC-003).
- [X] T003 [P] [US3] Add to the same file tests that the message is unchanged: `{"id": 1, "status": "paid", "secret": "x"}` through the projection raises `ValueError` reading `OrderCoreEntity wire projection: 'total' is a required property`, and through a `JsonSchemaValue` field the message equals `str(error)` of the error `jsonschema.validate` raises for the same value and schema; two `EntitySchemaMarker`s with the same entity and schema are equal, and the marker's `repr` names only `entity_cls` and `schema`; a marker after `pickle` and after `copy.deepcopy` is equal to the original and its field accepts and refuses the same two values as the original's; each user of the check (`entity_schema_marker`, `json_schema_value`) imports cleanly as the first module of a fresh process.
- [X] T004 Run T001–T003 and confirm each fails on today's code with the Before output of #406 (the tuple schema accepted at declaration; `check_schema` called on every value).

### Implementation

- [X] T005 [US1] Create `packages/aoa-action-machine/src/aoa/action_machine/system_core/json_schema_check.py` with `JsonSchemaCheck`: built from a schema, it picks the class with `jsonschema.validators.validator_for(schema)`, calls its `check_schema`, builds the validator once; `error_of(value)` returns `jsonschema.exceptions.best_match(validator.iter_errors(value))`; it keeps its schema and `__reduce__` rebuilds it from that schema (research R1). Module header, AI-CORE block and docstrings in the repository's style; not exported from `system_core/__init__`, which imports nothing, so `model/` and `domain/` import the module without a cycle.
- [X] T006 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/model/json_schema_value.py`: `define()` builds `JsonSchemaCheck(frozen_schema)` after the strict-shape rules, instead of `Draft7Validator.check_schema`, and stores it on the type as `_json_schema_check`; the core-schema validator calls `error_of` and raises `ValueError(str(error)) from error` (R2, R3). Update the module's data-flow notes and the AI-CORE block.
- [X] T007 [US1] In `packages/aoa-action-machine/src/aoa/action_machine/domain/entity_schema_marker.py`: add a `check` field (`init=False, compare=False, repr=False`) built in `__post_init__`; the core-schema validator calls `error_of` and raises today's `ValueError` with the `(path: …)` tail, chained from the error. In `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py`, `BaseEntity.schema()` drops `jsonschema.Draft7Validator.check_schema` and the `jsonschema` import if unused. Update the data-flow notes and AI-CORE blocks.
- [X] T008 Run the phase's tests (the files of the independent test): all pass. Measure the timing of the quickstart, step 3, and keep the numbers for the report.
- [X] T009 Adversarial breaks, one at a time, against the phase's test files only: check the schema as Draft 7 at declaration again → the tuple-schema tests of T001 fail; call `jsonschema.validate` per value again → the zero-count test of T002 fails; return the first error of `iter_errors` instead of `best_match` → the message test of T003 fails; remove `JsonSchemaCheck.__reduce__` → the pickle test of T003 fails; import `aoa.action_machine.model` from `entity_schema_marker.py` again → the import-order test fails; restore after each.

**Checkpoint**: show the diff; commit only on instruction.

---

## Phase 2: Versions — one commit

- [X] T010 Raise the version of `packages/aoa-action-machine` in its `pyproject.toml` and update `uv.lock`; run `uv run --extra dev graph-builder check` and rebuild the graph files only if it reports a change.

---

## Phase 3: The closing check run — one commit if it changes anything

- [X] T011 Run `bash scripts/run_checks_with_log.sh`, the example checks included, and take every remark to zero apart from the two the constitution accepts; this also confirms that no declared schema of the repository is refused as 2020-12 (research R4).

---

## Phase 4: Documentation — one commit

- [X] T012 [P] Update `docs/tutorials/step-17-schema-results.md` ("Where validation happens"): the schema is checked once, at declaration, in the draft named by its `$schema` or the newest one; each value is checked against that check; a schema its draft refuses is refused at declaration. Explanations from #401 section 4.6, case 6.5; a script and a notebook under `examples/step_17_schema_results/` showing the tuple schema refused, the Draft 7 schema accepted with its two values, and the unchanged message, with outputs from runs.
- [X] T013 [P] Update `docs/tutorials/step-18-complex-input.md` ("Arbitrary JSON by schema", "A partial entity on input"): the same rule for input fields, one sentence and a link to step 17's section; step 18 shows no new case, so it gets no example of its own.
- [X] T014 Run the example checks of the pages and examples T012–T013 touched.

---

## Phase 5: Changelog — one commit

- [X] T015 Write one article in `docs/CHANGELOG.md`, and its Russian version at the top of `docs/CHANGELOG.ru_draft.md`: what changed for a reader of schema fields, in plain words, without per-file detail.

---

## Dependencies

- Inside Phase 1, tests first; T004 must show the failures before T005.
- T006 and T007 depend on T005; they touch different files and could run in parallel, but both feed T008.
- Phases 2–5 follow Phase 1, in this order (constitution VI).

## Parallel opportunities

- T001, T002, T003 (one file, independent tests); T006 and T007 after T005; T012 and T013.

## Implementation strategy

Phase 1 alone is the whole behaviour change; Phases 2–5 are the tail every pull request carries. The pull request opens whole, after Phase 5.
