"""Dump an entity with dictionary references in Python mode and in JSON mode.

A Python-mode dump keeps each relationship wrapper with its canonical members;
a JSON-mode dump turns each selected member into its reference.

Run: uv run python examples/how_to/10_dictionary_python_dump.py
"""

from typing import Annotated

from pydantic import Field

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


price = PricesCoreEntity(primary=CompositeOne(id="eur"), alternatives=AggregateMany(ids=("usd",)))

python_dump = price.model_dump()
print("Python primary:", python_dump["primary"])
print("Python alternatives:", python_dump["alternatives"])
print("Canonical member kept:", python_dump["primary"].entity is CurrencyEnumEntity.EUR)

json_dump = price.model_dump(mode="json")
print("JSON primary:", json_dump["primary"])
print("JSON alternatives:", json_dump["alternatives"])
