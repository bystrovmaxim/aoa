"""The dictionary carries values and references in the graph.
Run: .venv/bin/python examples/step_20_dictionaries/08_graph.py


Inspect the dictionary, the field that refers to it, and the edge that carries the reference.
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
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

    dictionary = EntityGraphNode(CurrencyEnumEntity)
    tag = EntityGraphNode(PriceTagCoreEntity)
    field = next(edge.target_node for edge in tag.entity_field_edges if edge.target_node.label == "currency")
    reference = next(edge for edge in tag.relations if edge.properties["field_name"] == "currency")
    assert not tag.references
    assert reference.edge_name == "entity_relation"
    assert reference.properties["cardinality"] == "one"
    assert reference.properties["has_inverse"] is False
    print("Kind:", dictionary.properties["entity_kind"])
    print("Values:", [value["code"] for value in dictionary.properties["values"]])
    print("Reference:", field.properties["reference_qualname"].split(".")[-1])
    print("Edge:", reference.edge_name, "->", reference.target_node_id.split(".")[-1])


if __name__ == "__main__":
    main()
