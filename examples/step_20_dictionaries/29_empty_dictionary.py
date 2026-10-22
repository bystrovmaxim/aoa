"""A decorated dictionary cannot be empty.

An intermediate class can define shared fields; a concrete dictionary must supply values.
Run: uv run python examples/step_20_dictionaries/29_empty_dictionary.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity
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


@entity(description="Price tag", domain=ShopDomain)
class PriceTagCoreEntity(BaseCoreEntity):
    """Associate an amount with its currency."""

    id: str = Field(description="Tag identifier")
    amount: float = Field(description="Price amount")
    currency: CurrencyEnumEntity = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""

    class MoneyBaseEnumEntity(BaseEnumEntity):
        """Define shared fields without declaring a concrete dictionary."""

        symbol: str = Field(description="Currency symbol")

    print("Intermediate members:", MoneyBaseEnumEntity.members)
    try:

        @entity(description="Missing vocabulary", domain=ShopDomain)
        class EmptyEnumEntity(MoneyBaseEnumEntity):
            """Intentionally declare no values."""
    except ValueError as error:
        print(str(error))
    else:
        raise AssertionError("An empty dictionary was registered")


if __name__ == "__main__":
    main()
