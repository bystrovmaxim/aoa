"""Check a schema once, in the draft its values are checked with.

A JSON Schema field picks its draft when it is declared: the draft its
"$schema" names, the newest one (2020-12) when it names none. The schema is
checked once, in that draft, and every value afterwards is checked against it.
A schema its own draft refuses is refused at declaration, never on a value.

Run: uv run python examples/step_17_schema_results/02_draft_of_schema.py
"""

import jsonschema
from pydantic import Field, ValidationError

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseResult, JsonSchemaValue
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Customer order", domain=ShopDomain)
class OrderCoreEntity(BaseCoreEntity):
    """Describe an order whose rows a projection returns."""

    id: str = Field(description="Order identifier")
    status: str = Field(description="Order status")
    total: float = Field(description="Order total")


@meta(description="Stores the shop entities")
@entities(
    OrderCoreEntity,
)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


ORDER_WIRE = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "status": {"type": "string"}, "total": {"type": "number"}},
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}

# A Draft 7 "tuple": items as a list, one schema per position.
PAIR = {"type": "array", "items": [{"type": "string"}, {"type": "integer"}]}
# A projection lists fields of its entity, so there the same tuple form sits inside the id field.
ORDER_PAIR = {"type": "object", "properties": {"id": {"type": "string", "items": PAIR["items"]}}, "required": ["id"]}

print("1) No $schema: the newest draft checks the schema at declaration")
try:
    JsonSchemaValue.define(name="Pair", schema=PAIR)
except jsonschema.SchemaError as exc:
    print("   JsonSchemaValue.define ->", type(exc).__name__ + ":", exc.message)
else:
    raise AssertionError("The newest draft refuses a list of items")
try:
    OrderCoreEntity.schema(schema=ORDER_PAIR)
except jsonschema.SchemaError as exc:
    print("   OrderCoreEntity.schema  ->", type(exc).__name__ + ":", exc.message)
else:
    raise AssertionError("A projection follows the same rule")

print("2) $schema names Draft 7: the schema and its values are checked as Draft 7")
Pair7 = JsonSchemaValue.define(name="Pair7", schema={"$schema": "http://json-schema.org/draft-07/schema#", **PAIR})


class PairResult(BaseResult):
    """Return a pair checked position by position."""

    pair: Pair7 = Field(description="A name and a count")


print("   ['a', 1] ->", PairResult(pair=["a", 1]).pair)
try:
    PairResult(pair=[1, "a"])
except ValidationError as exc:
    print("   [1, 'a'] -> ValidationError:", exc.errors()[0]["msg"].splitlines()[0])
else:
    raise AssertionError("Draft 7 checks each position")

print("3) A refused value reports the best error, as before")


class OrderRowResult(BaseResult):
    """Return one order row as a projection."""

    order: OrderCoreEntity.schema(schema=ORDER_WIRE) = Field(description="Order row")  # type: ignore[valid-type]


print("   accepted:", OrderRowResult(order={"id": "o1", "status": "paid", "total": 99.5}).order)
try:
    OrderRowResult(order={"id": 1, "status": "paid", "secret": "x"})
except ValidationError as exc:
    print("   refused :", exc.errors()[0]["msg"])
else:
    raise AssertionError("The row has three errors")
