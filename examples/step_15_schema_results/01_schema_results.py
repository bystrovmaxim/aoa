"""
01_schema_results.py — Return complex objects validated by JSON Schema

Sometimes a service must return data whose exact shape is awkward to model as a
deep tree of nested Pydantic classes: an audit trail, a metadata blob, an
interchange snapshot, a partial view of an entity. Two field-level tools let a
field hold plain JSON validated against an explicit, strict JSON Schema — while
the rest of the model stays ordinarily typed:

  1. JsonSchemaValue.define(name=, schema=)  — a field type for any complex JSON
     payload, validated at construction. model_dump() emits raw JSON;
     model_json_schema() exposes the schema (so FastAPI / MCP surface it).
  2. BaseEntity.schema(schema={...})          — a field bound to an entity class
     but validated against a partial JSON Schema: return a subset of an entity's
     fields without hydrating the whole entity.

Both are plain Pydantic v2 types, so they validate the same way for a service
return AND for in-code construction — no machine required.

Tutorial: ../../docs/tutorials/step-15-schema-results_draft.md  ·  topic: schema-validated returns

Run:
    uv run python examples/step_15_schema_results/01_schema_results.py
"""

from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.model import BaseResult, JsonSchemaValue


# ── 1. A complex object as one schema-validated field ────────────────────────
# Strict schema: objects must list properties + forbid extras; arrays declare items.
AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "actor": {"type": "string"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "to": {"type": "string"},
                },
                "required": ["field", "to"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["actor", "changes"],
    "additionalProperties": False,
}
AuditReport = JsonSchemaValue.define(name="AuditReport", schema=AUDIT_SCHEMA)


class ChangeAuditResult(BaseResult):
    entity_id: str = Field(description="Affected entity")
    audit: AuditReport = Field(description="Audit trail payload (validated by JSON Schema)")


# ── 3. A partial projection of an entity ─────────────────────────────────────
class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    status: str = Field(description="Order status")
    total: float = Field(description="Order total")
    customer_email: str = Field(description="Full-entity field, omitted on the wire")


# The wire projection returns only id/status/total — not customer_email.
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
        description="Partial order projection (no nested customer)",
    )


def main() -> None:
    # 1) What a service aspect returns: a complex object, no nested Result model.
    result = ChangeAuditResult(
        entity_id="ord-1",
        audit={"actor": "alice", "changes": [{"field": "status", "to": "paid"}]},
    )
    print("1) Service return — complex object validated by JSON Schema:")
    print(f"   model_dump() -> {result.model_dump()}")
    audit_schema = ChangeAuditResult.model_json_schema()["properties"]["audit"]
    print(f"   schema exposed to FastAPI/MCP for `audit` -> type={audit_schema.get('type')}, "
          f"required={audit_schema.get('required')}")

    # 2) The same type validated in-code — any dict, anywhere, not just a service.
    print("\n2) Same type used in-code (model_validate):")
    ok = ChangeAuditResult.model_validate(
        {"entity_id": "ord-2", "audit": {"actor": "bob", "changes": []}}
    )
    print(f"   valid payload   -> accepted ({ok.entity_id})")
    try:
        ChangeAuditResult.model_validate(
            {"entity_id": "ord-3", "audit": {"actor": "eve", "changes": [{"field": "status"}]}}
        )
    except ValidationError:
        print("   invalid payload -> ValidationError (a change item is missing required 'to')")

    # 3) Partial entity projection: return a subset of OrderEntity, validated.
    print("\n3) Partial entity projection (BaseEntity.schema):")
    summary = OrderSummaryResult.model_validate(
        {"order": {"id": "o1", "status": "paid", "total": 99.5}}
    )
    print(f"   partial order   -> accepted: {summary.order}")
    try:
        OrderSummaryResult.model_validate(
            {"order": {"id": "o2", "status": "paid", "total": 10.0, "secret": "x"}}
        )
    except ValidationError:
        print("   unexpected field -> rejected (schema forbids fields outside the projection)")


if __name__ == "__main__":
    main()
