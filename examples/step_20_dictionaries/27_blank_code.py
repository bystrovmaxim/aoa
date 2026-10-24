"""A declared code cannot be blank.
Run: .venv/bin/python examples/step_20_dictionaries/27_blank_code.py


Declare a value with a whitespace-only code.
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

        class BlankEnumEntity(BaseEnumEntity):
            """Intentionally omit meaningful identity or label text."""

            VALUE = value(code=" ", display_name="Label")
    except ValidationError as error:
        print(error.errors()[0]["loc"][0])
        print(error.errors()[0]["msg"])
    else:
        raise AssertionError("A blank field was accepted")


if __name__ == "__main__":
    main()
