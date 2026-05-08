# tests/graph/test_node_graph_coordinator_companions.py
"""Coverage for recursive companion expansion in ``NodeGraphCoordinator``."""

from __future__ import annotations

from typing import Any

import pytest

from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.exceptions import DuplicateNodeError
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


class _Root:
    pass


class _Node(BaseGraphNode[object]):
    _companions: list[BaseGraphNode[Any]]

    def __init__(
        self,
        node_id: str,
        companions: list[BaseGraphNode[Any]] | None = None,
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type="Test",
            label=node_id,
            node_obj=object(),
        )
        object.__setattr__(self, "_companions", [] if companions is None else list(companions))

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return list(self._companions)


def test_node_graph_coordinator_recursively_includes_companions() -> None:
    grandchild = _Node("grandchild")
    child = _Node("child", [grandchild])
    root_node = _Node("root", [child])

    class _Inspector(BaseGraphNodeInspector[_Root]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return root_node if cls is _Root else None

    coord = NodeGraphCoordinator()
    coord.build([_Inspector()])

    assert {node.node_id for node in coord.get_all_nodes()} == {"root", "child", "grandchild"}


def test_node_graph_coordinator_rejects_duplicate_companion_ids_during_expansion() -> None:
    root_node = _Node("root", [_Node("root")])

    class _Inspector(BaseGraphNodeInspector[_Root]):
        def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
            return root_node if cls is _Root else None

    with pytest.raises(DuplicateNodeError, match="root"):
        NodeGraphCoordinator().build([_Inspector()])
