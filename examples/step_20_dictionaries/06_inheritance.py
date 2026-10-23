"""A subclass declares its own catalogue.

A child dictionary reuses fields while declaring a different set of currencies.
Run: uv run python examples/step_20_dictionaries/06_inheritance.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
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

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Price tag", domain=ShopDomain)
class PriceTagCoreEntity(BaseCoreEntity):
    """Associate an amount with its currency."""

    id: str = Field(description="Tag identifier")
    amount: float = Field(description="Price amount")
    currency: CurrencyEnumEntity = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""

    @entity(description="Another currency set", domain=ShopDomain)
    class LocalCurrencyEnumEntity(CurrencyEnumEntity):
        """Reuse the currency fields with a separate vocabulary."""

        GBP = value(code="gbp", display_name="Pound", symbol="£")

    print("Parent:", CurrencyEnumEntity.codes())
    print("Child:", LocalCurrencyEnumEntity.codes())
    assert LocalCurrencyEnumEntity.codes() == ["gbp"]


if __name__ == "__main__":
    main()
