"""Read dictionary values in the ERD payload.
Run: uv run python examples/step_20_dictionaries/09_erd.py

Follow one dictionary through the actual Maxitor query.
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseEnumEntity, value
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
    currency: CurrencyEnumEntity = Field(description="Money unit")


def main() -> None:
    """Run this one learning experiment."""
    import json

    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
    from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
    from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

    machine = ActionProductMachine(loggers=[])
    domain = next(node.node_id for node in machine.graph_coordinator.get_all_nodes() if node.label == "ShopDomain")
    store = DuckDBGraphResource.build_from_json(json.loads(machine.graph_coordinator.to_json()))
    diagram = ListEntitiesAction._slice_payload(store, domain, include_neighbors=False)
    currency = next(item for item in diagram["entities"] if item["label"] == "CurrencyEnumEntity")
    tag = next(item for item in diagram["entities"] if item["label"] == "PriceTagCoreEntity")
    relation = next(item for item in diagram["relations"] if item["relationship_kind"] == "reference")
    print(currency["values"][0])
    print(next(field["reference_qualname"] for field in tag["fields"] if field["name"] == "currency").split(".")[-1])
    print("Relation:", relation["label"], "->", relation["target"].split(".")[-1])


if __name__ == "__main__":
    main()
