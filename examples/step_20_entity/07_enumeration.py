"""Read a closed currency catalogue.

The class declares every value the shop accepts.
Run: uv run python examples/step_20_entity/07_enumeration.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Currencies accepted by the shop", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shop's currency vocabulary."""

    symbol: str = Field(description="Currency symbol")

    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")  # noqa: F821
    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")  # noqa: F821


print("Codes:", CurrencyEnumEntity.codes())
print("Members:", len(CurrencyEnumEntity.members))
print("Same object:", CurrencyEnumEntity.by_code("eur") is CurrencyEnumEntity.EUR)
print("Value:", CurrencyEnumEntity.EUR.display_name, CurrencyEnumEntity.EUR.symbol)
