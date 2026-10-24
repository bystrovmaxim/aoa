"""Select dictionary members through all six ordinary relationship containers.
Run: .venv/bin/python examples/step_21_relations/72_role_dictionary.py
"""

from typing import Annotated

from pydantic import Field, ValidationError, field_serializer

from aoa.action_machine.domain import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    CompositeMany,
    CompositeOne,
    NoInverse,
    value,
)
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class DictionaryDomain(BaseDomain):
    """Group the currency selection declarations."""

    name = "dictionary-endpoints"
    description = "Dictionary endpoints"


@entity(description="Currencies", domain=DictionaryDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the canonical currencies and an exported property."""

    symbol: str = Field(description="Currency symbol")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")

    @field_serializer("symbol")
    def serialize_symbol(self, symbol: str) -> str:
        """Make the custom property serializer visible in export."""
        return "Currency " + symbol


@entity(description="Price list", domain=DictionaryDomain)
class PriceListCoreEntity(BaseCoreEntity):
    """Demonstrate the six roles without a dictionary-only role restriction."""

    primary: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Primary currency")
    quoted: Annotated[AggregateOne[CurrencyEnumEntity], NoInverse()] = Field(description="Quoted currency")
    snapshot: Annotated[CompositeOne[CurrencyEnumEntity], NoInverse()] = Field(description="Snapshot currency")
    alternatives: Annotated[AssociationMany[CurrencyEnumEntity], NoInverse()] = Field(description="Alternatives")
    available: Annotated[AggregateMany[CurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Available currencies"
    )
    bundled: Annotated[CompositeMany[CurrencyEnumEntity], NoInverse()] = Field(description="Bundled currencies")


def python_selection() -> None:
    """Normalize explicit wrappers without changing the caller's values."""
    original = AssociationMany(ids=("usd", "eur", "usd"))
    price = PriceListCoreEntity(
        primary=AssociationOne(id="eur"),
        quoted=AggregateOne(id="usd"),
        snapshot=CompositeOne(id="eur"),
        alternatives=original,
        available=AggregateMany(ids=("usd",)),
        bundled=CompositeMany(ids=()),
    )
    assert price.primary.entity is CurrencyEnumEntity.EUR
    assert type(price.quoted) is AggregateOne and price.quoted.entity is CurrencyEnumEntity.USD
    assert type(price.snapshot) is CompositeOne and price.snapshot.entity is CurrencyEnumEntity.EUR
    assert price.alternatives.entities == (CurrencyEnumEntity.USD, CurrencyEnumEntity.EUR, CurrencyEnumEntity.USD)
    assert all(
        member is CurrencyEnumEntity.by_code(code)
        for code, member in zip(price.alternatives.ids, price.alternatives.entities, strict=True)
    )
    assert price.alternatives is not original and original.entities == () and not original.is_loaded
    assert type(price.available) is AggregateMany and price.available.entities == (CurrencyEnumEntity.USD,)
    assert type(price.bundled) is CompositeMany and price.bundled.is_loaded and price.bundled.entities == ()
    print("All six container classes retained")
    print("Selection order and repeats:", price.alternatives.ids)
    print("Caller loaded:", original.is_loaded, "validated loaded:", price.alternatives.is_loaded)
    print("Empty selection:", price.bundled.entities, "loaded:", price.bundled.is_loaded)


def json_transport() -> None:
    """Resolve arrays of id objects and export arrays of member references."""
    price = PriceListCoreEntity.model_validate_json(
        '{"primary":{"id":"eur"},"quoted":{"id":"usd"},"snapshot":{"id":"eur"},'
        '"alternatives":[{"id":"usd"},{"id":"eur"}],"bundled":[]}'
    )
    assert price.available is None
    assert price.alternatives.entities[0] is CurrencyEnumEntity.USD
    exported = price.model_dump(mode="json")
    assert exported["alternatives"] == [CurrencyEnumEntity.USD.to_reference(), CurrencyEnumEntity.EUR.to_reference()]
    assert exported["alternatives"][0]["properties"] == {"symbol": "Currency $"}
    assert exported["bundled"] == [] and exported["available"] is None
    print("Exported selections:", exported["alternatives"])
    print("Empty export:", exported["bundled"], "absent export:", exported["available"])
    validation = PriceListCoreEntity.model_json_schema(mode="validation")["properties"]
    serialization = PriceListCoreEntity.model_json_schema(mode="serialization")["properties"]
    assert validation["alternatives"]["type"] == serialization["alternatives"]["type"] == "array"
    assert validation["alternatives"]["items"]["required"] == ["id"]
    assert serialization["alternatives"]["items"]["required"] == ["code", "display_name", "properties"]
    print("Input item keys:", validation["alternatives"]["items"]["required"])
    print("Output item keys:", serialization["alternatives"]["items"]["required"])


def invalid_selections() -> None:
    """Refuse an unknown indexed code and a mismatched supplied member."""
    try:
        PriceListCoreEntity.model_validate_json(
            '{"primary":{"id":"eur"},"quoted":{"id":"usd"},"snapshot":{"id":"eur"},'
            '"alternatives":[{"id":"eur"},{"id":"xxx"}],"bundled":[]}'
        )
    except ValidationError as error:
        assert (
            str(error)
            == "1 validation error for PriceListCoreEntity\nalternatives\n  Value error, item 1: 'xxx' is not a declared value of CurrencyEnumEntity. Declared: ['eur', 'usd']. [type=value_error, input_value=[{'id': 'eur'}, {'id': 'xxx'}], input_type=list]\n    For further information visit https://errors.pydantic.dev/2.12/v/value_error"
        )
        assert error.errors()[0]["loc"] == ("alternatives",)
        assert (
            error.errors()[0]["msg"]
            == "Value error, item 1: 'xxx' is not a declared value of CurrencyEnumEntity. Declared: ['eur', 'usd']."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("Unknown dictionary member was accepted")
    try:
        PriceListCoreEntity(
            primary=AssociationOne(id="eur"),
            quoted=AggregateOne(id="usd"),
            snapshot=CompositeOne(id="eur"),
            alternatives=AssociationMany(ids=("eur",), entities=(CurrencyEnumEntity.USD,)),
            bundled=CompositeMany(ids=()),
        )
    except ValidationError as error:
        assert (
            str(error)
            == "1 validation error for PriceListCoreEntity\nalternatives\n  Value error, item 0: the supplied entity is not the declared value for code 'eur'. [type=value_error, input_value=AssociationMany(count=1, ...oaded=yes, n_entities=1), input_type=AssociationMany]\n    For further information visit https://errors.pydantic.dev/2.12/v/value_error"
        )
        assert (
            error.errors()[0]["msg"]
            == "Value error, item 0: the supplied entity is not the declared value for code 'eur'."
        )
        print(type(error).__name__ + ": " + str(error))
    else:
        raise AssertionError("Mismatched canonical member was accepted")


def graph_roles() -> None:
    """Preserve all six kinds and cardinalities in the public graph projection."""
    node = EntityGraphNode(PriceListCoreEntity)
    edges = {edge.properties["field_name"]: edge for edge in node.relations}
    actual = {name: (edge.properties["relation_type"], edge.properties["cardinality"]) for name, edge in edges.items()}
    assert actual == {
        "primary": ("association", "one"),
        "quoted": ("aggregation", "one"),
        "snapshot": ("composition", "one"),
        "alternatives": ("association", "many"),
        "available": ("aggregation", "many"),
        "bundled": ("composition", "many"),
    }
    assert all(edge.properties["has_inverse"] is False for edge in edges.values())
    assert node.references == [] and len(node.relations) == 6
    rows = {edge.target_node.label: edge.target_node for edge in node.entity_field_edges}
    assert all(rows[name].properties["reference_qualname"].endswith("CurrencyEnumEntity") for name in actual)
    print("Graph roles:", actual)


def main() -> None:
    """Run Python values, JSON transport, refusals and graph projection."""
    python_selection()
    json_transport()
    invalid_selections()
    graph_roles()


if __name__ == "__main__":
    main()
