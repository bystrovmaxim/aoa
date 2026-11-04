# Implementation Plan: A JSON Schema check is built once, in the draft it checks values with

**Branch**: `feature/issue-406-schema-validator-once` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/061-schema-validator-once/spec.md`; issue #406, step 2 of 8 of #399.

## Summary

One internal class, `JsonSchemaCheck`, does once what `jsonschema.validate` does on every call: it picks the validator class from the schema's `$schema` (the newest draft without it), checks the schema in that draft, and builds the validator; per value it returns the error `best_match` picks (R1). `JsonSchemaValue.define()` and `EntitySchemaMarker` (created by `BaseEntity.schema()`) build it at declaration and their Pydantic validators close over it (R2), keeping today's error types and wording (R3). A value check drops from ~550 µs to ~10 µs; a schema its own draft refuses is refused at declaration instead of on every value.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14)

**Primary Dependencies**: Pydantic 2.14, jsonschema 4.26

**Storage**: N/A

**Testing**: pytest, per package

**Target Platform**: library

**Project Type**: library (monorepo of packages)

**Performance Goals**: a value check of a three-field strict schema at least 25 times faster than today (~550 µs → ~10 µs)

**Constraints**: public signatures unchanged; every value passes or fails as today and reports the same message (FR-004, FR-005)

**Scale/Scope**: one new module (`system_core/json_schema_check.py`), three changed (`model/json_schema_value.py`, `domain/entity_schema_marker.py`, `domain/entity.py`), their tests, two tutorial pages

## Constitution Check

| Principle | How this plan meets it |
| --- | --- |
| I. The maintainer decides | No commit, push or pull request without an instruction; every phase ends with a diff to show |
| II. English in code and history | All code, docstrings, commits and the spec in English; only `tasks.ru_draft.md` is Russian, and it is not committed |
| III–V. Headers, AI-CORE blocks, docstrings | The new module gets its header and AI-CORE block; the three touched modules update their data-flow notes (`jsonschema.validate` → the shared check) and AI-CORE blocks |
| VI. Check run, documentation, changelog last | Phases 3–5 are exactly these three, in this order; examples run (the example checks) |
| Check run | After each phase only that phase's tests run; the closing run before the pull request, CI's on it, `scripts/check_before_pr.sh` for the browsers |

No violation; nothing in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/061-schema-validator-once/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/schema-fields.md
├── checklists/requirements.md
└── tasks.md            (/speckit-tasks)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/system_core/json_schema_check.py      # new: the shared check
├── src/aoa/action_machine/model/json_schema_value.py      # uses it
├── src/aoa/action_machine/domain/entity_schema_marker.py  # uses it
├── src/aoa/action_machine/domain/entity.py                # drops the Draft 7 check
└── tests/action_machine/{model,domain}/                   # the tests of case 6.5
examples/step_17_schema_results/, examples/step_18_complex_input/   # phase 4, as needed
docs/tutorials/step-17-schema-results.md, step-18-complex-input.md
```

**Structure Decision**: the shared check lives in `system_core/`, whose package imports nothing, so `model/` and `domain/` both import it without a cycle (R1).

## Phases

One phase = one commit.

1. **The shared check and its two users** (case 6.5). `JsonSchemaCheck` (R1); `JsonSchemaValue.define()` and `EntitySchemaMarker` build it at declaration and use it per value (R2, R3); `BaseEntity.schema()` drops `Draft7Validator.check_schema`. Tests: the tuple schema refused at declaration through both kinds of field; the same schema with Draft 7 accepted, `["a", 1]` passing and `[1, "a"]` refused; the message of `{"id": 1, "status": "paid", "secret": "x"}` unchanged for both; zero `check_schema` calls while values are checked; an unknown `$schema` warning once, at declaration; marker equality unchanged; a marker after `pickle` and `deepcopy` checks values the same way. Adversarial: Draft 7 at declaration again; `jsonschema.validate` per value again; the first error instead of `best_match`; `JsonSchemaCheck.__reduce__` removed. Timing reported as in the quickstart.
2. **Versions** — raise the version of each level that changed (`aoa-action-machine`) and rebuild the graph files if they change.
3. **The closing check run**, taken to zero, the example checks included; it also confirms no declared schema of the repository is refused as 2020-12 (R4).
4. **Documentation** — tutorial steps 17 and 18 (step 18 by one sentence and a link, no example of its own) say when the check runs (once at declaration for the schema, per value for the value) and which draft it uses; explanations from #401 section 4.6, case 6.5; examples, as a script and a notebook, from runs.
5. **Changelog** — one article.

## Complexity Tracking

None.
