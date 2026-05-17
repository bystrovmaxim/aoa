# packages/aoa-graph/src/aoa/graph/generalization_graph_edge.py
"""
GeneralizationGraphEdge — UML generalization (inheritance) interchange edge.

Exposes the fixed :data:`~aoa.graph.edge_relationship.GENERALIZATION` relationship and
provides :meth:`collect_direct_parents` — the single canonical algorithm for direct
Python bases used as generalization targets (see project plan §I.5).
"""

from __future__ import annotations

from typing import Generic, get_origin

from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.edge_relationship import GENERALIZATION, EdgeRelationship


def _class_sort_key(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


class GeneralizationGraphEdge(BaseGraphEdge):
    """Base graph edge with fixed ``GENERALIZATION`` relationship."""

    @property
    def edge_relationship(self) -> EdgeRelationship:
        """Return the fixed generalization relationship."""
        return GENERALIZATION

    @staticmethod
    def collect_direct_parents(host_cls: type, root: type) -> tuple[type, ...]:
        """
        Return direct generalization parent types for *host_cls* on the axis *root*.

        Direct bases are taken from ``__orig_bases__`` (when present) **and**
        ``__bases__``. ``typing.Generic`` subclasses may record only the parameterized
        root in ``__orig_bases__`` while ``__bases__`` lists the immediate superclass
        (e.g. ``class Child(ParentAction)`` on a ``BaseAction[P, R]`` axis); using both
        keeps parameterization (step toward ``get_origin``) without dropping the
        concrete parent. Transitive ancestors are never flattened into this result.
        """

        if not isinstance(host_cls, type):
            msg = f"host_cls must be a class, not {type(host_cls).__name__}"
            raise TypeError(msg)
        if not isinstance(root, type):
            msg = f"root must be a class, not {type(root).__name__}"
            raise TypeError(msg)

        if hasattr(host_cls, "__orig_bases__"):
            bases: tuple[object, ...] = (*host_cls.__orig_bases__, *host_cls.__bases__)
        else:
            bases = host_cls.__bases__

        normalized: set[type] = set()
        for base in bases:
            candidate = get_origin(base) or base
            if candidate is object:
                continue
            if not isinstance(candidate, type):
                continue
            if candidate is root:
                continue
            if candidate is Generic:
                continue
            if getattr(candidate, "_is_protocol", False):
                continue
            normalized.add(candidate)

        parents = {c for c in normalized if issubclass(c, root) and c is not root}
        return tuple(sorted(parents, key=_class_sort_key))
