# src/action_machine/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot name + target id).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic link from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``) and the target vertex interchange id (dotted path).

The **source** vertex is always ``BaseGraphNode.id`` for the hosting node — it is not
redundant on the edge object.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.id  +  links: list[BaseGraphEdge(link_name, target_id)]

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``link_name`` is the slot key (e.g. ``domain``, ``params``).
- ``target_id`` is the interchange id of the referenced vertex (``qualified_dotted_name``).
- Instances are immutable (``frozen=True``).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    BaseGraphEdge(link_name="domain", target_id="pkg.domains.SystemDomain")

Edge case: same ``link_name`` string on different nodes — distinguish by the host ``BaseGraphNode.id``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``target_id`` is not validated against a live graph.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Minimal typed record for (link slot, target id) on a host node.
CONTRACT: Frozen dataclass ``link_name`` + ``target_id``; construction only via constructor.
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
    ROLE: Interchange edge descriptor (slot name + target vertex id).
    CONTRACT: ``link_name`` = slot; ``target_id`` = referenced vertex id.
    INVARIANTS: Frozen; values are opaque strings for callers.
    AI-CORE-END
    """

    link_name: str
    target_id: str

    def __init__(self, link_name: str, target_id: str) -> None:
        object.__setattr__(self, "link_name", link_name)
        object.__setattr__(self, "target_id", target_id)
