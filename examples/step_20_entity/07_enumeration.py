"""Share a closed set of reference values.

EUR describes a currency used by many objects. Its symbol describes that value; it is not a dated exchange-rate quote or a position in an order process.

The dictionary is closed: it declares every value it has, in its own body, and nothing else is a value.

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
    """Declare the currencies the shop uses, each one a value of this dictionary."""

    symbol: str = Field(description="Currency symbol")

    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")  # noqa: F821
    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")  # noqa: F821
    RUB = CurrencyEnumEntity(code="rub", display_name="Ruble", symbol="₽")  # noqa: F821


print(CurrencyEnumEntity.codes())
print(CurrencyEnumEntity.by_code("eur").display_name, CurrencyEnumEntity.EUR.symbol)
print(CurrencyEnumEntity.USD is CurrencyEnumEntity.by_code("usd"))
