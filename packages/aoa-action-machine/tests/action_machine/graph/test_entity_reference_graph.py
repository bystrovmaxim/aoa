# tests/action_machine/graph/test_entity_reference_graph.py
"""
Tests for ``entity_reference`` — a dictionary reference reaches the graph as an edge.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Until this change a field typed by a dictionary produced a column and nothing else: a
consumer walking edges could not find the dictionary the model declares. These tests pin
the edge, its properties, its target and the one case the rule refuses — a dictionary that
has no node, which would otherwise leave a dangling target.

Every host and every classification fixture is ``@exclude_graph_model`` so it never joins
the global model other tests build; the dictionaries are graph models, because the edge is
emitted only for a target the graph carries.
"""

from __future__ import annotations

from typing import Annotated

import jsonschema
import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    Specialization,
    value,
)
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ReferenceDomain(BaseDomain):
    """The domain every fixture in this module belongs to."""

    name = "reference"
    description = "Reference"


@entity(description="Currency reference value", domain=ReferenceDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A dictionary a field can reference."""

    EUR = value(code="eur", display_name="Euro")
    USD = value(code="usd", display_name="US dollar")


@exclude_graph_model
@entity(description="Reference host", domain=ReferenceDomain)
class ReferenceHostCoreEntity(BaseCoreEntity):
    """Reference the dictionary as a required and as an optional value."""

    id: str = Field(description="Identifier")
    currency: CurrencyEnumEntity = Field(description="Required reference")
    settlement: CurrencyEnumEntity | None = Field(default=None, description="Optional reference")


@exclude_graph_model
@entity(description="Spec host", domain=ReferenceDomain)
class SpecReferenceSpecEntity(BaseSpecEntity):
    """Reference a dictionary from a Spec host."""

    id: str = Field(description="Identifier")
    currency: CurrencyEnumEntity = Field(description="Currency")


@exclude_graph_model
@entity(description="Assoc host", domain=ReferenceDomain)
class AssocReferenceAssocEntity(BaseAssocEntity):
    """Reference a dictionary from an Assoc host."""

    id: str = Field(description="Identifier")
    currency: CurrencyEnumEntity = Field(description="Currency")


@exclude_graph_model
@entity(description="Detail host", domain=ReferenceDomain)
class DetailReferenceDetailEntity(BaseDetailEntity):
    """Reference a dictionary from a Detail host."""

    id: str = Field(description="Identifier")
    currency: CurrencyEnumEntity = Field(description="Currency")


@exclude_graph_model
@entity(description="Reference base", domain=ReferenceDomain)
class ReferenceBaseCoreEntity(BaseCoreEntity):
    """Declare the reference on a base class."""

    id: str = Field(description="Identifier")
    currency: CurrencyEnumEntity = Field(description="Currency")


@exclude_graph_model
@entity(description="Inherited reference", domain=ReferenceDomain)
class InheritedReferenceCoreEntity(ReferenceBaseCoreEntity):
    """Inherit the reference."""

    note: str = Field(description="Note")


@exclude_graph_model
@entity(description="Forward reference", domain=ReferenceDomain)
class ForwardReferenceCoreEntity(BaseCoreEntity):
    """Name its dictionary before that dictionary exists."""

    id: str = Field(description="Identifier")
    currency: LaterCurrencyEnumEntity = Field(description="Currency")


@entity(description="Later currency reference value", domain=ReferenceDomain)
class LaterCurrencyEnumEntity(BaseEnumEntity):
    """Be the dictionary the forward reference names."""

    USD = value(code="usd", display_name="US dollar")


@entity(description="Pressing kind reference value", domain=ReferenceDomain)
class PressingKindEnumEntity(BaseEnumEntity):
    """Classify the record's axis and be referenced by a field."""

    FIRST = value(code="first", display_name="First")
    REPRESS = value(code="repress", display_name="Repress")


@exclude_graph_model
@entity(description="Record", domain=ReferenceDomain)
class RecordCoreEntity(BaseCoreEntity):
    """Carry the specialization axis that borrows the dictionary."""

    id: str = Field(description="Record identifier")
    pressing: Annotated[
        Specialization[FirstPressSpecEntity | RepressSpecEntity, PressingKindEnumEntity],
        Inverse(field_name="record"),
    ] = Field(description="Details of this pressing")


@exclude_graph_model
@entity(description="First pressing", domain=ReferenceDomain)
class FirstPressSpecEntity(BaseSpecEntity):
    """Point back at the head with its variant."""

    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(variant=PressingKindEnumEntity.FIRST),
        Inverse(RecordCoreEntity, "pressing"),
    ] = Field(description="Record described by these pressing details")


