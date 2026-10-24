"""A reference carries its description.
Run: .venv/bin/python examples/step_20_dictionaries/03_serialization.py


Serialize a price so a reader without the Python model can understand its currency.
"""

from typing import Annotated

from pydantic import Field

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
    tag = PriceTagCoreEntity(
        id="tag-1", amount=9.99, currency=AssociationOne(id=CurrencyEnumEntity.EUR.code, entity=CurrencyEnumEntity.EUR)
    )
    print(tag.model_dump(mode="json")["currency"])
    # The reference form is the JSON export; a Python-mode dump may keep a native value.
    assert tag.model_dump(mode="json")["currency"] == CurrencyEnumEntity.EUR.to_reference()


if __name__ == "__main__":
    main()
