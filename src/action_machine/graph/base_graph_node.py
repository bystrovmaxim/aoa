# src/action_machine/graph/base_graph_node.py
"""
BaseGraphNode — generic frozen node (id, node_type, label, properties, links).

``BaseGraphNode(obj)`` calls :meth:`parse`; it must return an object with attributes
``id``, ``node_type``, ``label``, ``properties``, ``links`` (typically
:class:`types.SimpleNamespace`). Because the node is frozen, the constructor uses
:func:`object.__setattr__` (assignment ``self.id = ...`` is not allowed on frozen instances).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from action_machine.graph.base_graph_edge import BaseGraphEdge

T = TypeVar("T", bound=object)


class BaseGraphNodeParseError(RuntimeError):
    """Raised when the base :meth:`BaseGraphNode.parse` is not overridden."""


@dataclass(init=False, frozen=True)
class BaseGraphNode(Generic[T]):
    id: str
    node_type: str
    label: str
    properties: dict[str, Any]
    links: list[BaseGraphEdge]

    def __init__(self, obj: T) -> None:
        item = self.parse(obj)
        object.__setattr__(self, "id", item.id)
        object.__setattr__(self, "node_type", item.node_type)
        object.__setattr__(self, "label", item.label)
        object.__setattr__(self, "properties", dict(item.properties))
        object.__setattr__(self, "links", list(item.links))

    @classmethod
    def parse(cls, obj: T) -> Any:
        """
        Single ``obj: T``. Return a small object with fields
        ``id``, ``node_type``, ``label``, ``properties``, ``links`` (``list[BaseGraphEdge]``).
        Use e.g. ``return SimpleNamespace(id=..., node_type=..., ...)``.
        """
        raise BaseGraphNodeParseError(
            "BaseGraphNode.parse() is not implemented on the base class; override in a subclass.",
        )
