# tests/action_machine/graph/test_edge_identity.py
"""Tests for edge ids: :func:`~aoa.action_machine.graph.edge_identity.edge_id`, the rule table, and the build refusals."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

import pytest

import aoa.action_machine
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import DuplicateEdgeError, InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.edge_identity import EDGE_ID_RULES, EdgeIdRule, edge_id
from aoa.action_machine.graph.edges.state_graph_edge import StateGraphEdge

_OFFER = "shop.OfferRequestCoreEntity"
_ITEM = "shop.OfferRequestItemDetailEntity"
_LIFECYCLE = "shop.OfferCoreEntity:lifecycle:lifecycle"


def _row(edge_type: str, target: str = _ITEM, source: str = _OFFER, **properties: Any) -> dict[str, Any]:
    """Return one exported edge row without an ``id``."""
    return {
        "source_id": source,
        "target_id": target,
        "type": edge_type,
        "relationship": "Association",
        "is_dag": False,
        "properties": properties,
    }


# ─── The function ────────────────────────────────────────────────────────────


def test_the_default_id_is_source_type_target() -> None:
    """A type without a rule is named by its source, its type and its target."""
    row = _row("@check_roles", source="actions.SignInAdminAction", target="auth.GuestRole")
    assert edge_id(row) == "actions.SignInAdminAction|@check_roles|auth.GuestRole"


def test_a_relation_is_named_by_its_field() -> None:
    """Two relations of one entity to the same entity differ by field; a new target keeps the id."""
    offers = _row("entity_relation", field_name="offers")
    chosen = _row("entity_relation", field_name="chosen_offer")
    retargeted = _row("entity_relation", target="shop.OtherEntity", field_name="offers")

    assert edge_id(offers) == f"{_OFFER}|entity_relation|offers"
    assert edge_id(chosen) != edge_id(offers)
    assert edge_id(retargeted) == edge_id(offers)


def test_a_transition_appends_the_state_it_leaves() -> None:
    """Two transitions into one state from two states get two ids."""
    target = f"{_LIFECYCLE}:active"
    from_draft = _row("lifecycle_transition", target=target, source=_LIFECYCLE, from_state="draft", to_state="active")
    from_paused = _row("lifecycle_transition", target=target, source=_LIFECYCLE, from_state="paused", to_state="active")

    assert edge_id(from_draft) == f"{_LIFECYCLE}|lifecycle_transition|{target}|draft"
    assert edge_id(from_paused) != edge_id(from_draft)


def test_an_id_already_in_the_row_is_ignored() -> None:
    """A 1.0 row, the same row with its id and the same row with a wrong id give one id."""
    row = _row("entity_relation", field_name="offers")
    expected = edge_id(row)

    assert edge_id({**row, "id": expected}) == expected
    assert edge_id({**row, "id": "something|else"}) == expected


@pytest.mark.parametrize("field", ["source_id", "type", "target_id"])
def test_a_row_without_a_required_field_is_refused(field: str) -> None:
    """A row that lacks its source, type or target names the missing field."""
    row = _row("@check_roles")
    del row[field]
    with pytest.raises(ValueError, match=field):
        edge_id(row)


@pytest.mark.parametrize(
    ("edge_type", "field", "extra"),
    [
        ("entity_relation", "field_name", {}),
        ("lifecycle_transition", "from_state", {"to_state": "active"}),
    ],
)
@pytest.mark.parametrize("value", [None, "", 5])
def test_a_row_without_its_rule_property_is_refused(edge_type: str, field: str, extra: dict[str, Any], value: Any) -> None:
    """A missing, empty or non-string rule property names the type and the property."""
    properties = dict(extra)
    if value is not None:
        properties[field] = value
    with pytest.raises(ValueError, match=f"{edge_type}.*{field}"):
        edge_id(_row(edge_type, **properties))


@pytest.mark.parametrize(
    ("row", "field"),
    [
        (_row("@check_roles", source="a|b"), "source_id"),
        (_row("@check_roles", target="a|b"), "target_id"),
        (_row("entity_relation", field_name="off|ers"), "field_name"),
        (_row("lifecycle_transition", from_state="dr|aft", to_state="active"), "from_state"),
    ],
)
def test_a_separator_inside_a_part_is_refused(row: dict[str, Any], field: str) -> None:
    """A ``|`` inside any part of the id names the part."""
    with pytest.raises(ValueError, match=field):
        edge_id(row)


def test_a_rule_sets_at_most_one_property() -> None:
    """A rule with both a member and a suffix is refused."""
    with pytest.raises(ValueError, match="at most one"):
        EdgeIdRule(member="a", suffix="b")


# ─── The table ───────────────────────────────────────────────────────────────


def _all_edge_classes() -> set[type[BaseGraphEdge]]:
    """Import every module of the package and return every edge class loaded."""
    for module in pkgutil.walk_packages(aoa.action_machine.__path__, "aoa.action_machine."):
        importlib.import_module(module.name)
    found: set[type[BaseGraphEdge]] = set()
    pending: list[type[BaseGraphEdge]] = [BaseGraphEdge]
    while pending:
        cls = pending.pop()
        for sub in cls.__subclasses__():
            if sub not in found:
                found.add(sub)
                pending.append(sub)
    return found


def test_every_declared_rule_is_in_the_table() -> None:
    """Every edge class that declares a rule is in the table under its type, and the table holds nothing else."""
    declared = {cls.__dict__["EDGE_TYPE"]: cls.__dict__["ID_RULE"] for cls in _all_edge_classes() if "ID_RULE" in cls.__dict__}
    assert declared == dict(EDGE_ID_RULES)


# ─── The build ───────────────────────────────────────────────────────────────


class _Axis:
    """Single host type for a tiny graph."""


class _Node(BaseGraphNode[object]):
    def __init__(self, node_id: str, *, edges: list[BaseGraphEdge] | None = None, companions: list[BaseGraphNode[Any]] | None = None) -> None:
        super().__init__(node_id=node_id, node_type="Params", label=node_id, properties={}, node_obj=object())
        object.__setattr__(self, "_edges", edges or [])
        object.__setattr__(self, "_companions", companions or [])

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return self._companions

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return self._edges


class _Inspector(BaseGraphNodeInspector[_Axis]):
    def __init__(self, root: BaseGraphNode[object]) -> None:
        self._root_node = root

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return self._root_node if cls is _Axis else None


def _build(root: BaseGraphNode[object]) -> NodeGraphCoordinator:
    """Build a coordinator over ``root`` and its companions."""
    coord = NodeGraphCoordinator()
    coord.build([_Inspector(root)])
    return coord


def _link(target: str, name: str = "uses") -> AssociationGraphEdge:
    """Return an association edge to ``target``."""
    return AssociationGraphEdge(edge_name=name, is_dag=False, target_node_id=target)


def test_two_edges_with_one_id_fail_the_build() -> None:
    """Two edges of one type without a rule between the same nodes are refused, naming both."""
    root = _Node("pkg.host", edges=[_link("pkg.other"), _link("pkg.other")], companions=[_Node("pkg.other")])

    with pytest.raises(DuplicateEdgeError) as caught:
        _build(root)

    assert caught.value.edge_id == "pkg.host|uses|pkg.other"
    message = str(caught.value)
    assert "pkg.host|uses|pkg.other" in message
    assert message.count("pkg.host -[uses]-> pkg.other") == 2


def test_a_node_id_with_the_separator_fails_the_build() -> None:
    """A node whose id contains ``|`` is refused even when no edge touches it."""
    root = _Node("pkg.host", companions=[_Node("pkg.odd|name")])

    with pytest.raises(InvalidGraphError, match=r"pkg\.odd\|name"):
        _build(root)


def test_an_edge_whose_rule_property_has_the_separator_fails_the_build() -> None:
    """A transition that leaves a state named with ``|`` is refused, naming the edge and the property."""
    transition = StateGraphEdge(target_node_id="pkg.state", from_state="dr|aft", to_state="done")
    root = _Node("pkg.host", edges=[transition], companions=[_Node("pkg.state")])

    with pytest.raises(InvalidGraphError, match=r"pkg\.host -\[lifecycle_transition\]-> pkg\.state.*from_state"):
        _build(root)


def test_edges_that_can_be_told_apart_build() -> None:
    """Edges of different types or targets between the same nodes build as before."""
    root = _Node(
        "pkg.host",
        edges=[_link("pkg.other"), _link("pkg.other", name="reads"), _link("pkg.third")],
        companions=[_Node("pkg.other"), _Node("pkg.third")],
    )

    assert len(_build(root).get_all_nodes()) == 3
