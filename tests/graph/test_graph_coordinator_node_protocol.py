"""Tests for ``GraphCoordinator`` node-protocol delegation."""

from __future__ import annotations

from action_machine.model.graph_model.regular_aspect_graph_node import (
    RegularAspectGraphNode,
)
from graph.base_graph_node import BaseGraphNode
from graph.graph_coordinator import GraphCoordinator


class _ActionHost:
    @staticmethod
    def run() -> None:
        pass


class _StubNode(BaseGraphNode[object]):
    def __init__(self) -> None:
        super().__init__(
            node_id="stub",
            node_type="Test",
            label="stub",
            properties={},
            node_obj=object(),
        )


class _StubNodeGraphCoordinator:
    def __init__(self) -> None:
        self.node_calls: list[tuple[str, str | None]] = []
        self.aspect_calls: list[type] = []
        self.node = _StubNode()
        self.regular_aspects = [RegularAspectGraphNode(_ActionHost.run)]

    def get_node_by_id(
        self,
        node_id: str,
        node_type: str | None = None,
    ) -> BaseGraphNode[object]:
        self.node_calls.append((node_id, node_type))
        return self.node

    def get_regular_aspect_nodes(
        self,
        action_cls: type,
    ) -> list[RegularAspectGraphNode]:
        self.aspect_calls.append(action_cls)
        return self.regular_aspects


def test_get_node_by_id_delegates_to_lazy_node_graph_coordinator(
    monkeypatch,
) -> None:
    stub = _StubNodeGraphCoordinator()
    call_count = 0

    def _factory() -> _StubNodeGraphCoordinator:
        nonlocal call_count
        call_count += 1
        return stub

    monkeypatch.setattr("graph.graph_coordinator.create_node_graph_coordinator", _factory)
    coord = GraphCoordinator()

    assert coord.get_node_by_id("abc", "Action") is stub.node
    assert coord.get_node_by_id("xyz") is stub.node
    assert stub.node_calls == [("abc", "Action"), ("xyz", None)]
    assert call_count == 1


def test_get_regular_aspect_nodes_delegates_to_lazy_node_graph_coordinator(
    monkeypatch,
) -> None:
    stub = _StubNodeGraphCoordinator()
    call_count = 0

    def _factory() -> _StubNodeGraphCoordinator:
        nonlocal call_count
        call_count += 1
        return stub

    monkeypatch.setattr("graph.graph_coordinator.create_node_graph_coordinator", _factory)
    coord = GraphCoordinator()

    assert coord.get_regular_aspect_nodes(_ActionHost) == stub.regular_aspects
    assert coord.get_regular_aspect_nodes(_ActionHost) == stub.regular_aspects
    assert stub.aspect_calls == [_ActionHost, _ActionHost]
    assert call_count == 1
