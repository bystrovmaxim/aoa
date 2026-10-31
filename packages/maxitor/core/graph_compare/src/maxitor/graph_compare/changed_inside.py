# packages/maxitor/core/graph_compare/src/maxitor/graph_compare/changed_inside.py
"""
changed_inside — what changed inside the elements a diagram draws without their parts.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``compare`` gives each element its own status, so a new field of a result leaves the
element that owns the result unchanged. A diagram that does not draw parts still has to
say that element changed. This walks each root's parts in both documents and lists what
changed there. The diagram names its roots and what it draws; the document's own
``relationship`` says what is owned, so no list of part types is kept here.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    root ──► its outgoing edges in A and in B
               target of a drawn type ──► not a part, skipped
               otherwise              ──► the edge is a part
               ``Composition`` or a ``through`` type ──► go on from the target
                                     anything else   ──► stop at the target

An edge that only follows a part added or removed is not listed beside it.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from typing import Any

from maxitor.graph_compare.compare import indexed
from maxitor.graph_compare.comparison import ChangedPart, Comparison, ElementComparison, Status

COMPOSITION = "Composition"
"""The ``relationship`` of an edge to what its source owns outright."""

LINKS = "Links"
"""The group of a part reached by an edge that does not own its target."""

_Side = tuple[dict[str, Mapping[str, Any]], dict[str, list[tuple[str, Mapping[str, Any]]]]]
"""One document's nodes by id, and each node's outgoing edges with their ids."""


def changed_inside(
    older: Mapping[str, Any],
    newer: Mapping[str, Any],
    comparison: Comparison,
    *,
    root_type: str,
    drawn_types: Collection[str],
    through: Collection[str],
) -> dict[str, tuple[ChangedPart, ...]]:
    """
    AI-CORE-BEGIN
    ROLE: List, per element of ``root_type`` found in both versions, every part that changed.
    CONTRACT: An edge to a node of ``drawn_types`` is not a part; every other edge is; the walk goes on through ``Composition`` edges and edges of a ``through`` type. A root with no changed part is left out; parts come by group, label and id.
    INVARIANTS: Pure; a part only in A is found by walking A; each node is walked once per root.
    FAILURES: ``GraphNotComparableError`` as ``compare`` raises it.
    AI-CORE-END
    """
    sides = (_side(older, "A"), _side(newer, "B"))
    result: dict[str, tuple[ChangedPart, ...]] = {}
    for root, item in comparison.nodes.items():
        if item.status in (Status.ADDED, Status.REMOVED) or _node(sides, root).get("type") != root_type:
            continue
        found = {(part.kind, part.id): part for part in _walked(root, sides, comparison, drawn_types, through)}
        if found:
            result[root] = tuple(sorted(found.values(), key=lambda part: (part.group, part.label, part.id)))
    return result


def _side(document: Mapping[str, Any], name: str) -> _Side:
    """A document's nodes and outgoing edges, as the walk reads them."""
    nodes, edges = indexed(document, name)
    outgoing: dict[str, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    for edge_id, edge in edges.items():
        outgoing[str(edge.get("source_id"))].append((edge_id, edge))
    return nodes, outgoing


def _node(sides: tuple[_Side, _Side], node_id: str) -> Mapping[str, Any]:
    """A node as B has it, or as A had it."""
    return sides[1][0].get(node_id) or sides[0][0].get(node_id) or {}


def _walked(
    root: str,
    sides: tuple[_Side, _Side],
    comparison: Comparison,
    drawn_types: Collection[str],
    through: Collection[str],
) -> Iterator[ChangedPart]:
    """Every changed part of ``root``, in either version."""
    seen = {root}
    queue = [(root, "")]
    while queue:
        source, inherited = queue.pop()
        for side in sides:
            for edge_id, edge in side[1].get(source, ()):
                target = str(edge.get("target_id"))
                node = _node(sides, target)
                if node.get("type") in drawn_types:
                    continue
                goes_on = edge.get("relationship") == COMPOSITION or edge.get("type") in through
                group = inherited or (_first_group(node, edge, through) if goes_on else LINKS)
                yield from _edge_part(edge_id, edge, node, group, comparison, goes_on)
                if goes_on and target not in seen:
                    seen.add(target)
                    yield from _node_part(target, node, group, comparison)
                    queue.append((target, group))


def _first_group(node: Mapping[str, Any], edge: Mapping[str, Any], through: Collection[str]) -> str:
    """The group a first step opens: a ``through`` target by its type, an owned one by its label."""
    return str(node.get("type") if edge.get("type") in through else node.get("label"))


def _edge_part(edge_id: str, edge: Mapping[str, Any], target: Mapping[str, Any], group: str, comparison: Comparison, owns: bool) -> Iterator[ChangedPart]:
    """The edge, when it changed for more than following an owned target in or out."""
    item = comparison.edges.get(edge_id)
    target_status = comparison.nodes.get(str(target.get("id")))
    follows = owns and target_status is not None and target_status.status in (Status.ADDED, Status.REMOVED)
    if item is not None and item.status is not Status.UNCHANGED and not follows:
        yield _part("edge", edge_id, str(target.get("label", "")), str(edge.get("type", "")), group, item)


def _node_part(node_id: str, node: Mapping[str, Any], group: str, comparison: Comparison) -> Iterator[ChangedPart]:
    """The node, when it changed."""
    item = comparison.nodes.get(node_id)
    if item is not None and item.status is not Status.UNCHANGED:
        yield _part("node", node_id, str(node.get("label", "")), str(node.get("type", "")), group, item)


def _part(kind: str, part_id: str, label: str, part_type: str, group: str, item: ElementComparison) -> ChangedPart:
    """One part as the list writes it."""
    return ChangedPart(kind=kind, id=part_id, label=label, type=part_type, group=group, status=item.status, differences=item.differences)
