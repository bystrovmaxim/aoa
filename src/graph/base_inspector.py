# src/graph/base_inspector.py
"""BaseInspector — abstract base for graph inspectors."""

from __future__ import annotations

from typing import Any

from graph.base_graph_node import BaseGraphNode


class BaseInspector:
    """Base class for graph inspectors (optional :meth:`get_graph_nodes` hook)."""

    def get_graph_nodes(self) -> list[BaseGraphNode[Any]]:
        """
        Optional hook for interchange-node assembly (e.g. :class:`~graph.node_graph_coordinator.NodeGraphCoordinator`).

        Default implementation raises :exc:`NotImplementedError`. Subclasses that
        emit :class:`~graph.base_graph_node.BaseGraphNode` instances override this **instance**
        method.

        Raises:
            NotImplementedError: This inspector does not implement interchange-node emission.
        """
        msg = (
            f"{type(self).__qualname__}.get_graph_nodes is not implemented; "
            "override it on inspectors that emit interchange nodes."
        )
        raise NotImplementedError(msg)
