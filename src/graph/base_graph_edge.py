# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, target id, target facet kind, DAG flag, target class).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic link from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), the target vertex interchange id (dotted path), the
facet **target** ``node_type`` string (same convention as the target host's
:attr:`~graph.base_graph_node.BaseGraphNode.node_type`), the Python **target
class** when the target is a type (``target_class_ref``), and whether the edge
participates in **acyclicity** (DAG) reasoning.

The **source** vertex is always :attr:`~graph.base_graph_node.BaseGraphNode.id` for the hosting node — it is not
redundant on the edge object.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.id  +  edges: list[BaseGraphEdge(...)]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    BaseGraphEdge(
        link_name="domain",
        target_id="pkg.domains.SystemDomain",
        target_node_type="Domain",
        is_dag=False,
        target_cls=SystemDomain,
    )

Edge case: same ``link_name`` on different nodes — distinguish by the host :attr:`~graph.base_graph_node.BaseGraphNode.id`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(init=False, frozen=True)
class BaseGraphEdge:
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, target id, target facet kind, DAG flag, target class).
    CONTRACT: ``target_node_type`` = target vertex facet ``node_type`` (aligned with that host's ``node_type``).
    INVARIANTS: Frozen; strings are opaque; ``is_dag`` is always set explicitly by the caller.
    AI-CORE-END
    """

    link_name: str
    target_id: str
    target_node_type: str
    is_dag: bool
    target_cls: type[Any]

    def __init__(
        self,
        link_name: str,
        target_id: str,
        target_node_type: str,
        is_dag: bool,
        target_cls: type[Any],
    ) -> None:
        object.__setattr__(self, "link_name", link_name)
        object.__setattr__(self, "target_id", target_id)
        object.__setattr__(self, "target_node_type", target_node_type)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "target_cls", target_cls)
