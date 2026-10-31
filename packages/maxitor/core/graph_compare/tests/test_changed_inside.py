# packages/maxitor/core/graph_compare/tests/test_changed_inside.py
"""``changed_inside``: what is a part, what stops the walk, and what the list says (spec 041, FR-008)."""

from __future__ import annotations

import copy
from typing import Any

from maxitor.graph_compare import Status, changed_inside, compare

ACTION = "s.ReadAction"
OTHER = "s.OtherAction"
RESULT = "s.ReadAction.Result"
PARAMS = "s.ReadAction.Params"
ASPECT = "s.ReadAction:summary"


def _node(node_id: str, node_type: str, label: str = "", **properties: Any) -> dict[str, Any]:
    """A node of a type."""
    return {"id": node_id, "type": node_type, "label": label or node_id.rsplit(":", 1)[-1], "properties": properties}


def _edge(source: str, edge_type: str, target: str, relationship: str, **properties: Any) -> dict[str, Any]:
    """An edge with its ``1.1`` id."""
    return {"id": f"{source}|{edge_type}|{target}", "source_id": source, "target_id": target, "type": edge_type, "relationship": relationship, "is_dag": False, "properties": properties}


def _graph() -> dict[str, Any]:
    """Two actions sharing a result, with params, an aspect and its checker, a role, a domain, a resource and an entity."""
    return {
        "schema_version": "1.1",
        "nodes": [
            _node(ACTION, "Action", "ReadAction"),
            _node(OTHER, "Action", "OtherAction"),
            _node(RESULT, "Result", "Result"),
            _node(PARAMS, "Params", "Params"),
            _node(f"{RESULT}:name", "Field", type="str"),
            _node(f"{PARAMS}:id", "Field", type="int"),
            _node(ASPECT, "SummaryAspect", "summary", description="Read"),
            _node(f"{ASPECT}:check", "Checker", "check"),
            _node("s.Role", "Role"),
            _node("s.Domain", "Domain", description="Sales"),
            _node("s.Store", "Resource", description="Store"),
            _node("s.Entity", "Entity", description="An entity"),
        ],
        "edges": [
            _edge(ACTION, "generic:result", RESULT, "Aggregation"),
            _edge(OTHER, "generic:result", RESULT, "Aggregation"),
            _edge(ACTION, "generic:params", PARAMS, "Aggregation"),
            _edge(RESULT, "field", f"{RESULT}:name", "Composition"),
            _edge(PARAMS, "field", f"{PARAMS}:id", "Composition"),
            _edge(ACTION, "@summary_aspect", ASPECT, "Composition"),
            _edge(ASPECT, "@result_checker", f"{ASPECT}:check", "Composition"),
            _edge(ACTION, "@check_roles", "s.Role", "Association"),
            _edge(ACTION, "domain", "s.Domain", "Aggregation"),
            _edge(ACTION, "@connection", "s.Store", "Association", key="store"),
            _edge(ACTION, "@depends", OTHER, "Association"),
            _edge(f"{RESULT}:name", "entity_schema", "s.Entity", "Aggregation"),
        ],
    }


def _inside(older: dict[str, Any], newer: dict[str, Any]) -> dict[str, list[tuple[str, str, str, str]]]:
    """Each root's parts as (group, kind, label, status), as a diagram of actions and roles asks."""
    found = changed_inside(older, newer, compare(older, newer), root_type="Action", drawn_types={"Action", "Role"}, through={"generic:params", "generic:result"})
    return {root: [(part.group, part.kind, part.label, part.status.value) for part in parts] for root, parts in found.items()}


