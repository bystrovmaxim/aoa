# packages/maxitor/core/graph_compare/src/maxitor/graph_compare/compare.py
"""
compare — two graph documents of the Open Gnomon Protocol, compared by ``id``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The protocol says two revisions are compared by ``id``, never by position, and
that their difference is the elements added, removed and changed under the same
``id`` (§4). This is that comparison, for any two documents — from a port, a file
or ``git show`` — with nothing but the standard library.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    A, B ──► check version, nodes, edges ──► index each side by id
                                               (a 1.0 edge's id from edge_ids.edge_id)
         ──► union of ids: only in B → added, only in A → removed,
                           in both → walk every field but ``id``
                                     objects key by key, anything else as one value
                                     differences → changed, none → unchanged
         ──► Comparison(nodes, edges, counts)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    result = compare(older, newer)
    result.edges["a.Offer|entity_relation|chosen"].differences
    # (Difference(path=('target_id',), change=<Change.CHANGED>, before='a.Core', after='a.Detail'),)
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Any

from maxitor.graph_compare.comparison import (
    Change,
    Comparison,
    Counts,
    Difference,
    ElementComparison,
    GraphNotComparableError,
    Status,
)
from maxitor.graph_compare.edge_ids import edge_id

KNOWN_VERSIONS = ("1.0", "1.1", "1.2")
"""The protocol's versions this comparison reads; any other is refused, never guessed."""


def compare(a: Mapping[str, Any], b: Mapping[str, Any]) -> Comparison:
    """
    AI-CORE-BEGIN
    ROLE: Compare two graph documents, A the older and B the newer, element by element.
    CONTRACT: Every node id and every edge id of A and B gets exactly one status; a changed element carries every difference by property path, with both values; the counts follow the statuses.
    INVARIANTS: Pure; position in an array never matters; a rename is a removal plus an addition.
    FAILURES: ``GraphNotComparableError`` when either document cannot be compared (see that class).
    AI-CORE-END
    """
    nodes_a, edges_a = indexed(a, "A")
    nodes_b, edges_b = indexed(b, "B")
    nodes, node_counts = _compared(nodes_a, nodes_b)
    edges, edge_counts = _compared(edges_a, edges_b)
    return Comparison(nodes=nodes, edges=edges, node_counts=node_counts, edge_counts=edge_counts)


def indexed(document: Mapping[str, Any], side: str) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    """A document's nodes and edges, each keyed by id in document order; refuse what cannot be compared."""
    if not isinstance(document, Mapping):
        raise GraphNotComparableError(f"Graph {side} is not an object.")
    version = document.get("schema_version")
    if version not in KNOWN_VERSIONS:
        raise GraphNotComparableError(f"Graph {side} has schema_version {version!r}; known: {', '.join(KNOWN_VERSIONS)}.")
    nodes = _by_id(document, "nodes", side, lambda node: node.get("id"))
    if version == "1.0":
        return nodes, _by_id(document, "edges", side, edge_id)
    return nodes, _by_id(document, "edges", side, lambda edge: edge.get("id"))


def _by_id(document: Mapping[str, Any], kind: str, side: str, id_of: Any) -> dict[str, Mapping[str, Any]]:
    """The elements of one kind keyed by the id ``id_of`` gives each; refuse a missing list, a bad element, a repeated id."""
    elements = document.get(kind)
    if not isinstance(elements, list):
        raise GraphNotComparableError(f"Graph {side} has no {kind!r} list.")
    keyed: dict[str, Mapping[str, Any]] = {}
    for position, element in enumerate(elements):
        if not isinstance(element, Mapping):
            raise GraphNotComparableError(f"Graph {side}: {kind}[{position}] is not an object.")
        element_id = id_of(element)
        if not isinstance(element_id, str) or not element_id:
            raise GraphNotComparableError(f"Graph {side}: {kind}[{position}] has no string 'id'.")
        if element_id in keyed:
            raise GraphNotComparableError(f"Graph {side}: two {kind} have the id {element_id!r}.")
        keyed[element_id] = element
    return keyed


def _compared(
    older: dict[str, Mapping[str, Any]], newer: dict[str, Mapping[str, Any]]
) -> tuple[Mapping[str, ElementComparison], Counts]:
    """Every id of either side with its comparison — A's order, then B's new ids — and the counts."""
    result: dict[str, ElementComparison] = {}
    added = removed = changed = 0
    for element_id, before in older.items():
        after = newer.get(element_id)
        if after is None:
            result[element_id] = ElementComparison(Status.REMOVED)
            removed += 1
            continue
        differences = tuple(_walk(_fields(before), _fields(after), ()))
        if differences:
            result[element_id] = ElementComparison(Status.CHANGED, differences)
            changed += 1
        else:
            result[element_id] = ElementComparison(Status.UNCHANGED)
    for element_id in newer:
        if element_id not in older:
            result[element_id] = ElementComparison(Status.ADDED)
            added += 1
    return MappingProxyType(result), Counts(added=added, removed=removed, changed=changed)


def _fields(element: Mapping[str, Any]) -> dict[str, Any]:
    """An element's fields but its ``id``: what can change while it stays the same element."""
    return {key: value for key, value in element.items() if key != "id"}


def _walk(before: Any, after: Any, path: tuple[str, ...]) -> Iterator[Difference]:
    """Every difference under ``path``: objects key by key in key order, anything else as one value."""
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        for key in sorted(before.keys() | after.keys()):
            inner = (*path, key)
            if key not in after:
                yield Difference(inner, Change.REMOVED, before=before[key])
            elif key not in before:
                yield Difference(inner, Change.ADDED, after=after[key])
            else:
                yield from _walk(before[key], after[key], inner)
        return
    if before != after:
        yield Difference(path, Change.CHANGED, before=before, after=after)
