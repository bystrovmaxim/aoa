"""Dictionary values and references survive the ERD query without a demo dependency."""

import json
from typing import Any

import jsonschema
import pytest

from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_entities_action_schema import ListEntitiesDomainSlicesJson
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_DOMAIN = "shop.ShopDomain"
_CURRENCY = "shop.CurrencyEnumEntity"
_TAG = "shop.PriceTagCoreEntity"
_VALUES = [
    {"code": "eur", "display_name": "Euro", "properties": {"symbol": "€"}},
    {"code": "usd", "display_name": "US dollar", "properties": {"symbol": "$"}},
]

_SCHEMA: dict[str, Any] = ListEntitiesDomainSlicesJson._json_schema
_RICH_DOMAIN = "shop.ExtrasDomain"
_RICH_DICTIONARY = "shop.ExtrasEnumEntity"
_RICH_VALUES = [
    {"code": "two", "display_name": "Two", "properties": {"symbol": "€", "note": "<safe> & readable"}},
    {"code": "tagged", "display_name": "Tagged", "properties": {"tags": ["a", "b"]}},
    {"code": "blank", "display_name": "Blank", "properties": {"note": ""}},
    {"code": "nulled", "display_name": "Nulled", "properties": {"note": None}},
    {"code": "bare", "display_name": "Bare", "properties": {}},
]
_RICH_EXPECTED = [
    {
        "code": "two",
        "display_name": "Two",
        "properties": [
            {"name": "symbol", "value": "€"},
            {"name": "note", "value": "<safe> & readable"},
        ],
    },
    {"code": "tagged", "display_name": "Tagged", "properties": [{"name": "tags", "value": '["a", "b"]'}]},
    {"code": "blank", "display_name": "Blank", "properties": [{"name": "note", "value": ""}]},
    {"code": "nulled", "display_name": "Nulled", "properties": [{"name": "note", "value": "null"}]},
    {"code": "bare", "display_name": "Bare", "properties": []},
]


@pytest.fixture(scope="module")
def diagram() -> dict[str, Any]:
    """Query a small graph containing a dictionary and one referring field."""
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"id": _DOMAIN, "type": "Domain", "label": "ShopDomain", "properties": {"name": "shop", "description": "Shop"}},
            {"id": _CURRENCY, "type": "Entity", "label": "CurrencyEnumEntity", "properties": {"description": "Currencies", "entity_kind": "enum", "values": _VALUES}},
            {"id": _CURRENCY + ":code", "type": "EntityField", "label": "code", "properties": {"field_type": "str", "primary_key_hint": False}},
            {"id": _CURRENCY + ":display_name", "type": "EntityField", "label": "display_name", "properties": {"field_type": "str", "primary_key_hint": False}},
            {"id": _TAG, "type": "Entity", "label": "PriceTagCoreEntity", "properties": {"description": "Tag", "entity_kind": "core"}},
            {"id": _TAG + ":currency", "type": "EntityField", "label": "currency", "properties": {"field_type": "CurrencyEnumEntity", "primary_key_hint": False, "reference_qualname": _CURRENCY}},
        ],
        "edges": [
            *({"source_id": identifier, "target_id": _DOMAIN, "type": "domain", "relationship": "Composition", "is_dag": False} for identifier in (_CURRENCY, _TAG)),
            {"source_id": _CURRENCY, "target_id": _CURRENCY + ":code", "type": "entity_field", "relationship": "Composition", "is_dag": False, "properties": {"ordinal": 0, "field_name": "code"}},
            {"source_id": _CURRENCY, "target_id": _CURRENCY + ":display_name", "type": "entity_field", "relationship": "Composition", "is_dag": False, "properties": {"ordinal": 1, "field_name": "display_name"}},
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


@pytest.fixture(scope="module")
def rich_diagram() -> dict[str, Any]:
    """Query a graph whose dictionary carries every property shape the card must show."""
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"id": _RICH_DOMAIN, "type": "Domain", "label": "ExtrasDomain", "properties": {"name": "extras", "description": "Extras"}},
            {"id": _RICH_DICTIONARY, "type": "Entity", "label": "ExtrasEnumEntity", "properties": {"description": "Extras", "entity_kind": "enum", "values": _RICH_VALUES}},
        ],
        "edges": [
            {"source_id": _RICH_DICTIONARY, "target_id": _RICH_DOMAIN, "type": "domain", "relationship": "Composition", "is_dag": False},
        ],
    }
    store = DuckDBGraphResource.build_from_json(graph)
    return ListEntitiesAction._slice_payload(store, _RICH_DOMAIN, include_neighbors=False)


