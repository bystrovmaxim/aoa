# tests/action_machine/graph/test_entity_specialization_graph.py
"""
The graph a specialization produces: edges to every alternative, and the field kept as a column.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A head field parameterised by ``Specialization[A | B | C]`` becomes **three edges**,
one per alternative, and stays **one column**. Both halves matter: the edges are what
a consumer walks to reach every table the continuation can live in, and the column is
what tells a reader that the row has a continuation at all. N edges without the column
would hide the field; the column without the edges would hide the choice.

These tests pin that, the properties an edge carries, the guarantee the edges rely on
— a target that is not a node is a build error, never a silent row — and the runtime
facts the design rests on: a link whose row is not loaded keeps its identifier and its
variant, and a class outside the union is refused where the value is assigned.

═══════════════════════════════════════════════════════════════════════════════
WHAT IS NOT COVERED YET
═══════════════════════════════════════════════════════════════════════════════

**The interchange JSON schema does not accept these edges yet.** It is a checked-in
document, and its ``link.oneOf`` list gains the branch in the phase that owns the
schema. There is a witness for that in the suite already: with a specialization left in
the built graph, ``test_entity_field_graph.test_entity_field_export_validates_against_graph_schema``
fails naming the offending row —

    edges.22 -> {'alternative_index': 0, 'alternatives': [...], 'classifier_value': 'first', ...}

That is why every fixture here is excluded from the built graph: a fixture left in
would make an unrelated test fail for a reason that belongs to another task.
"""

from __future__ import annotations

from typing import Annotated, Literal

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class _GDomain(BaseDomain):
    name = "g"
    description = "g"


# Every fixture is excluded from the built graph: the entity inspector walks every
# loaded ``BaseEntity`` subclass, imported test modules included, so a fixture left in
# would change the graph other tests build.


