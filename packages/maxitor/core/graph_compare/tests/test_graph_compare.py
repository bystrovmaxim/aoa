# packages/maxitor/core/graph_compare/tests/test_graph_compare.py
"""``compare``: one status per element, every difference by its path, the counts, and the refusals."""

from __future__ import annotations

from typing import Any

import pytest
from maxitor.graph_compare import Change, Counts, Difference, GraphNotComparableError, Status, compare


def _graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], version: str = "1.1") -> dict[str, Any]:
    """A minimal document: a version, nodes and edges."""
    return {"schema_version": version, "nodes": nodes, "edges": edges}


def _node(node_id: str, label: str = "", **properties: Any) -> dict[str, Any]:
    """A node of type ``Entity`` with the given properties."""
    return {"id": node_id, "type": "Entity", "label": label or node_id, "properties": properties}


def _edge(source: str, edge_type: str, target: str, **properties: Any) -> dict[str, Any]:
    """A ``1.0`` edge row: no ``id``."""
    return {"source_id": source, "target_id": target, "type": edge_type, "relationship": "Association", "is_dag": False, "properties": properties}


def _with_id(edge: dict[str, Any], edge_id: str) -> dict[str, Any]:
    """The same edge as ``1.1`` writes it."""
    return {"id": edge_id, **edge}


OFFER, CORE, DETAIL = _node("a.Offer"), _node("a.Core"), _node("a.Detail")
CHOSEN = _with_id(_edge("a.Offer", "entity_relation", "a.Core", field_name="chosen"), "a.Offer|entity_relation|chosen")


def test_every_status_and_the_counts() -> None:
    """An added, a removed, a changed and an unchanged node, each once; the counts follow."""
    older = _graph([_node("a.Kept"), _node("a.Gone"), _node("a.Moved", "Old")], [])
    newer = _graph([_node("a.Kept"), _node("a.Moved", "New"), _node("a.Come")], [])
    result = compare(older, newer)
    assert {node_id: item.status for node_id, item in result.nodes.items()} == {
        "a.Kept": Status.UNCHANGED,
        "a.Gone": Status.REMOVED,
        "a.Moved": Status.CHANGED,
        "a.Come": Status.ADDED,
    }
    assert list(result.nodes) == ["a.Kept", "a.Gone", "a.Moved", "a.Come"]
    assert result.node_counts == Counts(added=1, removed=1, changed=1)
    assert result.edge_counts == Counts()
    assert result.nodes["a.Moved"].differences == (Difference(("label",), Change.CHANGED, "Old", "New"),)
    assert result.nodes["a.Kept"].differences == ()


def test_two_edges_between_the_same_nodes_each_get_their_own_status() -> None:
    """Edges are told apart by id, not by the pair of nodes they join."""
    uses = _with_id(_edge("a.Offer", "uses", "a.Core"), "a.Offer|uses|a.Core")
    owns = _with_id(_edge("a.Offer", "owns", "a.Core"), "a.Offer|owns|a.Core")
    owns_changed = {**owns, "is_dag": True}
    result = compare(_graph([OFFER, CORE], [uses, owns]), _graph([OFFER, CORE], [uses, owns_changed]))
    assert result.edges["a.Offer|uses|a.Core"].status is Status.UNCHANGED
    assert result.edges["a.Offer|owns|a.Core"].status is Status.CHANGED


def test_a_relation_pointing_elsewhere_is_one_changed_edge() -> None:
    """A retargeted relation keeps its id, so it is changed — not removed and added — and names both targets."""
    retargeted = {**CHOSEN, "target_id": "a.Detail"}
    result = compare(_graph([OFFER, CORE, DETAIL], [CHOSEN]), _graph([OFFER, CORE, DETAIL], [retargeted]))
    assert list(result.edges) == ["a.Offer|entity_relation|chosen"]
    assert result.edges["a.Offer|entity_relation|chosen"].differences == (
        Difference(("target_id",), Change.CHANGED, "a.Core", "a.Detail"),
    )
    assert result.edge_counts == Counts(changed=1)


def test_a_nested_difference_is_named_by_its_full_path() -> None:
    """A leaf deep in a property is named from the element's top; a nested key that came or went too."""
    schema_a = {"properties": {"erid": {"type": "string"}, "old": {"type": "integer"}}}
    schema_b = {"properties": {"erid": {"type": ["string", "null"]}, "new": {"type": "boolean"}}}
    result = compare(_graph([_node("a.X", json_schema=schema_a)], []), _graph([_node("a.X", json_schema=schema_b)], []))
    assert result.nodes["a.X"].differences == (
        Difference(("properties", "json_schema", "properties", "erid", "type"), Change.CHANGED, "string", ["string", "null"]),
        Difference(("properties", "json_schema", "properties", "new"), Change.ADDED, None, {"type": "boolean"}),
        Difference(("properties", "json_schema", "properties", "old"), Change.REMOVED, {"type": "integer"}, None),
    )


