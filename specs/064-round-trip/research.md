# Research: What goes out comes back in

Measured on `main` at `fdae3dfec` (after #405–#408), Python 3.12, Pydantic 2.14.

## Before, re-measured

| Case | Output |
| --- | --- |
| 8.1 a Result field `raw: Opaque` | declared (BaseResult allows arbitrary types); `model_dump_json()` → `PydanticSerializationError: Unable to serialize unknown type: <class '__main__.Opaque'>`; `model_json_schema()` in both modes → `PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.IsInstanceSchema (<class '__main__.Opaque'>)` |
| 8.2 `AssociationMany(ids=()) == AssociationMany(ids=(), entities=(), entities_loaded=True)` | `True`, while `is_loaded` is `False` and `True` |

## R1. Where the build check runs

**Decision**: a new validator `graph/validators/json_form_validator.py`, `validate_json_forms(nodes)`, called by `NodeGraphCoordinator.build` beside `validate_emits_vocabulary`. For each node whose object is a `BaseParams` or `BaseResult` subclass it builds `model_json_schema(mode=...)` in validation and serialization mode. On failure it looks for the field: a `TypeAdapter` of the field's annotation with its metadata (arbitrary types allowed) whose JSON Schema fails in that mode; the error is `JsonFormError(InvalidGraphError)`: `"OpaqueAction.Result.raw has no JSON form (serialization mode): Cannot generate a JsonSchema for core_schema.IsInstanceSchema (<class 'Opaque'>). Describe it with JsonSchemaValue, or leave it out of the Result."`. When no field fails alone, the class is named.

**Rationale**: the build already refuses declarations that cannot work (entity fields, inverses, the events vocabulary); a missing JSON form is the same kind of mistake, and the build sees every Params and Result. The JSON Schema is what FastAPI and MCP publish; a type without one has no JSON form an adapter can write.

**Alternatives considered**: checking at class declaration (`__init_subclass__`) — refused: a Result may reference types declared later (forward references), and the schema is complete only when the model is.

## R2. One comparison of observable state

**Decision**: `model/observable_state.py`, `observable_difference(before, after) -> str | None`: the first difference with its path (`$.order.customer.entity.name`), or `None`. Rules, checked in this order:

1. different types → a difference (a UUID and its string differ though `==` holds);
2. a declared value (`BaseEnumEntity`, `BaseStateEntity` instances) → the same object;
3. a `Lifecycle` → the same declared current status;
4. a One relation → the same id and loaded state, then the entity when loaded; a Many relation → the same ids and loaded state, then the entities in order when loaded;
5. a model → the same loaded fields, in declaration order, each compared (a partial entity holds fewer);
6. a list or tuple → the same length, item by item; a mapping → the same keys in order, value by value;
7. anything else → `==`.

`==` of every type is left as it is (FR-007).

**Rationale**: rule 2 of #399 lists exactly these; a path makes a failure in a deep Result readable, and the cache of #410 can put the same message in its refusal.

## R3. Every Result the examples build

**Decision**: `tests/examples/round_trip_runner.py` runs a script as `python script.py` would (`runpy.run_path(..., run_name="__main__")`, the script's folder first on `sys.path`, `sys.argv[0]` the script), recording every `BaseResult` that `__init__`, `model_validate` or `model_validate_json` returns. When the script ends — normally or with `SystemExit(0)` — the recording stops, each recorded Result is read back (`model_validate_json(model_dump_json())`) and compared (R2); a difference or a failed read-back prints the Result's class and the difference to stderr and exits 1. `test_examples_run.py` runs each script through the runner, so no example runs twice (SC-004).

**Measured with a prototype**: the 288 examples build 191 Results; all read back with no difference. Without the script's folder on `sys.path` one example (`step_24_relations/67_cross_module_inverse.py`) cannot import its sibling package — the runner puts it first, as `python script.py` does.

**Alternatives considered**: a separate test running every example again — refused (doubles the examples job); generating samples from schemas for the examples — refused: the examples' own values (loaded relations, statuses) are what rule 2 is about.

## R4. Every Result class of the demo

**Decision**: a test in `aoa-demo` imports every module of `aoa.demo`, takes every `BaseResult` subclass (58), builds a sample from its validation-mode JSON Schema, validates it, reads it back and compares (R2). The sample generator lives in the test: an object gets its required properties; a string its `minLength`, or a value matching its `pattern` when the schema has one; numbers their `minimum` or just above `exclusiveMinimum`; `anyOf` its first branch that is not `null`; an array one item.

**Measured**: the 58 Result schemas use only `minimum` (26), `minLength` (12), `exclusiveMinimum` (6), `anyOf` (4) and `pattern` (2); none references an entity.

## R5. Versions

`aoa-action-machine` changes (`1.0.1a13` → `1.0.1a14`). `tests/` and `examples/` are not levels; the demo's test is under `tests/`.
