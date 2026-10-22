"""A declared value cannot be edited.

Many objects may share EUR, so changing its label through one reference must fail.
Run: uv run python examples/step_20_dictionaries/07_frozen.py
"""

from pydantic import Field, ValidationError

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
    try:
        CurrencyEnumEntity.EUR.display_name = "Changed"
    except ValidationError as error:
        print(error.errors()[0]["type"])
    else:
        raise AssertionError("The shared value was modified")
    print(CurrencyEnumEntity.EUR.display_name)


if __name__ == "__main__":
    main()
