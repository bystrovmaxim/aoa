"""Dictionary values and references survive the ERD query without a demo dependency."""

from typing import Any

import pytest

from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_DOMAIN = "shop.ShopDomain"
_CURRENCY = "shop.CurrencyEnumEntity"
_TAG = "shop.PriceTagCoreEntity"
_VALUES = [
    {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}},
    {"code": "usd", "display_name": "US dollar", "properties": {"symbol": "$"}},
]


@pytest.fixture(scope="module")
def diagram() -> dict[str, Any]:
    """Query a small graph containing a dictionary and one referring field."""
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"id": _DOMAIN, "type": "Domain", "label": "ShopDomain", "properties": {"name": "shop", "description": "Shop"}},
            {"id": _CURRENCY, "type": "Entity", "label": "CurrencyEnumEntity", "properties": {"description": "Currencies", "entity_kind": "enum", "values": _VALUES}},
            {"id": _TAG, "type": "Entity", "label": "PriceTagCoreEntity", "properties": {"description": "Tag", "entity_kind": "core"}},
            {"id": _TAG + ":currency", "type": "EntityField", "label": "currency", "properties": {"field_type": "CurrencyEnumEntity", "primary_key_hint": False, "reference_qualname": _CURRENCY}},
        ],
        "edges": [
            *({"source_id": identifier, "target_id": _DOMAIN, "type": "domain", "relationship": "Composition", "is_dag": False} for identifier in (_CURRENCY, _TAG)),
            {"source_id": _TAG, "target_id": _TAG + ":currency", "type": "entity_field", "relationship": "Composition", "is_dag": False, "properties": {"ordinal": 0, "field_name": "currency"}},
        ],
    }
    store = DuckDBGraphResource.build_from_json(graph)
    return ListEntitiesAction._slice_payload(store, _DOMAIN, include_neighbors=False)


def test_the_dictionary_row_carries_its_values(diagram: dict[str, Any]) -> None:
    """A card retains declaration order, labels and descriptive properties."""
    currency = next(item for item in diagram["entities"] if item["id"] == _CURRENCY)
    assert currency["entity_kind"] == "enum"
    assert currency["values"] == [
        {"code": "eur", "display_name": "Euro", "properties": [{"name": "symbol", "value": "€"}]},
        {"code": "usd", "display_name": "US dollar", "properties": [{"name": "symbol", "value": "$"}]},
    ]


def test_a_plain_entity_carries_no_values(diagram: dict[str, Any]) -> None:
    """A business object does not acquire a dictionary catalogue."""
    tag = next(item for item in diagram["entities"] if item["id"] == _TAG)
    assert tag["values"] == []


def test_a_reference_field_names_its_dictionary(diagram: dict[str, Any]) -> None:
    """The renderer can identify the referenced class without domain knowledge."""
    tag = next(item for item in diagram["entities"] if item["id"] == _TAG)
    assert tag["fields"][0]["reference_qualname"] == _CURRENCY
