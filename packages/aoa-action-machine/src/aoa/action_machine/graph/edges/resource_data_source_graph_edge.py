# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/resource_data_source_graph_edge.py
"""
ResourceDataSourceGraphEdge — the aggregation edge from a resource to the data source it names.

Protocol 1.7 writes it as ``resource_data_source``: ``Aggregation``, ``is_dag`` true, no
properties. A resource has at most one, and a resource without a data source has none.

::

    ResourceGraphNode  ──resource_data_source──►  DataSourceGraphNode  ──application──►  Application
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.aggregation_graph_edge import AggregationGraphEdge
from aoa.action_machine.resources.base_data_source import BaseDataSource
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


class ResourceDataSourceGraphEdge(AggregationGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed aggregation edge ``resource → data source``.
    CONTRACT: ``edge_name`` ``resource_data_source``; target id is the data source's dotted class name; no properties.
    INVARIANTS: Frozen via ``AggregationGraphEdge`` base; at most one per resource.
    AI-CORE-END
    """

    EDGE_NAME = "resource_data_source"

    def __init__(self, data_source_cls: type[BaseDataSource]) -> None:
        super().__init__(
            edge_name=self.EDGE_NAME,
            is_dag=True,
            target_node_id=TypeIntrospection.full_qualname(data_source_cls),
            target_node=None,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }
