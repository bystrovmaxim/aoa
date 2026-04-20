# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, source and target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
then **source** and **target** interchange ids, kinds, host objects, and a single
**ArchiMate-style relationship** for the edge.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseGraphNode.node_id  +  edges: list[BaseGraphEdge(...)]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    BaseGraphEdge(
        edge_name="domain",
        is_dag=False,
        source_node_id="pkg.actions.MyAction",
        source_node_type="Action",
        source_node_obj=MyAction,
        target_node_id="pkg.domains.SystemDomain",
        target_node_type="Domain",
        target_node_obj=SystemDomain,
        edge_relationship=EdgeRelationship.ASSOCIATION,
    )

Edge case: same ``edge_name`` on different nodes — distinguish by ``source_node_id``.
"""

from __future__ import annotations

from dataclasses import dataclass

from graph.edge_relationship import EdgeRelationship


@dataclass(init=False, frozen=True)
class BaseGraphEdge:
    """
    AI-CORE-BEGIN
    ROLE: Interchange edge descriptor (slot, DAG, source/target ids, kinds, hosts, relationship).
    CONTRACT: ``edge_relationship`` uses :class:`~graph.edge_relationship.EdgeRelationship` (ArchiMate-style kinds).
    INVARIANTS: Frozen; ``is_dag`` is always set explicitly by the caller.
    AI-CORE-END
    """

    edge_name: str
    is_dag: bool
    source_node_id: str
    source_node_type: str
    source_node_obj: object
    target_node_id: str
    target_node_type: str
    target_node_obj: object
    edge_relationship: EdgeRelationship

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        source_node_id: str,
        source_node_type: str,
        source_node_obj: object,
        target_node_id: str,
        target_node_type: str,
        target_node_obj: object,
        edge_relationship: EdgeRelationship,
    ) -> None:
        object.__setattr__(self, "edge_name", edge_name)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "source_node_id", source_node_id)
        object.__setattr__(self, "source_node_type", source_node_type)
        object.__setattr__(self, "source_node_obj", source_node_obj)
        object.__setattr__(self, "target_node_id", target_node_id)
        object.__setattr__(self, "target_node_type", target_node_type)
        object.__setattr__(self, "target_node_obj", target_node_obj)
        object.__setattr__(self, "edge_relationship", edge_relationship)