@exclude_graph_model
@entity(description="First", domain=_GDomain)
class _FirstEntity(BaseEntity):
    id: str = Field(description="id")
    stamper: str = Field(description="a column of its own")
    record: Annotated[
        Generalization[_HeadEntity],
        Classifier("record", Literal["first"]),
        Inverse(_HeadEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Second", domain=_GDomain)
class _SecondEntity(BaseEntity):
    id: str = Field(description="id")
    year: int = Field(description="a column of its own")
    record: Annotated[
        Generalization[_HeadEntity],
        Classifier("record", Literal["repress"]),
        Inverse(_HeadEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Third", domain=_GDomain)
class _ThirdEntity(BaseEntity):
    id: str = Field(description="id")
    record: Annotated[
        Generalization[_HeadEntity],
        Classifier("record", Literal["test"]),
        Inverse(_HeadEntity, "pressed"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Head", domain=_GDomain)
class _HeadEntity(BaseEntity):
    id: str = Field(description="id")
    title: str = Field(description="a plain column")
    media: str = Field(description="classifier")
    pressed: Annotated[
        Specialization[_FirstEntity | _SecondEntity | _ThirdEntity],
        Classifier(field="media", codes=Literal["first", "repress", "test"]),
        Inverse(field_name="record"),
    ] = Rel(description="how it was pressed")


@exclude_graph_model
@entity(description="No specialization", domain=_GDomain)
class _PlainEntity(BaseEntity):
    id: str = Field(description="id")
    title: str = Field(description="a plain column")


for _cls in (_FirstEntity, _SecondEntity, _ThirdEntity, _HeadEntity, _PlainEntity):
    _cls.model_rebuild()


def _node(cls: type[BaseEntity]) -> EntityGraphNode:
    """Return the graph node of ``cls``."""
    return EntityGraphNode(cls)


def _specialization_edges(cls: type[BaseEntity] = _HeadEntity) -> list[BaseGraphEdge]:
    """Return the specialization edges of ``cls``."""
    return [edge for edge in _node(cls).get_all_edges() if edge.edge_name == "entity_specialization"]


# ─────────────────────────────────────────────────────────────────────────────
# Every alternative gets an edge, and the field stays a column
# ─────────────────────────────────────────────────────────────────────────────


def test_one_edge_per_alternative_points_at_its_own_class() -> None:
    edges = _specialization_edges()

    assert [edge.target_node_id for edge in edges] == [
        TypeIntrospection.full_qualname(cls) for cls in (_FirstEntity, _SecondEntity, _ThirdEntity)
    ]


def test_the_field_is_still_a_column() -> None:
    node = _node(_HeadEntity)
    columns = [edge.target_node.label for edge in node.entity_field_edges if edge.target_node is not None]

    assert columns == ["id", "title", "media", "pressed"], "a reader has to see the field itself"


def test_the_same_field_is_not_emitted_twice() -> None:
    emitted = [edge.target_node_id for edge in _node(_HeadEntity).get_all_edges() if edge.edge_name == "entity_field"]

    assert len(emitted) == len(set(emitted)), "one column row per field"
    assert len([name for name in emitted if name.endswith(":pressed")]) == 1


def test_the_head_carries_both_its_columns_and_its_alternatives() -> None:
    kinds = [edge.edge_name for edge in _node(_HeadEntity).get_all_edges()]

    assert kinds.count("entity_specialization") == 3
    assert kinds.count("entity_field") == 4


# ─────────────────────────────────────────────────────────────────────────────
# What an edge carries
# ─────────────────────────────────────────────────────────────────────────────


def test_each_edge_carries_its_code_and_its_position() -> None:
    edges = _specialization_edges()

    assert [edge.properties["classifier_value"] for edge in edges] == ["first", "repress", "test"]
    assert [edge.properties["alternative_index"] for edge in edges] == [0, 1, 2]


def test_every_edge_repeats_the_whole_declaration() -> None:
    listed = [
        f"{code} -> {TypeIntrospection.full_qualname(cls)}"
        for code, cls in zip(("first", "repress", "test"), (_FirstEntity, _SecondEntity, _ThirdEntity), strict=True)
    ]

    for edge in _specialization_edges():
        assert edge.properties["alternatives"] == listed, "one edge is enough to read the whole cluster"
        assert edge.properties["classifier_field"] == "media"
        assert edge.properties["relation_type"] == "specialization"
        assert edge.properties["cardinality"] == "one"
        assert edge.properties["field_name"] == "pressed"


def test_the_edges_are_ordinary_associations_so_they_stay_in_the_full_graph() -> None:
    for edge in _specialization_edges():
        assert edge.edge_relationship.archimate_name == "Association"
        assert edge.is_dag is False


def test_an_edge_serializes_with_its_own_properties_only() -> None:
    row = _specialization_edges()[0].to_dict(source_id="some.Head")
    properties = row["properties"]

    assert row["type"] == "entity_specialization"
    assert row["relationship"] == "Association"
    assert row["target_id"] == TypeIntrospection.full_qualname(_FirstEntity)
    assert set(properties) == {
        "field_name",
        "classifier_field",
        "classifier_value",
        "alternative_index",
        "alternatives",
        "labels",
        "relation_type",
        "cardinality",
        "description",
        "has_inverse",
        "deprecated",
    }


# ─────────────────────────────────────────────────────────────────────────────
# The guarantee the edges rely on
# ─────────────────────────────────────────────────────────────────────────────


class _OrphanRoot:
    """A root type of its own, so this test's inspector walks nothing real."""


class _OrphanNode(BaseGraphNode[object]):
    """A node whose outbound edge points at something the coordinator cannot find."""

    def __init__(self) -> None:
        from aoa.action_machine.graph.core.association_graph_edge import (  # pylint: disable=import-outside-toplevel
            AssociationGraphEdge,
        )

        super().__init__(
            node_id="nowhere.Head",
            node_type="Entity",
            label="Head",
            properties={},
            node_obj=object(),
        )
        self._edge = AssociationGraphEdge(
            edge_name="entity_specialization",
            is_dag=False,
            target_node_id="nowhere.MissingEntity",
        )

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the one edge, whose target never becomes a node."""
        return [self._edge]


class _OrphanInspector(BaseGraphNodeInspector[_OrphanRoot]):
    """Emit exactly one node, whose edge points outside the graph."""

    def _get_node(self, cls: type) -> BaseGraphNode[object] | None:
        if cls is not _OrphanRoot:
            return None
        return _OrphanNode()


def test_the_coordinator_refuses_an_edge_whose_target_is_not_a_node() -> None:
    """A dangling target is a build error, so an edge never becomes a silent row."""
    coord = NodeGraphCoordinator()

    with pytest.raises(InvalidGraphError, match="missing target_node_id"):
        coord.build([_OrphanInspector()])


# ─────────────────────────────────────────────────────────────────────────────
# The runtime facts the design rests on
# ─────────────────────────────────────────────────────────────────────────────


def test_a_link_keeps_its_identifier_and_variant_without_a_loaded_row() -> None:
    head = _HeadEntity(
        id="h", title="t", media="first", pressed=Specialization[_FirstEntity](id="h", variant="first")
    )

    assert head.pressed.id == "h"
    assert head.pressed.variant == "first"
    assert head.pressed.entity is None


def test_a_loaded_row_reads_back_as_the_object_put_in() -> None:
    row = _FirstEntity(id="h", stamper="1A")
    head = _HeadEntity(
        id="h", title="t", media="first", pressed=Specialization[_FirstEntity](id="h", variant="first", entity=row)
    )

    assert head.pressed.entity is row


def test_a_class_outside_the_union_is_refused() -> None:
    with pytest.raises(ValidationError):
        Specialization[_FirstEntity](id="h", variant="first", entity=_ThirdEntity(id="h"))


# ─────────────────────────────────────────────────────────────────────────────
# A model that declares no specialization declares nothing new
# ─────────────────────────────────────────────────────────────────────────────


def test_a_model_without_specialization_has_no_specialization_edges() -> None:
    assert _specialization_edges(_PlainEntity) == []


def test_a_model_without_specialization_keeps_its_columns() -> None:
    node = _node(_PlainEntity)
    columns = [edge.target_node.label for edge in node.entity_field_edges if edge.target_node is not None]

    assert columns == ["id", "title"]
    assert node.properties == {"description": "No specialization"}
