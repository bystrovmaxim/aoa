"""Share a reference value.

EUR describes a currency used by many objects. Its symbol describes that value; it is not a dated exchange-rate quote or a position in an order process.

Run: uv run python examples/step_20_entity/07_enumeration.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


@entity(description="Currency reference value", domain=ShopDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Describe a currency shared by monetary amounts."""

    code: str = Field(description="Currency code")
    symbol: str = Field(description="Currency symbol")

currency = CurrencyEnumEntity(code="EUR", symbol="€")
assert currency.code == "EUR"
print(currency.code, currency.symbol)
