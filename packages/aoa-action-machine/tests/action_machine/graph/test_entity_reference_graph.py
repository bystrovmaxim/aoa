# tests/action_machine/graph/test_entity_reference_graph.py
"""
Tests for a dictionary association reaching the graph as an ordinary relation edge.

A field typed ``AssociationOne[D]`` with ``NoInverse()`` projects as one ``entity_relation``
edge to the dictionary and one retained ``entity_field`` row naming the dictionary. The
historical ``entity_reference`` edge is no longer generated for new declarations.
"""

from __future__ import annotations

import textwrap
from typing import Annotated

import jsonschema
import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseDomain,
    BaseEnumEntity,
    BaseSpecEntity,
    Classifier,
    Generalization,
    Inverse,
    NoInverse,
    Specialization,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.edge_identity import edge_id
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.isolated_entity_models import run_isolated_model


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
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Required reference")
    settlement: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Optional reference"
    )


@exclude_graph_model
@entity(description="Spec host", domain=ReferenceDomain)
class SpecReferenceSpecEntity(BaseSpecEntity):
    """Reference a dictionary from a Spec host."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")


@exclude_graph_model
@entity(description="Assoc host", domain=ReferenceDomain)
class AssocReferenceAssocEntity(BaseAssocEntity):
    """Reference a dictionary from an Assoc host."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")


@exclude_graph_model
@entity(description="Detail host", domain=ReferenceDomain)
class DetailReferenceDetailEntity(BaseDetailEntity):
    """Reference a dictionary from a Detail host."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")


@exclude_graph_model
@entity(description="Reference base", domain=ReferenceDomain)
class ReferenceBaseCoreEntity(BaseCoreEntity):
    """Declare the reference on a base class."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")


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
    currency: Annotated[AssociationOne[LaterCurrencyEnumEntity], NoInverse()] = Field(description="Currency")


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
    kind: Annotated[AssociationOne[PressingKindEnumEntity], NoInverse()] = Field(description="Kind")


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
    first: Annotated[AssociationOne[FirstTwinEnumEntity], NoInverse()] = Field(description="First twin")
    second: Annotated[AssociationOne[SecondTwinEnumEntity], NoInverse()] = Field(description="Second twin")


def test_each_selection_produces_one_ordinary_edge() -> None:
    """One field, one ordinary relation edge, with the field name and the one cardinality."""
    node = EntityGraphNode(ReferenceHostCoreEntity)

    assert [edge.properties["field_name"] for edge in node.relations] == ["currency", "settlement"]
    for edge in node.relations:
        assert edge.edge_name == "entity_relation"
        assert edge.properties["relation_type"] == "association"
        assert edge.properties["cardinality"] == "one"
        assert edge.properties["has_inverse"] is False
        assert edge.target_node_id == TypeIntrospection.full_qualname(CurrencyEnumEntity)
    assert node.references == []


def test_the_field_row_and_the_edge_name_the_same_dictionary() -> None:
    """The retained row and the ordinary edge are one selection projected twice."""
    node = EntityGraphNode(ReferenceHostCoreEntity)
    row = next(edge.target_node for edge in node.entity_field_edges if edge.target_node.label == "currency")

    assert row.properties["reference_qualname"] == TypeIntrospection.full_qualname(CurrencyEnumEntity)
    assert node.relations[0].target_node_id == row.properties["reference_qualname"]


@pytest.mark.parametrize(
    "entity_cls",
    [SpecReferenceSpecEntity, AssocReferenceAssocEntity, DetailReferenceDetailEntity],
)
def test_a_selection_on_every_host_kind_produces_the_edge(entity_cls: type) -> None:
    """The host's kind does not change the ordinary association."""
    node = EntityGraphNode(entity_cls)

    assert [edge.properties["field_name"] for edge in node.relations] == ["currency"]
    assert node.relations[0].target_node_id == TypeIntrospection.full_qualname(CurrencyEnumEntity)


