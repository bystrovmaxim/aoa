"""A bare code is refused.
Run: .venv/bin/python examples/step_23_dictionaries/20_bare_code.py


Pass a string directly into the typed currency field.
"""

from typing import Annotated

from pydantic import Field, ValidationError

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.resources import InMemoryDataSource


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Where ShopStorage keeps its rows")
class ShopDataSource(InMemoryDataSource):
    """The store ShopStorage works with."""


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage[ShopDataSource]):
    """Hold the shop entities."""


@entity(description="Currencies accepted by the shop", resource=ShopStorage)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the shop's currency vocabulary."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@entity(description="Price tag", resource=ShopStorage)
class PriceTagCoreEntity(BaseCoreEntity):
    """Associate an amount with its currency."""

    id: str = Field(description="Tag identifier")
    amount: float = Field(description="Price amount")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""
    try:
        PriceTagCoreEntity(id="tag-1", amount=1.0, currency="eur")
    except ValidationError as error:
        assert error.errors()[0]["loc"] == ("currency",)
        assert error.errors()[0]["msg"].startswith(
            "Value error, a dictionary relation takes its container, an id object {'id': code} or a reference"
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("The invalid reference was accepted")


if __name__ == "__main__":
    main()
