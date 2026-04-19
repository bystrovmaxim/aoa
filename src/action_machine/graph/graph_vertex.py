# src/action_machine/graph/graph_vertex.py
"""
Frozen interchange vertex for the coordinator graph (spec graph.md §10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    links: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphVertex:
    """One coordinator graph vertex (interchange shape)."""

    id: str
    node_type: str
    label: str
    properties: dict[str, Any]
    links: list[str] = field(default_factory=list)
