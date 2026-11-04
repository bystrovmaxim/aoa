# Research: A JSON Schema check is built once, in the draft it checks values with

Every decision below was measured on `main` at `4ff24deab`, Python 3.12, Pydantic 2.14.1, jsonschema 4.26.0. The probes live outside the repository; their outputs are quoted.

## R1. One shared check, built the way `jsonschema.validate` builds it

**Decision**: a new module `aoa/action_machine/system_core/json_schema_check.py` holds one class, `JsonSchemaCheck`. Built from a schema, it does the first three steps of `jsonschema.validate` once:

1. picks the validator class with `jsonschema.validators.validator_for(schema)` — the draft named by `$schema`, the newest draft (2020-12) when there is none, and the newest with the library's `DeprecationWarning` when `$schema` names a draft the library does not know;
2. checks the schema with that class (`check_schema`), raising `jsonschema.SchemaError` for a schema the draft refuses;
3. builds the validator instance.

Its one method, `error_of(value)`, returns `jsonschema.exceptions.best_match(validator.iter_errors(value))` — the error `jsonschema.validate` would raise, or `None`. The caller decides how to report it, so each kind of field keeps its own wording.

It keeps its schema and defines `__reduce__` as a rebuild from that schema, so `pickle` and `copy.deepcopy` give a working check: the validator instance itself cannot be pickled (`AttributeError: Can't get local object '_subresources_of_with_crazy_items.<locals>.subresources_of'`), while an `EntitySchemaMarker` pickles today and must keep doing so.

**Rationale**: `jsonschema.validate` is exactly `validator_for` → `check_schema` → instance → `best_match(iter_errors(...))` (read from its source in 4.26.0). Doing the first three once and the fourth per value changes nothing a value sees, by construction:

| Probe | Result |
| --- | --- |
| `jsonschema.validate(row, ORDER_WIRE)` | 576.5 µs |
| `best_match(validator.iter_errors(row))`, validator built once | 9.6 µs |
| the bad row `{"id": 1, "status": "paid", "secret": "x"}`: `(message, str(error))` before and after | equal; `'total' is a required property` |
| the tuple schema `PAIR` | `SchemaError: [{'type': 'string'}, {'type': 'integer'}] is not of type 'object', 'boolean'` when the check is built |
| `PAIR` with `"$schema"` naming Draft 7 | `Draft7Validator`; `["a", 1]` → no error; `[1, "a"]` → `'a' is not of type 'integer'` |
| `"$schema": "http://x/unknown"` | `Draft202012Validator`, one `DeprecationWarning` |

The module sits in `system_core/`, beside the other general helpers (`dot_path_navigator`, `type_introspection`), whose package `__init__` imports nothing. Both users import it without a cycle: in `model/` it would be imported by `domain/entity_schema_marker.py` through `model/__init__`, which loads the graph, which imports `entity_schema_marker` back (measured: `ImportError: cannot import name 'entity_schema_marker_from_annotated' from partially initialized module` when `domain` is imported first).

**Alternatives considered**:

- *`is_valid(value)` first, `best_match` only on failure* — measured 9.5 µs against 9.6 µs; no gain worth a second code path.
- *Pin Draft 7 everywhere* — refused: values are checked as 2020-12 today, so Draft 7 would silently stop checking 2020-12 keywords and change what passes (#401, question 10).
- *Pin 2020-12 and ignore `$schema`* — refused: a schema that names its draft would be checked in another one, which is the defect this step removes.
- *Keep `jsonschema.validate` and cache it* — the library has no per-schema cache; the check of the schema on every call is in the function itself.

## R2. When the check is built, and where it is kept

**Decision**: the check is built **at declaration** — in `JsonSchemaValue.define()` and when `EntitySchemaMarker` is created by `BaseEntity.schema()` — and kept on the declared thing; the Pydantic validator function closes over it.

- `JsonSchemaValue.define()` builds `JsonSchemaCheck(frozen_schema)` after its strict-shape rules (which still raise `ValueError` first) and stores it on the new type as `_json_schema_check`, next to `_json_schema`.
- `EntitySchemaMarker` builds it in `__post_init__` and keeps it in a field declared with `init=False, compare=False, repr=False`, so equality and `repr` of the marker stay `entity_cls` + `schema`. `BaseEntity.schema()` stops calling `Draft7Validator.check_schema`; creating the marker checks the schema.
- `__get_pydantic_core_schema__` of each reads the stored check; the per-value function calls `error_of` and raises `ValueError` with today's wording.

**Rationale**: the declaration is where the schema must be checked anyway (FR-002), and it runs once per declared field, while Pydantic may build a field's core schema more than once (once per model that uses the type). Building there is the strongest form of "once" and keeps the draft rule in one place. The validator instance is unhashable (`TypeError: unhashable type: 'Draft202012Validator'`), so the marker field must stay out of `__eq__`/`__hash__`; the marker is already unhashable through its `schema` dict, so nothing that works today depends on hashing it. The marker pickles today; through the check's `__reduce__` (R1) it still does, and so does `copy.deepcopy`.

The issue's wording "built once, when Pydantic builds the field's schema" is met more strictly: the check is built before that and Pydantic reuses it.

**Alternatives considered**:

- *Build in `__get_pydantic_core_schema__`* — refused: the schema would be checked twice (declaration and core-schema build) and the class chosen twice; the check would be built again for every model using the type.
- *A module-level cache keyed by the schema* — refused: schemas are dicts (unhashable), and a cache adds state the declaration already owns.

## R3. Error types and wording stay as they are

**Decision**:

- Projection: `ValueError(f"{entity_cls.__name__} wire projection: {error.message}{tail}")` with the same `(path: …)` tail built from `error.absolute_path`, chained `from error`.
- `JsonSchemaValue`: `ValueError(str(error))`, chained `from error`.
- A schema error stays `jsonschema.SchemaError`, now raised at declaration.

**Rationale**: these are today's two `except jsonschema.ValidationError` blocks with `exc` replaced by the returned error; the existing tests that match `"wire projection"` keep passing, and FR-005 holds by construction because the error is the one `jsonschema.validate` raises today.

## R4. What in the repository could change outcome

**Decision**: nothing in the repository changes outcome; the closing check run confirms it.

| Search | Result |
| --- | --- |
| `"$schema"` in schemas (packages, examples, docs, tests) | none |
| `"items": [` (tuple form) in schemas | none (four hits are data, not schemas) |
| `JsonSchemaValue.define(` call sites | 36 |
| `.schema(schema=` call sites | 23 |
| tests asserting on the message | `test_entity_schema_pydantic.py` (`match="wire projection"`, twice) |
| tests importing `Draft7Validator` / `check_schema` | none; the graph tests build their own `Draft202012Validator` for `GRAPH_JSON_SCHEMA`, unrelated |

Every declared schema is now checked as 2020-12 at declaration instead of Draft 7. A schema valid in Draft 7 but not in 2020-12 would now fail at import; one that is used on any value already fails today on that value, so only a declared-and-never-used schema could newly fail. The closing check run imports every package, example and test, which is that check.

## R5. Timings after

**Decision**: the tests prove the cause, not the clock. A phase test counts calls of the validator class's `check_schema` while values are checked through each kind of field and requires zero (SC-003); the timing of SC-001 is measured in the quickstart and reported with the phase, as a ratio against `jsonschema.validate` on the same row in the same process.

**Rationale**: a timing assertion flickers on a loaded CI machine; the count is deterministic and is exactly what made the check slow. Prototype: 576.5 µs → 9.6 µs, 60 times, far above the 25 times of SC-001.
