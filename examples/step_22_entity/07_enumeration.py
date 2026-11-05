"""Read a closed currency catalogue.

The class declares every value the shop accepts.
Run: uv run python examples/step_22_entity/07_enumeration.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage):
    """Hold the shop entities."""


@entity(description="Currencies accepted by the shop", resource=ShopStorage)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shop's currency vocabulary."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


print("Codes:", CurrencyEnumEntity.codes())
print("Members:", len(CurrencyEnumEntity.members))
print("Same object:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
print("Value:", CurrencyEnumEntity.EUR.display_name, CurrencyEnumEntity.EUR.symbol)
