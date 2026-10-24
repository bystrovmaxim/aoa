"""A blank reference code is malformed.
Run: .venv/bin/python examples/step_20_dictionaries/24_blank_reference.py


Whitespace cannot identify a value.
"""

from typing import Annotated

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
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
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""
    try:
        PriceTagCoreEntity(id="tag-1", amount=1.0, currency=AssociationOne(id=" "))
    except ValidationError as error:
        assert error.errors()[0]["loc"] == ("currency",)
        assert (
            error.errors()[0]["msg"]
            == "Value error, a dictionary association id must be a non-empty string code, got ' '."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid reference was accepted")


if __name__ == "__main__":
    main()
