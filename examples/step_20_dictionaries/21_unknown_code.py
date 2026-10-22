"""An unknown reference code is refused.

The producer sends a code outside the declared vocabulary.
Run: uv run python examples/step_20_dictionaries/21_unknown_code.py
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
        PriceTagCoreEntity(id="tag-1", amount=1.0, currency={"code": "unknown"})
    except ValidationError as error:
        print("Field:", error.errors()[0]["loc"][0])
        print(error.errors()[0]["msg"])
    else:
        raise AssertionError("The invalid reference was accepted")


if __name__ == "__main__":
    main()
