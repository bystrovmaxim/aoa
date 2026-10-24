# packages/aoa-action-machine/tests/action_machine/graph/test_dictionary_relation_containers.py
"""
Dictionary relations support all six ordinary containers, to-one and to-many.

To-one containers resolve an id to the canonical declared member; to-many containers resolve
every id in input order. Unknown, blank or wrong-typed codes and foreign or mismatched supplied
members are refused with item paths. Transport and both schema modes are covered, and the graph
projection keeps the declared role family and cardinality without a duplicate reference edge.
"""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import Field, ValidationError

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
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity


class ContainerDomain(BaseDomain):
    """Domain for the six-container dictionary fixtures."""

    name = "containers"
    description = "Containers"


@entity(description="Currency", domain=ContainerDomain)
class ContainerCurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@exclude_graph_model
@entity(description="Host", domain=ContainerDomain)
class ContainerHostCoreEntity(BaseCoreEntity):
    """A host selecting the dictionary through all six ordinary containers."""

    id: str = Field(description="Identifier")
    a_one: Annotated[AssociationOne[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Association one")
    ag_one: Annotated[AggregateOne[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Aggregate one")
    c_one: Annotated[CompositeOne[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Composite one")
    a_many: Annotated[AssociationMany[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Association many")
    ag_many: Annotated[AggregateMany[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Aggregate many")
    c_many: Annotated[CompositeMany[ContainerCurrencyEnumEntity], NoInverse()] = Field(description="Composite many")


_CONTAINERS: dict[str, type[Any]] = {
    "AssociationOne": AssociationOne,
    "AggregateOne": AggregateOne,
    "CompositeOne": CompositeOne,
    "AssociationMany": AssociationMany,
    "AggregateMany": AggregateMany,
    "CompositeMany": CompositeMany,
}

_ONE_FIELD = {"AssociationOne": "a_one", "AggregateOne": "ag_one", "CompositeOne": "c_one"}
_MANY_FIELD = {"AssociationMany": "a_many", "AggregateMany": "ag_many", "CompositeMany": "c_many"}

_ONE = list(_ONE_FIELD)
_MANY = list(_MANY_FIELD)


def _make_host(**overrides: Any) -> ContainerHostCoreEntity:
    """Build a valid host, letting one field be overridden."""
    base: dict[str, Any] = {
        "id": "h1",
        "a_one": AssociationOne(id="eur"),
        "ag_one": AggregateOne(id="eur"),
        "c_one": CompositeOne(id="eur"),
        "a_many": AssociationMany(ids=("eur", "usd")),
        "ag_many": AggregateMany(ids=("eur",)),
        "c_many": CompositeMany(ids=("usd",)),
    }
    base.update(overrides)
    return ContainerHostCoreEntity(**base)


def test_all_six_containers_are_accepted_for_a_dictionary() -> None:
    """Every ordinary container is now a legal dictionary relationship."""
    validate_entity_fields([ContainerHostCoreEntity, ContainerCurrencyEnumEntity])


@pytest.mark.parametrize("container", _ONE)
def test_to_one_containers_resolve_the_member(container: str) -> None:
    """Each to-one container resolves the id to the canonical member and keeps its class."""
    field = _ONE_FIELD[container]
    host = _make_host(**{field: _CONTAINERS[container](id="eur")})
    value = getattr(host, field)

    assert type(value).__name__ == container
    assert value.entity is ContainerCurrencyEnumEntity.EUR
    assert value.id == value.entity.code


@pytest.mark.parametrize("container", _MANY)
def test_to_many_containers_resolve_every_id_in_order(container: str) -> None:
    """Each to-many container resolves every id, in input order, retaining its class."""
    field = _MANY_FIELD[container]
    host = _make_host(**{field: _CONTAINERS[container](ids=("usd", "eur"))})
    value = getattr(host, field)

    assert type(value).__name__ == container
    assert value.ids == ("usd", "eur")
    assert [member.code for member in value.entities] == ["usd", "eur"]
    assert value.is_loaded is True


@pytest.mark.parametrize("container", _ONE + _MANY)
def test_an_unknown_code_is_refused(container: str) -> None:
    """An id naming no declared value is refused, with an item path on to-many."""
    field = (_ONE_FIELD | _MANY_FIELD)[container]
    with pytest.raises(ValidationError, match="not a declared value"):
        _make_host(**{field: _CONTAINERS[container](id="xxx") if container in _ONE else _CONTAINERS[container](ids=("xxx",))})


@pytest.mark.parametrize("container", _ONE + _MANY)
def test_a_blank_or_wrong_type_code_is_refused(container: str) -> None:
    """A non-string or blank id is not a code shortcut."""
    field = (_ONE_FIELD | _MANY_FIELD)[container]
    bad = _CONTAINERS[container](id=7) if container in _ONE else _CONTAINERS[container](ids=(7,))
    with pytest.raises(ValidationError, match="non-empty string code"):
        _make_host(**{field: bad})


def test_a_mismatched_supplied_member_is_refused() -> None:
    """A supplied member whose code disagrees with the id is refused, with the item path."""
    with pytest.raises(ValidationError, match="item 0: the supplied entity is not the declared value"):
        _make_host(a_many=AssociationMany(ids=("eur",), entities=(ContainerCurrencyEnumEntity.USD,)))


def test_a_copy_of_a_member_is_refused() -> None:
    """A constructed copy is not the declared value."""
    copy = ContainerCurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")

    with pytest.raises(ValidationError, match="not the declared value"):
        _make_host(c_one=CompositeOne(id="eur", entity=copy))


def test_an_empty_to_many_selection_is_loaded_and_empty() -> None:
    """An empty selection is a completed load of zero rows, not an unloaded state."""
    host = _make_host(a_many=AssociationMany(ids=()))

    assert host.a_many.ids == ()
    assert host.a_many.entities == ()
    assert host.a_many.is_loaded is True


def test_the_input_wrapper_is_not_mutated() -> None:
    """The caller's wrapper stays id-only; the validated field receives a new wrapper."""
    wrapper = AssociationMany(ids=("eur",))

    host = _make_host(a_many=wrapper)

    assert wrapper.entities == ()
    assert host.a_many is not wrapper
    assert [member.code for member in host.a_many.entities] == ["eur"]


def test_json_transport_round_trips_to_one_and_to_many() -> None:
    """The id-object and id-array inputs resolve, and the output is the member reference."""
    host = ContainerHostCoreEntity.model_validate_json(
        '{"id": "h2", "a_one": {"id": "eur"}, "ag_one": {"id": "eur"}, "c_one": {"id": "eur"},'
        ' "a_many": [{"id": "eur"}, {"id": "usd"}], "ag_many": [{"id": "eur"}], "c_many": [{"id": "usd"}]}'
    )

    assert host.a_one.entity is ContainerCurrencyEnumEntity.EUR
    assert [member.code for member in host.a_many.entities] == ["eur", "usd"]
    dumped = host.model_dump(mode="json")
    assert dumped["a_one"] == ContainerCurrencyEnumEntity.EUR.to_reference()
    assert dumped["a_many"] == [
        ContainerCurrencyEnumEntity.EUR.to_reference(),
        ContainerCurrencyEnumEntity.USD.to_reference(),
    ]


def test_both_schema_modes_describe_input_and_reference() -> None:
    """Validation describes the input shape; serialization describes the emitted reference."""
    validation = ContainerHostCoreEntity.model_json_schema(mode="validation")["properties"]
    serialization = ContainerHostCoreEntity.model_json_schema(mode="serialization")["properties"]

    assert validation["a_one"]["type"] == "object"
    assert validation["a_one"]["required"] == ["id"]
    assert validation["a_many"]["type"] == "array"
    assert validation["a_many"]["items"]["required"] == ["id"]

    assert set(serialization["a_one"]["required"]) == {"code", "display_name", "properties"}
    assert serialization["a_many"]["type"] == "array"
    assert set(serialization["a_many"]["items"]["required"]) == {"code", "display_name", "properties"}


def test_graph_projection_keeps_role_family_and_cardinality() -> None:
    """The graph keeps each declared role family/cardinality and emits no duplicate reference edge."""
    node = EntityGraphNode(ContainerHostCoreEntity)
    edges = {edge.properties["field_name"]: edge for edge in node.relations}

    assert edges["a_one"].properties["relation_type"] == "association"
    assert edges["a_one"].properties["cardinality"] == "one"
    assert edges["c_one"].properties["relation_type"] == "composition"
    assert edges["c_one"].properties["cardinality"] == "one"
    assert edges["a_many"].properties["relation_type"] == "association"
    assert edges["a_many"].properties["cardinality"] == "many"
    assert edges["ag_many"].properties["relation_type"] == "aggregation"
    assert edges["ag_many"].properties["cardinality"] == "many"
    assert edges["c_many"].properties["description"] == "Composite many"
    assert node.references == []
