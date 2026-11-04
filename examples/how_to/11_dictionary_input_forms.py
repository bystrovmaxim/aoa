"""Send a dictionary selection as an id object or as the reference it came out as.

A dictionary relation reads its container, the id object {"id": code}, or the
reference it writes, on every path: from JSON, from a dict in code, from a
FastAPI or MCP request. A reference is chosen by its code; its label and
properties come from the catalogue.

Run: uv run python examples/how_to/11_dictionary_input_forms.py
"""

from typing import Annotated

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AggregateMany, BaseCoreEntity, BaseEnumEntity, CompositeOne, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class PricingDomain(BaseDomain):
    """Group the pricing declarations."""

    name = "pricing"
    description = "Pricing"


@entity(description="Currencies", domain=PricingDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare canonical currency values."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Prices", domain=PricingDomain)
class PricesCoreEntity(BaseCoreEntity):
    """Select one primary currency and several alternatives."""

    primary: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Primary currency")
    alternatives: Annotated[AggregateMany[CurrencyEnumEntity], NoInverse()] = Field(description="Alternative currencies")


print("1) A dict in code, as FastAPI and MCP pass it")
price = PricesCoreEntity.model_validate({"primary": {"id": "eur"}, "alternatives": [{"id": "usd"}]})
print("   primary:", price.primary, "| alternatives:", price.alternatives.ids)

print("2) The reference written is read back")
written = price.model_dump(mode="json")
print("   written:", written["primary"])
print("   read back equal:", PricesCoreEntity.model_validate(written) == price)

print("3) The code chooses; the catalogue labels")
relabelled = PricesCoreEntity.model_validate(
    {"primary": {"code": "eur", "display_name": "Dollar"}, "alternatives": [{"id": "usd"}, {"code": "eur"}]}
)
print("   primary label:", relabelled.primary.entity.display_name)
print("   alternatives:", relabelled.alternatives.ids)

print("4) What is refused")
for bad in ("eur", {"id": "eur", "extra": 1}, {"display_name": "Euro"}, {"id": "gbp"}):
    try:
        PricesCoreEntity.model_validate({"primary": bad, "alternatives": []})
    except ValidationError:
        print("   refused:", bad)
    else:
        raise AssertionError(f"{bad!r} must be refused")

schema = PricesCoreEntity.model_json_schema(mode="validation")["properties"]["primary"]
print("5) Input schema:", [shape["required"] for shape in schema["anyOf"]])
