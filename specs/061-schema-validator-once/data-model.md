# Data model: A JSON Schema check is built once

One new internal type; two existing ones keep it.

## `JsonSchemaCheck` (new, `aoa/action_machine/system_core/json_schema_check.py`)

| Aspect | Rule |
| --- | --- |
| Built from | one JSON Schema dict |
| Draft | `validator_for(schema)`: `$schema`'s draft; the newest when absent or unknown (unknown: the library's `DeprecationWarning`, once) |
| On build | the schema is checked in that draft; a refused schema raises `jsonschema.SchemaError` |
| State | the schema it was built from and the validator instance, built once |
| `error_of(value)` | `best_match(iter_errors(value))`: the error `jsonschema.validate` would raise, or `None` |
| Equality, hashing | not used; the instance is unhashable |
| Pickle, deep copy | `__reduce__` rebuilds the check from its schema, so the result checks values the same way |
| Public | no; internal to `aoa-action-machine`, not exported from `system_core/__init__` |

## `JsonSchemaValue` type (from `JsonSchemaValue.define`)

| Aspect | Rule |
| --- | --- |
| Declaration | strict-shape rules (`ValueError`) first, then `JsonSchemaCheck(schema)` |
| Kept on the type | `_json_schema` (unchanged) and `_json_schema_check` |
| Value check | `error_of(value)`; an error → `ValueError(str(error))` |

## `EntitySchemaMarker` (from `BaseEntity.schema`)

| Aspect | Rule |
| --- | --- |
| Fields | `entity_cls`, `schema` (unchanged); `check: JsonSchemaCheck` with `init=False, compare=False, repr=False`, set in `__post_init__` |
| Declaration | creating the marker checks the schema; `BaseEntity.schema()` no longer calls `Draft7Validator.check_schema` |
| Value check | `error_of(value)`; an error → `ValueError("<Entity> wire projection: <message> (path: …)")` |
| Equality | unchanged: `entity_cls` and `schema` |
| Pickle, deep copy | still work, as today; the copy checks values the same way |
