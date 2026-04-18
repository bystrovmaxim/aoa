# src/action_machine/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot name + target id + DAG flag).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic link from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), the target vertex interchange id (dotted path), and
whether the edge participates in **acyclicity** (DAG) reasoning for that link class.

The **source** vertex is always ``BaseGraphNode.id`` for the hosting node — it is not
redundant on the edge object.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.id  +  links: list[BaseGraphEdge(link_name, target_id, is_dag)]

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``link_name`` is the slot key (e.g. ``domain``, ``params``).
- ``target_id`` is the interchange id of the referenced vertex (``qualified_dotted_name``).
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
        is_dag=False,
    )

Edge case: same ``link_name`` on different nodes — distinguish by the host ``BaseGraphNode.id``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``target_id`` is not validated against a live graph. ``is_dag`` does not enforce acyclicity by itself.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Minimal typed record for (link slot, target id, DAG participation) on a host node.
CONTRACT: Frozen ``link_name`` + ``target_id`` + ``is_dag``; construction only via constructor.
INVARIANTS: Source id is the containing node — interchange shape only.
EXTENSION POINTS: Specializations may add factory methods or wrap coordinator ``GraphEdge``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(init=False, frozen=True)
class BaseGraphEdge:
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot name + target vertex id + DAG flag).
    CONTRACT: ``link_name`` = slot; ``target_id`` = referenced vertex id; ``is_dag`` = include in acyclicity check.
    INVARIANTS: Frozen; strings are opaque; ``is_dag`` is always set explicitly by the caller.
    AI-CORE-END
    """

    link_name: str
    target_id: str
    is_dag: bool

    def __init__(
        self,
        link_name: str,
        target_id: str,
        is_dag: bool,
    ) -> None:
        object.__setattr__(self, "link_name", link_name)
        object.__setattr__(self, "target_id", target_id)
        object.__setattr__(self, "is_dag", is_dag)
