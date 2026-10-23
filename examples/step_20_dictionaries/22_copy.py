"""A constructed copy is refused.

Construct a new object with the same fields as EUR, then try to use it as a reference.
Run: uv run python examples/step_20_dictionaries/22_copy.py
"""

from pydantic import Field, ValidationError

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
    try:
        PriceTagCoreEntity(
            id="tag-1", amount=1.0, currency=CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")
        )
    except ValidationError as error:
        print("Field:", error.errors()[0]["loc"][0])
        print(error.errors()[0]["msg"])
    else:
        raise AssertionError("The invalid reference was accepted")


if __name__ == "__main__":
    main()
