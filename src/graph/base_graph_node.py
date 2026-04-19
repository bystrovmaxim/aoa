# src/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen node (``payload``, ``obj``).

``BaseGraphNode(obj)`` calls :meth:`parse` with the same ``obj``. :meth:`parse` returns a
frozen :class:`Payload`; that value is stored as :attr:`payload`. The **original**
constructor argument is stored on :attr:`obj`.

``id``, ``node_type``, ``label``, ``properties``, and ``edges`` are read-only views of
:attr:`payload` (:func:`property` accessors for ``node.id``-style access).

Because the node is frozen, the constructor uses :func:`object.__setattr__`.

:meth:`to_facet_vertex` projects this node into a :class:`~graph.facet_vertex.FacetVertex`
for the classic coordinator ``build()`` pipeline. **Deprecated:** emit
:class:`DeprecationWarning`; prefer the facet snapshot / coordinator projection path for new code.
``node_name`` is :attr:`Payload.id`; ``node_class`` is ``obj`` (must be a ``type``). Each
:class:`~graph.base_graph_edge.BaseGraphEdge` carries ``target_node_type`` — the same
facet ``node_type`` string the target host would use in its :class:`Payload` (set by each ``*Node``
when building outgoing edges); projection passes it through to :class:`~graph.facet_edge.FacetEdge`.

``_base_link_to_facet_edge`` is **deprecated** as well; callers should build
:class:`~graph.facet_edge.FacetEdge` from :class:`~graph.base_graph_edge.BaseGraphEdge`
fields directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.common.deprecated import deprecated
from graph.base_graph_edge import BaseGraphEdge
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex


@deprecated("_base_link_to_facet_edge is deprecated and will be removed.")
def _base_link_to_facet_edge(link: BaseGraphEdge) -> FacetEdge:
    """Map ``BaseGraphEdge`` → ``FacetEdge``. Deprecated: construct ``FacetEdge`` at the call site."""
    return FacetEdge(
        target_node_type=link.target_node_type,
        target_name=link.target_id,
        edge_type=link.link_name,
        is_structural=link.is_dag,
        edge_meta=(),
        target_class_ref=link.target_cls,
    )


class BaseGraphNodeParseError(RuntimeError):
    """Raised when the base :meth:`BaseGraphNode.parse` is not overridden."""


@dataclass(frozen=True)
class Payload:
    """Interchange fields; returned by :meth:`BaseGraphNode.parse` and stored as :attr:`BaseGraphNode.payload`."""

    id: str
    node_type: str
    label: str
    properties: dict[str, Any]
    edges: list[BaseGraphEdge]


@dataclass(init=False, frozen=True)
class BaseGraphNode[T: object]:
    payload: Payload
    obj: T

    def __init__(self, obj: T) -> None:
        object.__setattr__(self, "payload", self.parse(obj))
        object.__setattr__(self, "obj", obj)

    @property
    def id(self) -> str:
        return self.payload.id

    @property
    def node_type(self) -> str:
        return self.payload.node_type

    @property
    def label(self) -> str:
        return self.payload.label

    @property
    def properties(self) -> dict[str, Any]:
        return self.payload.properties

    @property
    def edges(self) -> list[BaseGraphEdge]:
        return self.payload.edges

    @deprecated("BaseGraphNode.to_facet_vertex() is deprecated and will be removed.")
    def to_facet_vertex(self) -> FacetVertex:
        """
        Build a :class:`~graph.facet_vertex.FacetVertex` from ``payload`` and ``obj``.

        Deprecated: emits :class:`DeprecationWarning`; migrate to the facet snapshot / coordinator
        projection API.

        Requires ``obj`` to be a ``type`` (the owning class). ``node_meta`` is
        ``tuple(payload.properties.items())`` (insertion order).
        """
        host = self.obj
        if not isinstance(host, type):
            msg = f"BaseGraphNode.to_facet_vertex() requires obj to be a type, got {type(host)!r}"
            raise TypeError(msg)
        p = self.payload
        node_meta = tuple(p.properties.items())
        edges = tuple(
            FacetEdge(
                target_node_type=e.target_node_type,
                target_name=e.target_id,
                edge_type=e.link_name,
                is_structural=e.is_dag,
                edge_meta=(),
                target_class_ref=e.target_cls,
            )
            for e in p.edges
        )
        return FacetVertex(
            node_type=p.node_type,
            node_name=p.id,
            node_class=host,
            node_meta=node_meta,
            edges=edges,
        )

    @classmethod
    def parse(cls, obj: T) -> Payload:
        """Build and return a :class:`Payload` for ``obj``. Subclasses implement this."""
        raise BaseGraphNodeParseError(
            "BaseGraphNode.parse() is not implemented on the base class; override in a subclass.",
        )
