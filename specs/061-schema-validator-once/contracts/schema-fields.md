# Contract: what a caller of the two schema fields observes

The signatures do not change. What changes is when a broken schema is refused and how long a value check takes.

| Call | Today | After |
| --- | --- | --- |
| `JsonSchemaValue.define(name=..., schema=S)`, `S` valid in 2020-12 | accepted (checked as Draft 7) | accepted (checked as 2020-12) |
| `JsonSchemaValue.define(...)` with the Draft 7 tuple `PAIR` | accepted | `SchemaError: [{'type': 'string'}, {'type': 'integer'}] is not of type 'object', 'boolean'` |
| a value of that field | `SchemaError` on every value | — (never declared) |
| `PAIR` with `"$schema": draft-07` | accepted; `["a", 1]` passes, `[1, "a"]` → `ValidationError` (each value re-checks the schema) | the same outcome, the schema checked once |
| `OrderCoreEntity.schema(schema=S)` | the same as `JsonSchemaValue` for every row above | the same as `JsonSchemaValue` for every row above |
| a valid row, three-field strict schema | ~550 µs | ~10 µs |
| `{"id": 1, "status": "paid", "secret": "x"}` through the projection | `ValueError: OrderCoreEntity wire projection: 'total' is a required property` | the same |
| a refused value through `JsonSchemaValue` | `ValueError(str(error))` | the same |
| `$schema` naming an unknown draft | the newest draft, `DeprecationWarning` on every value | the newest draft, `DeprecationWarning` once, at declaration |
| strict-shape violation in `JsonSchemaValue.define` | `ValueError` before the schema check | the same |
| `pickle` / `copy.deepcopy` of an `EntitySchemaMarker` | an equal marker | an equal marker whose check refuses and accepts the same values |
