# tests/action_machine/graph/test_graph_json_schema_specialization.py
"""
The interchange schema accepts the two edges a specialization produces, and refuses a broken one.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

`GRAPH_JSON_SCHEMA` is a checked-in document, and everything the graph exports has to be declared
in it. Two branches were added for this feature — `entity_specialization` (head → one
alternative) and `parent_entity` (extension → head) — and this file is what keeps them honest:
the positive case proves the branches are reachable and complete, and each negative case proves
the branch actually constrains something rather than accepting any object with a matching `type`.

A schema that accepted everything would pass every positive test ever written, so the negative
cases are the point. Each one breaks exactly one thing and names it.

═══════════════════════════════════════════════════════════════════════════════
WHY THE PAYLOAD IS BUILT HERE RATHER THAN TAKEN FROM A MACHINE
═══════════════════════════════════════════════════════════════════════════════

Every fixture in this suite that declares a specialization is marked `@exclude_graph_model`,
because a broken one left in the graph fails the build of every test that assembles one. A
machine build therefore carries no specialization edge to validate, and one is assembled here
instead — from real `EntityGraphNode` and edge objects, so the property sets under test are the
ones the code produces and not a copy written by hand.

`properties` is closed (`additionalProperties: false`) in both branches, which is what makes the
extra-property case meaningful: without it, a payload could carry anything beside the declared
keys and still pass.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValidationError** — the payload does not match the schema; each test asserts the failure.

Does not cover what the graph emits (the graph tests do), or what Maxitor's store accepts (its
own tests do).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import Field

from aoa.action_machine.domain import (
    BaseEntity,
    Classifier,
    Generalization,
    Inverse,
    Rel,
    Specialization,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.edges.entity_specialization_graph_edge import (
    EntitySpecializationGraphEdge,
)
from aoa.action_machine.graph.edges.parent_entity_graph_edge import ParentEntityGraphEdge
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

_VALIDATOR = Draft202012Validator(GRAPH_JSON_SCHEMA)


class SchemaDomain(BaseDomain):
    name = "schema"
    description = "schema"


@exclude_graph_model
@entity(description="First variant", domain=SchemaDomain)
class SchemaFirstEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SchemaHeadEntity],
        Classifier("rec", Literal["first"]),
        Inverse(SchemaHeadEntity, "pack"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Second variant", domain=SchemaDomain)
class SchemaSecondEntity(BaseEntity):
    id: str = Field(description="id")
    rec: Annotated[
        Generalization[SchemaHeadEntity],
        Classifier("rec", Literal["repress"]),
        Inverse(SchemaHeadEntity, "pack"),
    ] = Rel(description="back")


@exclude_graph_model
@entity(description="Head", domain=SchemaDomain)
class SchemaHeadEntity(BaseEntity):
    id: str = Field(description="id")
    media: str = Field(description="classifier")
    pack: Annotated[
        Specialization[SchemaFirstEntity | SchemaSecondEntity],
        Classifier(field="media", codes=Literal["first", "repress"]),
        Inverse(field_name="rec"),
    ] = Rel(description="one of two")


for _cls in (SchemaFirstEntity, SchemaSecondEntity, SchemaHeadEntity):
    _cls.model_rebuild()


def _rows_for(cls: type[BaseEntity]) -> list[dict[str, Any]]:
    """
    Return every vertex a machine emits for ``cls``: the entity itself and its column vertices.

    The columns are here because the entity's own edges point at them, and a payload that named a
    field vertex it never declared would be refused for a reason that has nothing to do with the
    branches under test.
    """
    node = EntityGraphNode(cls)
    rows = [node.to_dict()]
    rows.extend(
        edge.target_node.to_dict()
        for edge in node.entity_field_edges
        if getattr(edge, "target_node", None) is not None
    )
    return rows


def _domain_row() -> dict[str, Any]:
    """Return the domain vertex row the entity rows refer to, built by the node that owns it."""
    return DomainGraphNode(SchemaDomain).to_dict()


def _specialization_rows() -> list[dict[str, Any]]:
    """Return the `entity_specialization` link rows a machine emits for the head."""
    head_id = TypeIntrospection.full_qualname(SchemaHeadEntity)
    return [
        edge.to_dict(source_id=head_id)
        for edge in EntitySpecializationGraphEdge.get_entity_specialization_edges(SchemaHeadEntity)
    ]


def _generalization_rows() -> list[dict[str, Any]]:
    """Return the `parent_entity` link rows a machine emits for both extensions."""
    rows: list[dict[str, Any]] = []
    for cls in (SchemaFirstEntity, SchemaSecondEntity):
        rows.extend(
            edge.to_dict(source_id=TypeIntrospection.full_qualname(cls))
            for edge in ParentEntityGraphEdge.get_entity_generalization_edges(cls)
        )
    return rows


def _payload(
    *,
    specialization_rows: list[dict[str, Any]] | None = None,
    generalization_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble a complete export: the entities, their columns, their domain, and both edge kinds."""
    nodes = [_domain_row()]
    for cls in (SchemaHeadEntity, SchemaFirstEntity, SchemaSecondEntity):
        nodes.extend(_rows_for(cls))
    edges = [
        *(_specialization_rows() if specialization_rows is None else specialization_rows),
        *(_generalization_rows() if generalization_rows is None else generalization_rows),
    ]
    return {"schema_version": "1.0", "nodes": nodes, "edges": edges}