def _node_of(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    """One node of a graph, to edit it."""
    return next(node for node in graph["nodes"] if node["id"] == node_id)


def _changed_copy() -> tuple[dict[str, Any], dict[str, Any]]:
    """Two equal graphs, the second to edit."""
    older = _graph()
    return older, copy.deepcopy(older)


def test_nothing_changed_lists_nothing() -> None:
    """Equal documents have no changed part."""
    older, newer = _changed_copy()
    assert _inside(older, newer) == {}


def test_a_new_result_field_is_one_part_of_every_action_using_the_result() -> None:
    """The field is listed once, without its edge, and a shared ``Result`` reaches both actions."""
    older, newer = _changed_copy()
    newer["nodes"].append(_node(f"{RESULT}:extra", "Field"))
    newer["edges"].append(_edge(RESULT, "field", f"{RESULT}:extra", "Composition"))
    expected = [("Result", "node", "extra", "added")]
    assert _inside(older, newer) == {ACTION: expected, OTHER: expected}


def test_a_removed_field_is_found_by_walking_a() -> None:
    """A part only in A is listed, as its node, with no edge beside it."""
    older, newer = _changed_copy()
    newer["nodes"] = [node for node in newer["nodes"] if node["id"] != f"{PARAMS}:id"]
    newer["edges"] = [edge for edge in newer["edges"] if edge["target_id"] != f"{PARAMS}:id"]
    assert _inside(older, newer) == {ACTION: [("Params", "node", "id", "removed")]}


def test_a_changed_field_carries_its_differences() -> None:
    """A changed part gives the comparison's differences."""
    older, newer = _changed_copy()
    _node_of(newer, f"{PARAMS}:id")["properties"]["type"] = "str"
    parts = changed_inside(older, newer, compare(older, newer), root_type="Action", drawn_types={"Action", "Role"}, through={"generic:params"})[ACTION]
    assert parts[0].status is Status.CHANGED
    assert [(d.path, d.before, d.after) for d in parts[0].differences] == [(("properties", "type"), "int", "str")]


def test_an_aspect_and_what_it_owns_are_parts_under_the_aspect() -> None:
    """The aspect names its group, and a checker under it falls in the same group."""
    older, newer = _changed_copy()
    _node_of(newer, ASPECT)["properties"]["description"] = "Read it"
    _node_of(newer, f"{ASPECT}:check")["label"] = "check it"
    assert _inside(older, newer) == {ACTION: [("summary", "node", "check it", "changed"), ("summary", "node", "summary", "changed")]}


def test_a_link_the_diagram_does_not_draw_is_a_part_and_its_target_is_not() -> None:
    """A resource's link counts; the resource's own change does not, nor does the domain's."""
    older, newer = _changed_copy()
    next(edge for edge in newer["edges"] if edge["type"] == "@connection")["properties"]["key"] = "main"
    _node_of(newer, "s.Store")["properties"]["description"] = "Reworded"
    _node_of(newer, "s.Domain")["properties"]["description"] = "Reworded"
    assert _inside(older, newer) == {ACTION: [("Links", "edge", "s.Store", "changed")]}


def test_moving_to_another_domain_is_a_change_inside() -> None:
    """The old link goes and the new one comes, both under Links."""
    older, newer = _changed_copy()
    newer["nodes"].append(_node("s.Heir", "Domain"))
    edge = next(edge for edge in newer["edges"] if edge["type"] == "domain")
    edge.update(target_id="s.Heir", id=f"{ACTION}|domain|s.Heir")
    assert _inside(older, newer) == {ACTION: [("Links", "edge", "s.Domain", "removed"), ("Links", "edge", "s.Heir", "added")]}


def test_an_entity_a_field_points_at_is_not_entered() -> None:
    """``entity_schema`` only points: a changed entity is the ERD's."""
    older, newer = _changed_copy()
    _node_of(newer, "s.Entity")["properties"]["description"] = "Reworded"
    assert _inside(older, newer) == {}


def test_what_the_diagram_draws_is_no_part() -> None:
    """A changed role, a changed depended-on action, a new association: drawn, so none is a part."""
    older, newer = _changed_copy()
    _node_of(newer, "s.Role")["label"] = "Renamed"
    _node_of(newer, OTHER)["label"] = "Renamed"
    newer["nodes"].append(_node("s.Role2", "Role"))
    newer["edges"].append(_edge(ACTION, "@check_roles", "s.Role2", "Association"))
    assert _inside(older, newer) == {}


def test_an_added_or_removed_action_is_left_out() -> None:
    """Its own status stands: nothing is listed for it."""
    older, newer = _changed_copy()
    newer["nodes"].append(_node("s.NewAction", "Action"))
    newer["nodes"].append(_node("s.NewAction.Result", "Result"))
    newer["edges"].append(_edge("s.NewAction", "generic:result", "s.NewAction.Result", "Aggregation"))
    assert _inside(older, newer) == {}


def test_a_cycle_of_owned_nodes_ends() -> None:
    """Owned nodes pointing at each other are walked once."""
    older, newer = _changed_copy()
    for graph in (older, newer):
        graph["edges"].append(_edge(f"{ASPECT}:check", "@back", ASPECT, "Composition"))
    _node_of(newer, ASPECT)["properties"]["description"] = "Read it"
    assert _inside(older, newer) == {ACTION: [("summary", "node", "summary", "changed")]}


def test_parts_come_by_group_label_and_id() -> None:
    """The order does not follow the walk."""
    older, newer = _changed_copy()
    for name in ("zeta", "alpha"):
        newer["nodes"].append(_node(f"{RESULT}:{name}", "Field"))
        newer["edges"].append(_edge(RESULT, "field", f"{RESULT}:{name}", "Composition"))
    _node_of(newer, f"{PARAMS}:id")["properties"]["type"] = "str"
    assert [part[2] for part in _inside(older, newer)[ACTION]] == ["id", "alpha", "zeta"]
