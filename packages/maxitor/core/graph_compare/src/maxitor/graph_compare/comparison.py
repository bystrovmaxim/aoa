# packages/maxitor/core/graph_compare/src/maxitor/graph_compare/comparison.py
"""
Comparison — what comparing two graph documents gives: a status per element, the differences, the counts.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The result of :func:`~maxitor.graph_compare.compare.compare`, as plain frozen values
that any reader — a viewer, a CI job, a test — can walk without knowing how it was
computed. Every node and every edge of the two documents gets exactly one status;
a changed one carries each difference by its property path, with both values.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Comparison ─┬─ nodes: id ──► ElementComparison(status, differences)
                ├─ edges: id ──► ElementComparison(status, differences)
                └─ node_counts, edge_counts: Counts(added, removed, changed)

    Difference(path, change, before, after)   path from the element's top, e.g.
                                              ("properties", "json_schema", "type")
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    """What happened to one element between the older document A and the newer B."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class Change(StrEnum):
    """What happened to one property of a changed element."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class Difference:
    """
    One property of a changed element that differs between A and B.

    AI-CORE-BEGIN
    ROLE: Names one difference of a changed element by its path, with both values.
    CONTRACT: ``path`` starts at the element's top; ``before`` is A's value unless ``change`` is ``added``, ``after`` is B's unless it is ``removed``; the absent side is ``None``.
    INVARIANTS: ``path`` is never empty; a list is one value, so a path never names a list item.
    AI-CORE-END
    """

    path: tuple[str, ...]
    change: Change
    before: Any = None
    after: Any = None


@dataclass(frozen=True, slots=True)
class ElementComparison:
    """
    One node or edge as it compares between A and B.

    AI-CORE-BEGIN
    ROLE: The status of one element and, when it changed, what changed.
    CONTRACT: ``differences`` lists every differing property, in key order at each level.
    INVARIANTS: ``differences`` is non-empty exactly when ``status`` is ``changed``.
    AI-CORE-END
    """

    status: Status
    differences: tuple[Difference, ...] = ()


@dataclass(frozen=True, slots=True)
class Counts:
    """How many elements of one kind were added, removed and changed; unchanged ones are not counted."""

    added: int = 0
    removed: int = 0
    changed: int = 0


@dataclass(frozen=True, slots=True)
class Comparison:
    """
    Two graph documents compared by ``id``.

    AI-CORE-BEGIN
    ROLE: Everything a reader needs to draw or report what changed from A to B.
    CONTRACT: ``nodes`` and ``edges`` map every id of A and B to its ``ElementComparison``: A's ids in A's order, then the ids only B has, in B's order.
    INVARIANTS: Read-only; the counts agree with the statuses.
    AI-CORE-END
    """

    nodes: Mapping[str, ElementComparison]
    edges: Mapping[str, ElementComparison]
    node_counts: Counts
    edge_counts: Counts


class GraphNotComparableError(ValueError):
    """
    A document cannot be compared; the message says why.

    AI-CORE-BEGIN
    ROLE: The one refusal of ``compare``.
    CONTRACT: Raised for an unknown ``schema_version``, missing ``nodes``/``edges`` lists, an element that is not an object or has no string ``id``, two elements of one kind with one id, or a ``1.0`` edge whose id cannot be computed.
    AI-CORE-END
    """