def _rejects(payload: dict[str, Any]) -> None:
    """
    Assert the schema refuses ``payload``.

    The message is deliberately not asserted on. `link` is a `oneOf`, so a refusal reports the
    whole edge object rather than the offending key, and a test that searched the text for the key
    would be asserting on jsonschema's formatting instead of on the schema. What ties a refusal to
    the mutation is the positive test beside it: the same payload **unmutated** validates, so the
    only difference this test introduces is the one thing it broke.
    """
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


# ─────────────────────────────────────────────────────────────────────────────
# Both branches are reachable and complete
# ─────────────────────────────────────────────────────────────────────────────


def test_a_payload_with_both_new_edges_validates() -> None:
    """The positive case: one axis, two alternatives, both directions, and every required key."""
    payload = _payload()

    kinds = {edge["type"] for edge in payload["edges"]}
    assert kinds == {"entity_specialization", "parent_entity"}, "both new branches are exercised"
    _VALIDATOR.validate(payload)


def test_the_two_branches_carry_what_the_contract_promises() -> None:
    """The keys under test are the ones the code emits, so a renamed property fails here."""
    specialization = _specialization_rows()[0]
    generalization = _generalization_rows()[0]

    assert set(specialization["properties"]) == {
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
    assert set(generalization["properties"]) == {
        "field_name",
        "inverse_field",
        "classifier_value",
        "head_entity_id",
    }
    assert generalization["relationship"] == "Generalization"
    assert specialization["relationship"] == "Association"


def test_the_labels_mirror_the_alternatives_for_display() -> None:
    """
    `labels` is what a diagram shows: the class with its code, the `Entity` suffix dropped.

    It is a display string and nothing parses it back, so it is asserted to be aligned with
    `alternatives` — same order, same length — rather than to have any particular spelling.
    """
    properties = _specialization_rows()[0]["properties"]

    assert len(properties["labels"]) == len(properties["alternatives"])
    assert properties["labels"] == ["SchemaFirst (first)", "SchemaSecond (repress)"]
    assert properties["alternatives"][0].endswith("SchemaFirstEntity"), "the resolvable name is untouched"


def test_each_alternative_produces_exactly_one_generalization_edge() -> None:
    """Two alternatives, two edges — and each names its own code, not the first one found."""
    rows = _generalization_rows()
    assert len(rows) == 2
    assert sorted(row["properties"]["classifier_value"] for row in rows) == ["first", "repress"]


# ─────────────────────────────────────────────────────────────────────────────
# A required key missing is refused, one case per branch
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "missing",
    ["field_name", "classifier_field", "classifier_value", "alternative_index", "alternatives"],
)
def test_a_specialization_edge_without_a_required_key_is_refused(missing: str) -> None:
    rows = _specialization_rows()
    del rows[0]["properties"][missing]

    _rejects(_payload(specialization_rows=rows))


@pytest.mark.parametrize("missing", ["field_name", "inverse_field", "classifier_value", "head_entity_id"])
def test_a_generalization_edge_without_a_required_key_is_refused(missing: str) -> None:
    rows = _generalization_rows()
    del rows[0]["properties"][missing]

    _rejects(_payload(generalization_rows=rows))


# ─────────────────────────────────────────────────────────────────────────────
# An extra key is refused, which is what `additionalProperties: false` buys
# ─────────────────────────────────────────────────────────────────────────────


def test_a_specialization_edge_with_an_undeclared_property_is_refused() -> None:
    rows = _specialization_rows()
    rows[0]["properties"]["surprise"] = "not in the contract"

    _rejects(_payload(specialization_rows=rows))


def test_a_generalization_edge_with_an_undeclared_property_is_refused() -> None:
    rows = _generalization_rows()
    rows[0]["properties"]["surprise"] = "not in the contract"

    _rejects(_payload(generalization_rows=rows))


# ─────────────────────────────────────────────────────────────────────────────
# The branch is selected by the type, and the relationship is pinned
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_type", ["entity_specialisation", "EntitySpecialization", "entity_relation"])
def test_an_edge_whose_type_is_not_declared_is_refused(bad_type: str) -> None:
    rows = _specialization_rows()
    rows[0]["type"] = bad_type

    _rejects(_payload(specialization_rows=rows))


def test_a_generalization_edge_with_another_relationship_is_refused() -> None:
    """The relationship is the whole reason the full graph strips these edges, so it is pinned."""
    rows = _generalization_rows()
    rows[0]["relationship"] = "Association"

    _rejects(_payload(generalization_rows=rows))


def test_an_alternative_index_that_is_not_a_number_is_refused() -> None:
    rows = _specialization_rows()
    rows[0]["properties"]["alternative_index"] = "first"

    _rejects(_payload(specialization_rows=rows))


def test_an_empty_alternatives_list_is_refused() -> None:
    """Every edge of a cluster carries the whole declaration, and a declaration has members."""
    rows = _specialization_rows()
    rows[0]["properties"]["alternatives"] = []

    _rejects(_payload(specialization_rows=rows))
