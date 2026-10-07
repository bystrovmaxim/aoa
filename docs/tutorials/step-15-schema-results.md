<!-- translated-from: step-15-schema-results_draft.md @ 2026-06-17T17:53:37Z · sha256:28668b131c3d -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 15 — Result by JSON schema

<table width="100%"><tr>
  <td align="left"><a href="step-14-mcp.md">← Step 14 — MCP</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-16-complex-input.md">Step 16 — Complex input →</a></td>
</tr></table>

- [A complex object as one field](#a-complex-object-as-one-field)
- [Why it suits services](#why-it-suits-services)
- [In code, it's plain Pydantic](#in-code-its-plain-pydantic)
- [A partial entity projection](#a-partial-entity-projection)
- [Where validation happens](#where-validation-happens)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

An operation's contract is described by `Params` and `Result` — usually as strictly typed Pydantic models, and that is what you should do in most cases. But sometimes the shape of the data in the result is awkward as a tree of nested classes: an audit log, a metadata blob, an interchange graph snapshot, a partial "slice" of an entity for an API. Building a separate model of a dozen nested classes for each such piece is a lot of code for a value that goes outward as JSON anyway.

AOA gives two **field-level** tools: a single model field can hold arbitrary JSON, validated by an explicit **strict JSON Schema** at object construction, while the other fields stay ordinary typed fields. This is especially convenient for services — to hand out data without building a heavy `Result` model around it — but it works [in code too](#in-code-its-plain-pydantic), because these are plain Pydantic v2 types.

[▶ Try in Colab](https://drive.google.com/file/d/1h1VgrUKEKlaKs_tiGAR0pAqRyFZwKZb3/view?usp=drive_link) · [Open in project](../../examples/step_15_schema_results/01_schema_results.py)

---

## A complex object as one field

`JsonSchemaValue.define(name=, schema=)` creates a **field type** for `BaseResult`, `BaseParams`, or any `BaseModel`. The value of such a field is arbitrary JSON, which at model construction is validated against the schema via `jsonschema`:

```python
from aoa.action_machine.model import BaseResult, JsonSchemaValue

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "actor": {"type": "string"},
        "changes": {"type": "array", "items": {
            "type": "object",
            "properties": {"field": {"type": "string"}, "to": {"type": "string"}},
            "required": ["field", "to"],
            "additionalProperties": False,
        }},
    },
    "required": ["actor", "changes"],
    "additionalProperties": False,
}
AuditReport = JsonSchemaValue.define(name="AuditReport", schema=AUDIT_SCHEMA)


class ChangeAuditResult(BaseResult):
    entity_id: str = Field(description="Affected entity")
    audit: AuditReport = Field(description="Audit trail payload")
```

The schema is **strict** by construction, and this is checked at the moment of `define`: every object must list `properties` and close itself with `"additionalProperties": false`, every array must declare `items`. `define` rejects a vague schema immediately (`ValueError`), not on production data. You define such a type at **module level** — so the type's identity is stable.

The `audit` field stays an ordinary field next to the typed `entity_id`: `model_dump()` returns raw JSON, and `model_json_schema()` shows that very schema — which is why [FastAPI](step-13-fastapi.md) and [MCP](step-14-mcp.md) see it and surface it in OpenAPI and in the tool description.

## Why it suits services

When a service hands out data whose shape is set externally (by an interchange contract, a partner's schema, an audit format) or changes independently of your code, describing it with a dozen nested models is extra work and extra coupling. A single `JsonSchemaValue` field solves both tasks: the value is **validated** against the schema on input and output, and the schema is **visible** in the API contract. You do not build a `Result` model around someone else's structure — you declare its schema where it belongs.

## In code, it's plain Pydantic

A `JsonSchemaValue` field is an ordinary Pydantic v2 type, so it validates the value the same way whether you return it from a service or validate a dict right in the code. No machine is needed for this:

```python
ChangeAuditResult.model_validate({"entity_id": "ord-2", "audit": {"actor": "bob", "changes": []}})  # ok
ChangeAuditResult.model_validate({"entity_id": "ord-3", "audit": {"actor": "eve",
    "changes": [{"field": "status"}]}})  # ValidationError: a change is missing the required 'to'
```

So the same schema safeguards data both at the service boundary and in any internal code that assembles or accepts this structure.

## A partial entity projection

The third case is to return **part** of a domain entity, not the whole. `BaseEntity.schema(schema={...})` creates an `Annotated[Entity, …]` annotation: the field is semantically bound to the entity class (for readers and the graph), but on the wire it is validated against an explicit JSON Schema — a subset of its fields.

```python
class OrderSummaryResult(BaseResult):
    order: OrderEntity.schema(schema=_ORDER_WIRE) = Field(  # type: ignore[valid-type]
        description="Partial order projection (no nested customer)",
    )

OrderSummaryResult.model_validate({"order": {"id": "o1", "status": "paid", "total": 99.5}})  # ok
```

Important is what this is **not**: the field's value is a plain `dict` validated against the schema, and **not** a hydrated `OrderEntity` instance (no lifecycle, relations, or `FieldNotLoadedError`). Full entities are assembled elsewhere — in [resources](../index.md#v-data-model). The projection returns exactly the declared slice: a field outside the schema will be rejected. When you need a rich Python type on the wire (computed fields, your own structure) — use a separate `BaseModel`, not a projection.

## Where validation happens

- **Validation is at model construction.** The ordinary constructor and `model_validate` validate the value; `model_construct()` skips validators (the general Pydantic contract) — it is not for validated assembly.
- **`None` only for a union with `None`.** For the field to be allowed absent, declare `… | None`; then schema validation is not run on `None`.
- **An MCP tool's input is from `Params`.** Projections and `JsonSchemaValue` on `Result` affect the serialized JSON and the graph metadata, but **not** the MCP tool's argument schema — it is still derived only from `Params`.

**Run:**

```bash
uv run python examples/step_15_schema_results/01_schema_results.py
```

**Output:**

```text
1) Service return — complex object validated by JSON Schema:
   model_dump() -> {'entity_id': 'ord-1', 'audit': {'actor': 'alice', 'changes': [{'field': 'status', 'to': 'paid'}]}}
   schema exposed to FastAPI/MCP for `audit` -> type=object, required=['actor', 'changes']

2) Same type used in-code (model_validate):
   valid payload   -> accepted (ord-2)
   invalid payload -> ValidationError (a change item is missing required 'to')

3) Partial entity projection (BaseEntity.schema):
   partial order   -> accepted: {'id': 'o1', 'status': 'paid', 'total': 99.5}
   unexpected field -> rejected (schema forbids fields outside the projection)
```

## Invariants

- **A field, not the whole model.** The schema applies to one field; the other fields stay ordinarily typed.
- **Strict schema by construction.** Objects list `properties` and set `"additionalProperties": false`, arrays declare `items`; otherwise `define` fails immediately.
- **Validation at construction.** The constructor/`model_validate` validate; `model_construct` does not.
- **The schema is visible to the contract.** `model_dump()` — raw JSON; `model_json_schema()` — the user schema that FastAPI and MCP surface.
- **A projection ≠ an entity.** `BaseEntity.schema()` gives a validated `dict` slice, not a hydrated instance; an MCP tool's input is taken only from `Params`.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

When the result's shape is awkward as a tree of nested models, AOA lets you describe it at the field level: `JsonSchemaValue.define` holds arbitrary JSON validated by a strict schema, and `BaseEntity.schema` returns a partial entity projection — both stay plain Pydantic types, so they work in a service result and in internal code alike, and their schema is visible in OpenAPI and in the MCP tool description. This removes the need to build a heavy `Result` model for a value that goes outward as JSON anyway.

Next — **[Accepting complex data from a request](step-16-complex-input.md)**: the mirror topic — how an operation accepts collections, nested objects, and JSON by schema.

---

## Review questions

1. In which cases is a `JsonSchemaValue` field more appropriate than a tree of nested Pydantic models?
2. What does "strict schema" mean, and at what moment is its strictness checked?
3. Where is value validation against the schema performed, and why does `model_construct()` skip it?
4. How do you make a field optional so that validation is not run on `None`?
5. How does `BaseEntity.schema(...)` differ from returning a hydrated entity instance? What exactly is in the field?
6. Does a projection on `Result` affect an MCP tool's argument schema? Where does the tool's input come from?
7. Why does such a field's schema automatically land in OpenAPI and the MCP tool description?

> **Exercise.** In [01_schema_results.py](../../examples/step_15_schema_results/01_schema_results.py) add an optional `reason` field (string, not in `required`) to `AUDIT_SCHEMA` and check that values with and without it pass. Then remove `"additionalProperties": false` from the nested `changes.items` object and confirm that `JsonSchemaValue.define` rejects such a schema at type definition.

---

<table width="100%"><tr>
  <td align="left"><a href="step-14-mcp.md">← Step 14 — MCP</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-16-complex-input.md">Step 16 — Complex input →</a></td>
</tr></table>
