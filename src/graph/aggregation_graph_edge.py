"""
AggregationGraphEdge — convenience edge with fixed aggregation relationship.

Provide a thin ``BaseGraphEdge`` specialization that always uses
``edge_relationship=AGGREGATION`` while preserving the rest of the constructor
shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graph.base_graph_edge import BaseGraphEdge
from graph.edge_relationship import AGGREGATION

if TYPE_CHECKING:
    from graph.base_graph_node import BaseGraphNode


class AggregationGraphEdge(BaseGraphEdge):
    """Base graph edge with fixed ``AGGREGATION`` relationship."""

    def __init__(
        self,
        *,
        edge_name: str,
        is_dag: bool,
        source_node_id: str,
        source_node_type: str,
        source_node: BaseGraphNode[Any] | None = None,
        target_node_id: str,
        target_node_type: str,
        target_node: BaseGraphNode[Any] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name=edge_name,
            is_dag=is_dag,
            source_node_id=source_node_id,
            source_node_type=source_node_type,
            source_node=source_node,
            target_node_id=target_node_id,
            target_node_type=target_node_type,
            target_node=target_node,
            edge_relationship=AGGREGATION,
            properties=properties,
        )
