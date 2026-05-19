# Entity wire projections — `BaseEntity.schema(...)`

This guide describes `BaseEntity.schema(schema={...})` in ActionMachine (`aoa.action_machine.domain`): when to use it instead of a separate DTO, how validation and OpenAPI work, and how the interchange graph records the link to the entity class.

---

## 1. What it is (and is not)

`OrderEntity.schema(schema={...})` returns a **typing annotation** (`Annotated[..., EntitySchemaMarker]`), not an entity instance.

- **Semantic link**: the field is tied to `OrderEntity` for readers, graph tooling, and policies that care about the entity type.
- **Wire contract**: the **only** runtime shape for that field is the **inline JSON Schema** dict you pass to `.schema()`. Values are plain JSON objects validated with **jsonschema** at Pydantic model construction time.
- **Not a full entity**: you do **not** get lifecycle, relations, or `FieldNotLoadedError` semantics on the wire dict. Hydrated `OrderEntity` instances are built elsewhere (e.g. repositories), not from this annotation alone.

Use a **separate Pydantic DTO** (`BaseModel` / nested models) when you want a rich Python type on the wire, computed fields, or a schema that is not literally one JSON Schema document.

---

## 2. Quick start

```python
from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model import BaseResult
from myapp.domains import ShopDomain


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str
    status: str
    total: float
    # ... other entity fields, relations, etc.


_ORDER_WIRE = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string"},
        "total": {"type": "number"},
    },
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}


class OrderSummaryResult(BaseResult):
    order: OrderEntity.schema(schema=_ORDER_WIRE) = Field(  # type: ignore[valid-type]
        description="Partial order payload for APIs",
    )


payload = {"order": {"id": "o1", "status": "paid", "total": 99.5}}
result = OrderSummaryResult.model_validate(payload)
assert result.order["id"] == "o1"
```

At class definition time, `BaseEntity.schema()` deep-copies the schema and runs `jsonschema.Draft7Validator.check_schema`, so invalid Draft-7 fragments fail early.

---

## 3. Required vs optional wire fields

Mark optional keys in the JSON Schema (omit from `required`, or use union types in `properties`). For a field that may be absent on the **Python** side, use a union with `None` on the `BaseResult` / `BaseParams` field:

```python
class OrderSummaryResult(BaseResult):
    order: OrderEntity.schema(schema=_ORDER_WIRE) | None = Field(
        default=None,
        description="Partial order; omitted when not computed",
    )
```

When the value is `None`, the JSON Schema validator for the projection does not run. When the value is a dict, it must satisfy `_ORDER_WIRE`.

---

## 4. Limitations

- The argument to `.schema()` must be a **non-empty `dict`** that is valid **JSON Schema** (Draft 7 check at registration time).
- Only **JSON-serializable** schema content: no Python types, callables, or entity instances inside the schema dict.
- The validated value is a **plain `dict`** (identity preserved on success); there is no automatic conversion to `OrderEntity`.

---

## 5. OpenAPI, MCP, and Pydantic

Pydantic v2 uses metadata hooks on `EntitySchemaMarker` for core validation and JSON Schema emission. FastAPI and `model_json_schema()` see the **user** JSON Schema for the field. MCP tool **input** schemas still come from **Params** only; projections on **Result** affect serialized JSON and interchange metadata, not MCP tool arguments.

---

## 6. Interchange graph — `entity_schema`

For each `BaseParams` / `BaseResult` field (or property-style member) that uses `BaseEntity.schema(...)`, the graph emits an aggregation edge named **`entity_schema`** from the concrete **`Field`** / **`PropertyField`** companion node to the **`Entity`** node for the marker’s `entity_cls`. The edge is DAG-participating (`is_dag=True`); `target_node_id` is the entity class full qualname; `properties` on the edge are JSON-only (currently `{}`).

If the entity type is excluded from the graph (for example `@exclude_graph_model` on the entity class) but a projection still targets it, `NodeGraphCoordinator.build()` can fail referential integrity checks — keep projections pointed at entities that exist in the coordinator’s node set.

---

## 7. Further reading

- Implementation: `packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py` (`BaseEntity.schema`), `entity_schema_marker.py`.
- Sample usage: `packages/aoa-examples/src/aoa/examples/model/entity_projection_demo/`.
- Tests: `tests/action_machine/domain/`, adapter tests under `tests/action_machine/adapters/`, `tests/action_machine/graph_model/test_entity_schema_graph_edge.py`, `tests/examples/model/test_entity_projection_samples.py`.
