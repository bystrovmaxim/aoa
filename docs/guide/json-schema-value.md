# JsonSchemaValue — field-level JSON with a static JSON Schema

This guide describes `JsonSchemaValue` in ActionMachine (`aoa.action_machine.model`): when to use it, how to declare fields, and how it surfaces in OpenAPI, MCP, and the interchange graph.

---

## 1. Problem — why not `dict[str, Any]`?

A plain `dict[str, Any]` (or `Any`) on `BaseResult` / `BaseParams`:

- does not validate structure at model construction time;
- does not attach a machine-readable schema for OpenAPI or for graph tooling;
- weakens the contract between summary aspects, adapters, and clients.

`JsonSchemaValue.define(name, schema)` returns a **dedicated type** you use as the field annotation. Pydantic validates the value with **jsonschema**; `model_dump()` still returns a normal `dict` (or list, etc.) for that field.

---

## 2. Quick start

```python
from pydantic import Field

from aoa.action_machine.model import BaseResult, JsonSchemaValue

GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {"type": "array", "items": {"type": "object"}},
        "edges": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["nodes", "edges"],
    "additionalProperties": False,
}
GraphJson = JsonSchemaValue.define(name="GraphJson", schema=GRAPH_SCHEMA)


class OrderResult(BaseResult):
    order_id: str
    graph: GraphJson = Field(description="Interchange graph JSON")


result = OrderResult(order_id="ORD-1", graph={"nodes": [], "edges": []})
assert result.model_dump()["graph"] == {"nodes": [], "edges": []}
```

Define the type at **module level** (not inside a class body) so import order and graph introspection stay stable.

---

## 3. Optional fields

Use a union with `None`:

```python
class OrderResult(BaseResult):
    order_id: str
    graph: GraphJson | None = None
```

When the value is `None`, Pydantic does not run the JSON Schema validator for that branch. When it is not `None`, the full schema applies.

---

## 4. OpenAPI (FastAPI)

FastAPI uses the Pydantic model’s `model_json_schema()` for response models. `JsonSchemaValue` types implement `__get_pydantic_json_schema__`, so the field’s JSON Schema appears in the generated OpenAPI document **without** hand-written OpenAPI patches.

In practice the field schema may be **inline** or behind a `**$ref`** into `components/schemas`, depending on Pydantic/version; tests should resolve `$ref` when asserting.

Reference tests: `tests/action_machine/adapters/fastapi/test_fastapi_json_schema_value.py`.

---

## 5. MCP

MCP tools publish an **input** schema from the action’s **Params** model. `JsonSchemaValue` on the **Result** does not alter tool input parameters.

Results are serialized with `model_dump(mode="json")`; JSON fields remain plain JSON-compatible values in the success envelope.

Reference tests: `tests/action_machine/adapters/mcp/test_mcp_json_schema_value.py`.

---

## 6. Graph builder

`FieldGraphEdge` resolves each field’s annotation (including `Optional` unwrapping) and, when the type was created with `JsonSchemaValue.define`, attaches metadata to the interchange `Field` node:

- `properties["json_schema_value"]` — `true`
- `properties["json_schema_name"]` — the `name` passed to `define`
- `properties["json_schema"]` — deep copy of the schema dict

Public helpers for custom tooling:

- `is_json_schema_value_type(tp)`
- `get_json_schema_value_metadata(tp)` → `{"name": str, "schema": dict}` or `None`

Example interchange graphs include several results with a `sample_audit` field; see `tests/examples/model/test_sample_graph_json_fields.py` and `aoa.examples.model.*.actions` for concrete usage.

---

## 7. Limitations and FAQ


| Topic                          | Behavior                                                                                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `model_construct()`            | Skips validators; JSON Schema is **not** applied. Use `Result(...)` for validated construction.                   |
| Invalid instance at `define()` | `jsonschema.SchemaError` if the schema document is invalid.                                                       |
| Invalid field value            | Pydantic `ValidationError` (jsonschema errors are wrapped for a single surface).                                  |
| Large schemas                  | Embedded as-is in OpenAPI and graph metadata; keep schemas focused.                                               |
| Adapters                       | No special-case code paths are required for `JsonSchemaValue` on wire models; behavior comes from Pydantic hooks. |


Further detail: module docstring in `packages/aoa-action-machine/src/aoa/action_machine/model/json_schema_value.py` and spike notes in `docs/spikes/json_schema_value_pydantic_v2.md`.