def test_an_inherited_selection_produces_the_edge() -> None:
    """An inherited field is carried exactly as a declared one."""
    node = EntityGraphNode(InheritedReferenceCoreEntity)

    assert [edge.properties["field_name"] for edge in node.relations] == ["currency"]


def test_a_forward_referenced_dictionary_produces_the_edge() -> None:
    """After resolution the edge exists."""
    ForwardReferenceCoreEntity.model_rebuild()

    node = EntityGraphNode(ForwardReferenceCoreEntity)

    assert [edge.target_node_id for edge in node.relations] == [
        TypeIntrospection.full_qualname(LaterCurrencyEnumEntity)
    ]


def test_a_selection_and_an_axis_naming_the_same_dictionary_stay_distinct() -> None:
    """The axis borrows the vocabulary; the selection names the value."""
    head = EntityGraphNode(RecordCoreEntity)
    assert any(edge.edge_name == "entity_specialization" for edge in head.get_all_edges())
    assert head.references == []

    host = EntityGraphNode(AxisReferenceCoreEntity)
    assert [edge.edge_name for edge in host.relations] == ["entity_relation"]
    assert host.relations[0].target_node_id == TypeIntrospection.full_qualname(PressingKindEnumEntity)


def test_two_dictionaries_with_the_same_short_name_keep_separate_targets() -> None:
    """The target is the qualified name, so a short name collides nowhere."""
    node = EntityGraphNode(TwinHostCoreEntity)

    assert {edge.properties["field_name"]: edge.target_node_id for edge in node.relations} == {
        "first": TypeIntrospection.full_qualname(FirstTwinEnumEntity),
        "second": TypeIntrospection.full_qualname(SecondTwinEnumEntity),
    }


def test_a_graph_document_with_an_ordinary_association_edge_validates() -> None:
    """The ordinary relation schema validates the emitted edge."""
    node = EntityGraphNode(ReferenceHostCoreEntity)
    dictionary = EntityGraphNode(CurrencyEnumEntity)
    document = {
        "schema_version": "1.1",
        "nodes": [node.to_dict(), dictionary.to_dict()],
        "edges": [{**row, "id": edge_id(row)} for row in (edge.to_dict(source_id=node.node_id) for edge in node.relations)],
    }

    jsonschema.validate(document, GRAPH_JSON_SCHEMA)


def _run_hidden_dictionary_refusal() -> str:
    """Run the hidden-dictionary refusal in a fresh interpreter, off the shared model."""
    script = textwrap.dedent(
        """
        from typing import Annotated

        from pydantic import Field

        from aoa.action_machine.domain import (
            AssociationOne,
            BaseCoreEntity,
            BaseDomain,
            BaseEnumEntity,
            NoInverse,
            value,
        )
        from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
        from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
        from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
        from aoa.action_machine.intents.entity import entity

        class HiddenDomain(BaseDomain):
            name = "hidden"
            description = "Hidden"

        @exclude_graph_model
        @entity(description="Hidden dictionary", domain=HiddenDomain)
        class HiddenEnumEntity(BaseEnumEntity):
            USD = value(code="usd", display_name="US dollar")

        @exclude_graph_model
        @entity(description="Hidden host", domain=HiddenDomain)
        class HiddenReferenceCoreEntity(BaseCoreEntity):
            id: str = Field(description="Identifier")
            currency: Annotated[AssociationOne[HiddenEnumEntity], NoInverse()] = Field(description="Currency")

        try:
            validate_entity_fields([HiddenReferenceCoreEntity])
            print("ACCEPT")
        except EntityFieldDeclarationError as exc:
            print("REFUSE " + exc.field_name + " " + exc.details)
        """
    )
    result = run_isolated_model(script)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_selection_of_a_dictionary_outside_the_graph_is_refused_by_the_rule() -> None:
    """The declaration boundary names the problem; the builder never emits a dangling edge."""
    out = _run_hidden_dictionary_refusal()

    assert "REFUSE currency" in out
    assert "no node in the graph" in out