def _property_items(properties: dict[str, Any]) -> list[dict[str, str]]:
    """Render one property mapping the way the action renders it."""
    return [
        {"name": name, "value": item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)}
        for name, item in properties.items()
    ]


def _assert_one_item_per_property(values: list[dict[str, Any]], declared: list[dict[str, Any]]) -> None:
    """Assert that every declared property produced exactly one payload item."""
    for value, source in zip(values, declared, strict=True):
        assert len(value["properties"]) == len(source["properties"]), f"{value['code']} lost a property"


def test_every_property_shape_reaches_the_payload(rich_diagram: dict[str, Any]) -> None:
    """Strings, arrays, an empty string, `None` and no properties at all each keep their text form."""
    dictionary = next(item for item in rich_diagram["entities"] if item["id"] == _RICH_DICTIONARY)

    assert dictionary["values"] == _RICH_EXPECTED


def test_every_property_item_is_a_name_value_string_pair(rich_diagram: dict[str, Any]) -> None:
    """The payload carries a typed list, not a mapping and not a JSON string."""
    dictionary = next(item for item in rich_diagram["entities"] if item["id"] == _RICH_DICTIONARY)

    for value in dictionary["values"]:
        for item in value["properties"]:
            assert set(item) == {"name", "value"}
            assert isinstance(item["name"], str)
            assert isinstance(item["value"], str)


def test_the_rich_payload_satisfies_the_contract(rich_diagram: dict[str, Any]) -> None:
    """The strict schema accepts every shape the action emits, with no edit to the schema."""
    row = {"domain_label": "Extras", "domain_qualname": _RICH_DOMAIN, "list_entities": rich_diagram}
    jsonschema.validate([row], _SCHEMA)


def test_the_payload_keeps_one_item_per_graph_property(rich_diagram: dict[str, Any]) -> None:
    """The invariant behind the card: nothing disappears between the graph and the payload."""
    dictionary = next(item for item in rich_diagram["entities"] if item["id"] == _RICH_DICTIONARY)

    _assert_one_item_per_property(dictionary["values"], _RICH_VALUES)


def test_a_lossy_conversion_is_caught_by_the_invariant(rich_diagram: dict[str, Any]) -> None:
    """A conversion that drops a member fails the count assertion instead of passing silently."""
    dictionary = next(item for item in rich_diagram["entities"] if item["id"] == _RICH_DICTIONARY)
    lossy = [
        {**value, "properties": _property_items(source["properties"])[:-1]}
        for value, source in zip(dictionary["values"], _RICH_VALUES, strict=True)
    ]

    with pytest.raises(AssertionError, match="lost a property"):
        _assert_one_item_per_property(lossy, _RICH_VALUES)

def test_a_dictionary_card_drops_the_rows_the_kind_supplies(diagram: dict[str, Any]) -> None:
    """A reader sees labels, not storage identity: the two kind rows never reach the card."""
    currency = next(item for item in diagram["entities"] if item["id"] == _CURRENCY)

    assert currency["fields"] == []


def test_a_dictionary_value_keeps_its_code_in_the_payload(diagram: dict[str, Any]) -> None:
    """Dropping the printed rows must not drop the data the graph and the exports keep."""
    currency = next(item for item in diagram["entities"] if item["id"] == _CURRENCY)

    assert [value["code"] for value in currency["values"]] == ["eur", "usd"]
    assert [value["display_name"] for value in currency["values"]] == ["Euro", "US dollar"]


def test_a_plain_entity_keeps_every_field_row(diagram: dict[str, Any]) -> None:
    """The projection belongs to the dictionary kind alone."""
    tag = next(item for item in diagram["entities"] if item["id"] == _TAG)

    assert [field["name"] for field in tag["fields"]] == ["currency"]
