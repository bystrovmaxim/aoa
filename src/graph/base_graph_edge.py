# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, target id, target facet kind, DAG flag, target class).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic link from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), the target vertex interchange id (dotted path), the
facet **target** ``node_type`` string (same convention as the target host's
:class:`~graph.base_graph_node.Payload.node_type`), the Python **target
class** when the target is a type (``target_class_ref``), and whether the edge
participates in **acyclicity** (DAG) reasoning.

The **source** vertex is always ``BaseGraphNode.payload.id`` for the hosting node — it is not
redundant on the edge object.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.payload.id  +  edges: list[BaseGraphEdge(...)]

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``link_name`` is the slot key (e.g. ``domain``, ``params``).
- ``target_id`` is the interchange id of the referenced vertex (``qualified_dotted_name``).
- ``target_node_type`` is the facet ``node_type`` of the target host (caller supplies it;
  match the corresponding ``*Node`` / :class:`Payload` ``node_type``).
- ``target_cls`` is the referenced type when the target is a class; use for facet materialization.
- ``is_dag``: if ``True``, consumers may include this edge when checking the graph for
  cycles along DAG-relevant arcs (same role as :attr:`GraphEdge.is_dag` on coordinator edges).
  If ``False``, the link is informational / exempt from that check.
- Instances are immutable (``frozen=True``).

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

Edge case: same ``link_name`` on different nodes — distinguish by the host ``BaseGraphNode.payload.id``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``target_id`` is not validated against a live graph. ``is_dag`` does not enforce acyclicity by itself.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Minimal typed record for (link slot, target id, target facet kind, DAG, target class).
CONTRACT: Caller sets ``target_node_type`` to the target host's facet ``node_type``.
INVARIANTS: Source id is the containing node — interchange shape only.
EXTENSION POINTS: Specializations may add factory methods or wrap coordinator ``GraphEdge``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(init=False, frozen=True)
class BaseGraphEdge:
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, target id, target facet kind, DAG flag, target class).
    CONTRACT: ``target_node_type`` = target vertex facet ``node_type`` (aligned with that host's ``Payload``).
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
