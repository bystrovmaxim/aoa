# src/graph/base_graph_edge.py
"""
BaseGraphEdge — one outgoing interchange edge (slot, DAG flag, source and target identity).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represents one outgoing semantic edge from a :class:`BaseGraphNode`: the slot key
(e.g. ``domain``, ``params``), whether it participates in **acyclicity** (DAG) reasoning,
then **source** and **target** interchange ids, kinds, host objects, and **ArchiMate-style
relationship** at each end (arrow / connector semantics per endpoint).

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
        source_node_relationship=EdgeRelationship.ASSOCIATION,
        target_node_id="pkg.domains.SystemDomain",
        target_node_type="Domain",
        target_node_obj=SystemDomain,
        target_node_relationship=EdgeRelationship.ASSOCIATION,
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
    ROLE: Interchange edge descriptor (slot, DAG, source/target ids, kinds, hosts, per-end relationship).
    CONTRACT: ``*_node_relationship`` use :class:`~graph.edge_relationship.EdgeRelationship` (ArchiMate-style kinds).
    INVARIANTS: Frozen; ``is_dag`` is always set explicitly by the caller.
    AI-CORE-END
    """

    edge_name: str
    is_dag: bool
    source_node_id: str
    source_node_type: str
    source_node_obj: object
    source_node_relationship: EdgeRelationship
    target_node_id: str
    target_node_type: str
    target_node_obj: object
    target_node_relationship: EdgeRelationship

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        source_node_id: str,
        source_node_type: str,
        source_node_obj: object,
        source_node_relationship: EdgeRelationship,
        target_node_id: str,
        target_node_type: str,
        target_node_obj: object,
        target_node_relationship: EdgeRelationship,
    ) -> None:
        object.__setattr__(self, "edge_name", edge_name)
        object.__setattr__(self, "is_dag", is_dag)
        object.__setattr__(self, "source_node_id", source_node_id)
        object.__setattr__(self, "source_node_type", source_node_type)
        object.__setattr__(self, "source_node_obj", source_node_obj)
        object.__setattr__(self, "source_node_relationship", source_node_relationship)
        object.__setattr__(self, "target_node_id", target_node_id)
        object.__setattr__(self, "target_node_type", target_node_type)
        object.__setattr__(self, "target_node_obj", target_node_obj)
        object.__setattr__(self, "target_node_relationship", target_node_relationship)