@exclude_graph_model
@entity(description="Repress", domain=ReferenceDomain)
class RepressSpecEntity(BaseSpecEntity):
    """Point back at the head with its variant."""

    record: Annotated[
        Generalization[RecordCoreEntity],
        Classifier(variant=PressingKindEnumEntity.REPRESS),
        Inverse(RecordCoreEntity, "pressing"),
    ] = Field(description="Record described by these pressing details")


for _axis_model in (RecordCoreEntity, FirstPressSpecEntity, RepressSpecEntity):
    _axis_model.model_rebuild()


@exclude_graph_model
@entity(description="Axis dictionary reference", domain=ReferenceDomain)
class AxisReferenceCoreEntity(BaseCoreEntity):
    """Reference the very dictionary the axis borrows."""

    id: str = Field(description="Identifier")
    kind: PressingKindEnumEntity = Field(description="Kind")


@exclude_graph_model
@entity(description="Hidden currency reference value", domain=ReferenceDomain)
class HiddenEnumEntity(BaseEnumEntity):
    """Stay out of the graph on purpose."""

    USD = value(code="usd", display_name="US dollar")


@exclude_graph_model
@entity(description="Hidden dictionary reference", domain=ReferenceDomain)
class HiddenReferenceCoreEntity(BaseCoreEntity):
    """Reference a dictionary that is marked outside the graph."""

    id: str = Field(description="Identifier")
    currency: HiddenEnumEntity = Field(description="Currency")


def _twin(module: str) -> type[BaseEnumEntity]:
    """Return a dictionary named ``TwinEnumEntity`` in a module of its own."""
    twin = type(
        "TwinEnumEntity",
        (BaseEnumEntity,),
        {
            "__module__": module,
            "__doc__": "A dictionary sharing its short name with another.",
            "ONE": value(code="one", display_name="One"),
        },
    )
    return entity(description="Twin dictionary", domain=ReferenceDomain)(twin)


FirstTwinEnumEntity = _twin("tests.twin.one")
SecondTwinEnumEntity = _twin("tests.twin.two")


@exclude_graph_model
@entity(description="Twin host", domain=ReferenceDomain)
class TwinHostCoreEntity(BaseCoreEntity):
    """Reference two dictionaries whose short names are the same."""

    id: str = Field(description="Identifier")
    first: FirstTwinEnumEntity = Field(description="First twin")
    second: SecondTwinEnumEntity = Field(description="Second twin")


def _references(entity_cls: type) -> list:
    """Return the entity's reference edges."""
    return list(EntityGraphNode(entity_cls).references)


def test_each_reference_produces_one_edge() -> None:
    """One field, one edge, with the field name and the one cardinality."""
    node = EntityGraphNode(ReferenceHostCoreEntity)

    assert [edge.properties["field_name"] for edge in node.references] == ["currency", "settlement"]
    for edge in node.references:
        assert edge.edge_name == "entity_reference"
        assert edge.properties["cardinality"] == "one"
        assert edge.is_dag is False
        assert edge.target_node_id == TypeIntrospection.full_qualname(CurrencyEnumEntity)

    walked = [edge for edge in node.get_all_edges() if edge.edge_name == "entity_reference"]
    assert len(walked) == len(node.references)


