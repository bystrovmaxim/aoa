"""Duplicate codes are refused.

Two names in one dictionary try to claim the same code.
Run: uv run python examples/step_20_dictionaries/26_duplicate_code.py
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
    try:

        class DuplicateEnumEntity(BaseEnumEntity):
            """Intentionally give two values one identity."""

            FIRST = DuplicateEnumEntity(code="same", display_name="First")  # noqa: F821
            SECOND = DuplicateEnumEntity(code="same", display_name="Second")  # noqa: F821
    except ValueError as error:
        print(str(error))
    else:
        raise AssertionError("Duplicate codes were accepted")


if __name__ == "__main__":
    main()
