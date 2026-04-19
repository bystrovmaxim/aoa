# src/action_machine/graph/base_inspector.py
"""BaseInspector — abstract base for graph inspectors."""

from __future__ import annotations

from abc import ABC
from typing import Any

from action_machine.graph.base_graph_node import BaseGraphNode


class BaseInspector(ABC):
    """Abstract base for graph inspectors."""

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """
        Optional hook for interchange-node assembly (e.g. :class:`~action_machine.graph.node_graph_coordinator.NodeGraphCoordinator`).

        Default implementation raises :exc:`NotImplementedError`. Subclasses that
        emit :class:`~action_machine.graph.base_graph_node.BaseGraphNode` instances override this **instance**
        method.

        Returns:
            Zero or more interchange nodes.

        Raises:
            NotImplementedError: This inspector does not implement interchange-node emission.
        """
        msg = (
            f"{type(self).__qualname__}.get_graph_nodes is not implemented; "
            "override it on inspectors that emit interchange nodes."
        )
        raise NotImplementedError(msg)
