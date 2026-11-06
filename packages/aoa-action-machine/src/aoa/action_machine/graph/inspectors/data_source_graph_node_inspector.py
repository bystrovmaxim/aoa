# packages/aoa-action-machine/src/aoa/action_machine/graph/inspectors/data_source_graph_node_inspector.py
"""
DataSourceGraphNodeInspector — graph-node contributor for ``BaseDataSource`` subclasses.

Walks the loaded ``BaseDataSource`` subclass tree and emits one
:class:`~aoa.action_machine.graph.nodes.data_source_graph_node.DataSourceGraphNode` per class
that participates in interchange; a framework kind (``PostgresDataSource``) opts out with
:func:`~aoa.action_machine.graph.core.exclude_graph_model.exclude_graph_model`.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.nodes.data_source_graph_node import DataSourceGraphNode
from aoa.action_machine.resources.base_data_source import BaseDataSource


class DataSourceGraphNodeInspector(BaseGraphNodeInspector[BaseDataSource]):
    """
    AI-CORE-BEGIN
    ROLE: Emit ``DataSourceGraphNode`` rows for every loaded ``BaseDataSource`` subclass.
    CONTRACT: One node per visited data source class unless it declares ``exclude_graph_model``.
    AI-CORE-END
    """

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return DataSourceGraphNode(cls)