def test_the_field_row_and_the_edge_name_the_same_dictionary() -> None:
    """The row and the edge are one reference projected twice."""
    node = EntityGraphNode(ReferenceHostCoreEntity)
    row = next(edge.target_node for edge in node.entity_field_edges if edge.target_node.label == "currency")

    assert row.properties["reference_qualname"] == TypeIntrospection.full_qualname(CurrencyEnumEntity)
    assert node.references[0].target_node_id == row.properties["reference_qualname"]


@pytest.mark.parametrize(
    "entity_cls",
    [SpecReferenceSpecEntity, AssocReferenceAssocEntity, DetailReferenceDetailEntity],
)
def test_a_reference_on_every_host_kind_produces_the_edge(entity_cls: type) -> None:
    """The host's kind does not change the reference."""
    edges = _references(entity_cls)

    assert [edge.properties["field_name"] for edge in edges] == ["currency"]
    assert edges[0].target_node_id == TypeIntrospection.full_qualname(CurrencyEnumEntity)


def test_an_inherited_reference_produces_the_edge() -> None:
    """An inherited field is carried exactly as a declared one."""
    edges = _references(InheritedReferenceCoreEntity)

    assert [edge.properties["field_name"] for edge in edges] == ["currency"]


def test_a_forward_referenced_dictionary_produces_the_edge() -> None:
    """After resolution the edge exists; before it, the field is not judged a scalar."""
    ForwardReferenceCoreEntity.model_rebuild()

    edges = _references(ForwardReferenceCoreEntity)

    assert [edge.target_node_id for edge in edges] == [TypeIntrospection.full_qualname(LaterCurrencyEnumEntity)]


def test_a_reference_and_an_axis_naming_the_same_dictionary_stay_distinct() -> None:
    """The axis borrows the vocabulary; the reference names the value."""
    head = EntityGraphNode(RecordCoreEntity)
    assert any(edge.edge_name == "entity_specialization" for edge in head.get_all_edges())
    assert head.references == []

    host = EntityGraphNode(AxisReferenceCoreEntity)
    assert [edge.edge_name for edge in host.references] == ["entity_reference"]
    assert host.references[0].target_node_id == TypeIntrospection.full_qualname(PressingKindEnumEntity)


def test_two_dictionaries_with_the_same_short_name_keep_separate_targets() -> None:
    """The target is the qualified name, so a short name collides nowhere."""
    edges = _references(TwinHostCoreEntity)

    assert {edge.properties["field_name"]: edge.target_node_id for edge in edges} == {
        "first": TypeIntrospection.full_qualname(FirstTwinEnumEntity),
        "second": TypeIntrospection.full_qualname(SecondTwinEnumEntity),
    }
    assert edges[0].target_node_id != edges[1].target_node_id


def test_a_graph_document_with_a_reference_edge_validates() -> None:
    """The schema declares ``entity_reference`` and its properties."""
    node = EntityGraphNode(ReferenceHostCoreEntity)
    dictionary = EntityGraphNode(CurrencyEnumEntity)
    document = {
        "schema_version": "1.0",
        "nodes": [node.to_dict(), dictionary.to_dict()],
        "edges": [edge.to_dict(source_id=node.node_id) for edge in node.references],
    }

    jsonschema.validate(document, GRAPH_JSON_SCHEMA)

    incomplete = {
        "schema_version": "1.0",
        "nodes": [node.to_dict(), dictionary.to_dict()],
        "edges": [
            {
                **node.references[0].to_dict(source_id=node.node_id),
                "properties": {"field_name": "currency"},
            },
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(incomplete, GRAPH_JSON_SCHEMA)


def test_a_reference_to_a_dictionary_outside_the_graph_is_refused_by_the_rule() -> None:
    """The declaration boundary names the problem; the builder never emits a dangling edge."""
    with pytest.raises(EntityFieldDeclarationError) as caught:
        validate_entity_fields([HiddenReferenceCoreEntity])

    assert "no node in the graph" in caught.value.details
    assert _references(HiddenReferenceCoreEntity) == []