def test_a_list_is_one_value() -> None:
    """A list changed as a whole; its path ends at the property, never at an item."""
    result = compare(_graph([_node("a.X", tags=["a", "b"])], []), _graph([_node("a.X", tags=["b", "a"])], []))
    assert result.nodes["a.X"].differences == (Difference(("properties", "tags"), Change.CHANGED, ["a", "b"], ["b", "a"]),)


def test_a_rename_is_a_removal_and_an_addition() -> None:
    """Identity is the id: a node under a new id is another node."""
    result = compare(_graph([_node("a.Old", "Same")], []), _graph([_node("a.New", "Same")], []))
    assert result.nodes["a.Old"].status is Status.REMOVED
    assert result.nodes["a.New"].status is Status.ADDED


def test_two_equal_graphs_are_all_unchanged() -> None:
    """Nothing changed: every element unchanged, every count zero — whatever the order in the arrays."""
    older = _graph([OFFER, CORE, DETAIL], [CHOSEN])
    newer = _graph([DETAIL, CORE, OFFER], [CHOSEN])
    result = compare(older, newer)
    assert {item.status for item in [*result.nodes.values(), *result.edges.values()]} == {Status.UNCHANGED}
    assert result.node_counts == result.edge_counts == Counts()


def test_a_1_0_graph_compares_with_a_1_1_graph() -> None:
    """A 1.0 graph's edges get the ids 1.1 writes, special rules included, so the same model is unchanged."""
    transition = _edge("a.Life", "lifecycle_transition", "a.Done", from_state="open")
    plain = _edge("a.Offer", "uses", "a.Core")
    relation = _edge("a.Offer", "entity_relation", "a.Core", field_name="chosen")
    older = _graph([OFFER, CORE], [transition, plain, relation], "1.0")
    newer = _graph(
        [OFFER, CORE],
        [
            _with_id(transition, "a.Life|lifecycle_transition|a.Done|open"),
            _with_id(plain, "a.Offer|uses|a.Core"),
            _with_id(relation, "a.Offer|entity_relation|chosen"),
        ],
    )
    result = compare(older, newer)
    assert set(result.edges) == {"a.Life|lifecycle_transition|a.Done|open", "a.Offer|uses|a.Core", "a.Offer|entity_relation|chosen"}
    assert {item.status for item in result.edges.values()} == {Status.UNCHANGED}


@pytest.mark.parametrize(
    ("document", "words"),
    [
        ({"schema_version": "2.0", "nodes": [], "edges": []}, "schema_version '2.0'"),
        ({"schema_version": "1.1", "edges": []}, "no 'nodes' list"),
        ({"schema_version": "1.1", "nodes": [], "edges": {}}, "no 'edges' list"),
        ({"schema_version": "1.1", "nodes": ["a.X"], "edges": []}, "nodes[0] is not an object"),
        ({"schema_version": "1.1", "nodes": [{"label": "X"}], "edges": []}, "nodes[0] has no string 'id'"),
        ({"schema_version": "1.1", "nodes": [], "edges": [_edge("a", "uses", "b")]}, "edges[0] has no string 'id'"),
        ({"schema_version": "1.1", "nodes": [_node("a.X"), _node("a.X")], "edges": []}, "two nodes have the id 'a.X'"),
        (_graph([], [_edge("a", "uses", "b"), _edge("a", "uses", "b")], "1.0"), "two edges have the id 'a|uses|b'"),
        (_graph([], [_edge("a", "entity_relation", "b")], "1.0"), "'entity_relation': 'field_name'"),
        (_graph([], [_edge("a|x", "uses", "b")], "1.0"), "'source_id' contains '|'"),
    ],
)
def test_what_cannot_be_compared_is_refused(document: dict[str, Any], words: str) -> None:
    """Each refusal names its cause, and which side it came from."""
    with pytest.raises(GraphNotComparableError, match=r"Graph B|Edge of type") as refused:
        compare(_graph([], []), document)
    assert words in str(refused.value)


def test_the_older_side_is_named_when_it_is_the_one_refused() -> None:
    """A refusal of A says A."""
    with pytest.raises(GraphNotComparableError, match=r"^Graph A has schema_version None"):
        compare({"nodes": [], "edges": []}, _graph([], []))
