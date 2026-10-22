"""Resolve a storage code explicitly.

The database column is called money_unit; the domain field is called currency.
Run: uv run python examples/step_20_dictionaries/04_storage_mapping.py
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
    from aoa.action_machine.domain import build

    row = {"tag_key": "tag-1", "price": 9.99, "money_unit": "eur"}
    value = CurrencyEnumEntity.by_code(row["money_unit"])
    tag = build(
        row,
        PriceTagCoreEntity,
        lambda fields, data: {
            fields.id: data["tag_key"],
            fields.amount: data["price"],
            fields.currency: value,
        },
    )
    print(tag.id, tag.currency.code)
    print("Shared value:", tag.currency is CurrencyEnumEntity.EUR)


if __name__ == "__main__":
    main()
