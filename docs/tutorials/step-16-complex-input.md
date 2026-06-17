<!-- translated-from: step-16-complex-input_draft.md @ 2026-06-17T17:53:37Z · sha256:a18a84e5a3d5 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 16 — Accepting complex data from a request

<table width="100%"><tr>
  <td align="left"><a href="step-15-schema-results.md">← Step 15 — Result by schema</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-17-connections.md">Step 17 — Connections at the boundary →</a></td>
</tr></table>

- [Nested objects and collections](#nested-objects-and-collections)
- [Arbitrary JSON by schema](#arbitrary-json-by-schema)
- [A partial entity on input](#a-partial-entity-on-input)
- [How the transports see it](#how-the-transports-see-it)
- [Field names: one trap](#field-names-one-trap)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

The previous chapter was about how an operation **returns** complex data. This one is the mirror: how it **accepts** it. A request rarely carries a couple of scalars — usually it is nested objects, collections, sometimes arbitrary JSON. The good news is that no separate mechanism is needed for this: `Params` is a Pydantic model, so **any** Pydantic shape works as a field, and the [adapters](step-13-fastapi.md) themselves derive both the request body and the schema from it. Complex input in AOA is accepted exactly the same way as simple input.

[▶ Try in Colab](https://drive.google.com/file/d/1YukUsvY7G0z-XzgU6rrGcyCGWZRL4T3x/view?usp=drive_link) · [Open in project](../../examples/step_16_complex_input/01_complex_input.py)

---

## Nested objects and collections

A `Params` field can be another model or a collection — this is ordinary Pydantic, with no special support:

```python
class Address(BaseModel):
    city: str
    zip: str

class LineItem(BaseModel):
    sku: str
    qty: int = Field(ge=1)

class CreateOrderParams(BaseParams):
    customer: str
    address: Address                # nested object
    lines: list[LineItem]           # collection of objects
    tags: list[str] = Field(default_factory=list)   # collection of scalars
```

The machine and the adapters parse this automatically: the incoming JSON is validated into typed `Address` and a list of `LineItem`, and field constraints (`qty: int = Field(ge=1)`) are checked on each element. `BaseParams` is declared with `extra="forbid"`, so an unknown key in the input will be rejected — the input contract is strict.

## Arbitrary JSON by schema

When part of a request is arbitrary JSON whose shape is set externally (not by your classes), the same [`JsonSchemaValue`](step-15-schema-results.md) works on input as on output: a `Params` field holds JSON validated by a strict schema at construction.

```python
OrderMeta = JsonSchemaValue.define(name="OrderMeta", schema={
    "type": "object",
    "properties": {"source": {"type": "string"}, "ab_test": {"type": "string"}},
    "required": ["source"],
    "additionalProperties": False,
})

class CreateOrderParams(BaseParams):
    ...
    metadata: OrderMeta             # arbitrary JSON, validated by schema
```

Invalid `metadata` (without the required `source`, with an extra key) is rejected at the boundary, and the schema itself is visible in OpenAPI and in the MCP tool description — the client and the agent know in advance what to pass.

## A partial entity on input

Symmetrically to output projections, [`BaseEntity.schema(...)`](step-15-schema-results.md#a-partial-entity-projection) works on input too: a `Params` field accepts a partial "slice" of an entity — a schema-validated `dict` semantically bound to the entity class. This is convenient when the client sends not the whole entity but exactly the declared subset of its fields.

## How the transports see it

The shape of `Params` is one, but delivery depends on the transport:

- **[FastAPI](step-13-fastapi.md).** For `POST/PUT/PATCH` all complex input arrives in the JSON body — nested objects and collections are parsed naturally. For `GET/DELETE` parameters are taken from the query and the path, so scalars go there (and, if needed, repeated keys for lists), while structural requests are shaped as `POST` with a body.
- **[MCP](step-14-mcp.md).** A tool's `inputSchema` is the full `model_json_schema()` of `Params`: nested models become `$ref`/`$defs`, lists become `array`. The agent gets the exact structural contract and fills it in without guessing the shape.

In both cases not a line of code for parsing complex input needs to be written — it is derived from the contract.

## Field names: one trap

`BaseParams` inherits the dict interface of `BaseSchema` (`keys()`, `values()`, `items()`, `get()`). So a field named like one of these methods — for example `items` — shadows it and triggers a Pydantic warning. Name such a field differently (`lines`, `entries`), as in the example above.

**Run:**

```bash
uv run python examples/step_16_complex_input/01_complex_input.py
```

**Output:**

```text
1) In-code (model_validate):
   address -> Address(city='Berlin')
   lines   -> list[LineItem] x2; tags=['priority', 'gift']
   metadata-> {'source': 'web', 'ab_test': 'v2'} (validated by JSON Schema)
   bad metadata -> ValidationError (schema requires 'source')

2) Over HTTP (FastAPI TestClient):
   POST /orders -> 200 {'order_id': 'ord-1', 'item_count': 2}

3) To an agent (MCP inputSchema):
   properties: ['customer', 'address', 'lines', 'tags', 'metadata']
   lines -> type=array; address -> $ref
```

The same complex `Params` is accepted in three ways: as a dict in code, as a JSON body over HTTP, and as a tool's structural schema for an agent — and validated against the contract everywhere.

## Invariants

- **Complex input is ordinary Pydantic.** Nested models, `list[...]`, `dict[...]` are `Params` fields; no separate mechanism is required.
- **The input contract is strict.** `BaseParams` is `extra="forbid"`: an unknown key is rejected.
- **Arbitrary JSON by schema.** `JsonSchemaValue` and entity projections work on `Params` the same way as on `Result`.
- **Delivery depends on the transport.** FastAPI: structural input in the `POST` body; MCP: `inputSchema` from `model_json_schema(Params)` carries the nesting whole.
- **A field name must not shadow the dict interface** of `BaseSchema` (`items`/`keys`/`values`/`get`).

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

Complex input in AOA requires nothing beyond ordinary Pydantic: nested objects and collections are `Params` fields, arbitrary JSON is accepted by a strict schema via `JsonSchemaValue`, and a partial entity via `BaseEntity.schema`. The input contract is strict (`extra="forbid"`), and the adapters derive both the body parsing (FastAPI) and the tool schema (MCP) from it — without parsing code. Together with the previous chapter this closes both boundaries of an operation: how it accepts data and how it returns it.

Next — **[Connections at the request boundary](step-17-connections.md)**: how the adapter supplies open resources to an operation on each incoming request.

---

## Review questions

1. Why is no separate mechanism needed to accept nested objects and collections? What is enough to declare for it?
2. What happens to an unknown key in an input request, and why?
3. When is `JsonSchemaValue` appropriate on input, and when is an ordinary nested model?
4. How does the same complex `Params` look to FastAPI and to MCP? Where does the body appear, and where the `inputSchema`?
5. Why is a structural request shaped as `POST` with a body rather than `GET` with a query?
6. Why can a field not be named `items`, and how do you work around it?

> **Exercise.** In [01_complex_input.py](../../examples/step_16_complex_input/01_complex_input.py) add an optional field `coupon: str | None = None` to `CreateOrderParams` and check that the request passes both with and without it. Then send through `TestClient` a body with an extra key not in `Params` and confirm the adapter answers `422` — the input contract is strict.

---

<table width="100%"><tr>
  <td align="left"><a href="step-15-schema-results.md">← Step 15 — Result by schema</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-17-connections.md">Step 17 — Connections at the boundary →</a></td>
</tr></table>
