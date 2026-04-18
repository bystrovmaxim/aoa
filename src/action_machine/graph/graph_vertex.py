# src/action_machine/graph/graph_vertex.py
"""
Frozen interchange vertex for the coordinator graph (spec graph.md §10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple


class GraphVertexParseError(RuntimeError):
    """Raised when :meth:`GraphVertex.parse` is invoked on the base class."""


class ParsedGraphVertex(NamedTuple):
    """
    Inline struct produced by :meth:`GraphVertex.parse` — ``GraphVertex`` fields
    without retaining a reference to the parsed source object.
    """

    id: str
    node_type: str
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class GraphVertex:
    """One coordinator graph vertex (interchange shape)."""

    id: str
    node_type: str
    label: str
    properties: dict[str, Any]

    @classmethod
    def parse(cls, obj: object) -> ParsedGraphVertex:
        """
        Map an arbitrary source object to interchange fields.

        The default implementation always raises; concrete subclasses override
        this method.

        Raises:
            GraphVertexParseError: Always on the base class.
        """
        raise GraphVertexParseError(
            "GraphVertex.parse() is not implemented on the base class; "
            "use a concrete subclass.",
        )
