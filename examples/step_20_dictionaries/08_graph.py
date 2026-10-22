"""The dictionary carries values in the graph.

Inspect the dictionary and a field that refers to it.
Run: uv run python examples/step_20_dictionaries/08_graph.py
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
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

    dictionary = EntityGraphNode(CurrencyEnumEntity)
    tag = EntityGraphNode(PriceTagCoreEntity)
    field = next(edge.target_node for edge in tag.entity_field_edges if edge.target_node.label == "currency")
    print("Kind:", dictionary.properties["entity_kind"])
    print("Values:", [value["code"] for value in dictionary.properties["values"]])
    print("Reference:", field.properties["reference_qualname"].split(".")[-1])


if __name__ == "__main__":
    main()
