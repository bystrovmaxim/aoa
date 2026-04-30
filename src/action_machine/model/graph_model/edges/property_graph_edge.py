# src/action_machine/model/graph_model/edges/property_graph_edge.py
"""
PropertyGraphEdge — COMPOSITION from Params → PropertyField interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params-schema computed / plain-property companions: composition with
``edge_name`` ``property:{name}`` from a params vertex to a
:class:`~action_machine.model.graph_model.property_field_graph_node.PropertyFieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params (source id + type)  ──{property:`name`}──►  PropertyFieldGraphNode
"""

from __future__ import annotations

from typing import Any

from action_machine.model.graph_model.property_field_graph_node import PropertyFieldGraphNode
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class PropertyGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge Params host → property-field vertex.
    CONTRACT: ``edge_name`` ``property:`` + stripped property name (``_`` when empty); ``is_dag`` False; ``target_node`` is the ``PropertyFieldGraphNode``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        params_node_id: str,
        params_node_type: str,
        property_node: PropertyFieldGraphNode,
        source_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        prop_name = property_node.node_obj.property_name.strip() or "_"
        super().__init__(
            edge_name=f"property",
            is_dag=False,
            source_node_id=params_node_id,
            source_node_type=params_node_type,
            source_node=source_node,
            target_node_id=property_node.node_id,
            target_node_type=property_node.node_type,
            target_node=property_node,
        )
