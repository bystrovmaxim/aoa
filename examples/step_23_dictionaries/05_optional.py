"""An absent reference is None.
Run: .venv/bin/python examples/step_23_dictionaries/05_optional.py


A quote may have no settlement currency yet.
"""

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, BaseEnumEntity, NoInverse, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class ShopDomain(BaseDomain):
    """Group the shop declarations."""

    name = "shop"
    description = "Shop model"


@meta(description="Stores the shop entities", domain=ShopDomain)
class ShopStorage(BaseStorage):
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

    class QuoteCoreEntity(BaseCoreEntity):
        """Allow an explicitly absent settlement currency."""

        currency: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(
            default=None, description="Settlement unit"
        )

    quote = QuoteCoreEntity()
    print("Absent:", quote.currency is None)
    assert quote.currency is None


if __name__ == "__main__":
    main()
