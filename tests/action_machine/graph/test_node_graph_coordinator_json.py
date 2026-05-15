# tests/action_machine/graph/test_node_graph_coordinator_json.py
"""Tests for :meth:`~aoa.graph.node_graph_coordinator.NodeGraphCoordinator.to_json` (graph + action_machine)."""

from __future__ import annotations

import json
from typing import Any

import networkx as nx
import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from aoa.action_machine.graph_model.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode
from aoa.graph.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.graph.composition_graph_edge import CompositionGraphEdge
from aoa.graph.node_graph_coordinator import NodeGraphCoordinator


class _Axis:
    """Single host type for a tiny interchange fixture."""


class _ParamsNode(BaseGraphNode[object]):
    def __init__(self, node_id: str) -> None:
        super().__init__(
            node_id=node_id,
            node_type="Params",
            label=node_id,
            properties={},
            node_obj=object(),
        )


class _ParamsHarnessNode(BaseGraphNode[object]):
    def __init__(self, *, host_id: str, companion: BaseGraphNode[Any], edge: BaseGraphEdge) -> None:
        super().__init__(
            node_id=host_id,
            node_type="Params",
            label=host_id,
            properties={},
            node_obj=object(),
        )
        object.__setattr__(self, "_companion", companion)
        object.__setattr__(self, "_edge", edge)

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return [self._companion]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return [self._edge]


class _HarnessInspector(BaseGraphNodeInspector[_Axis]):
    def __init__(self, root: BaseGraphNode[object]) -> None:
        self._root_node = root

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        if cls is _Axis:
            return self._root_node
        return None


class _EmptyInspector(BaseGraphNodeInspector[_Axis]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return None


def test_to_json_raises_before_build() -> None:
    with pytest.raises(RuntimeError, match="only available after a successful build"):
        NodeGraphCoordinator().to_json()


def test_to_json_empty_graph_round_trip() -> None:
    coord = NodeGraphCoordinator()
    coord.build([_EmptyInspector()], export_json_schema=GRAPH_JSON_SCHEMA)
    raw = coord.to_json()
    assert json.loads(raw) == {"edges": [], "nodes": [], "schema_version": "1.0"}


def test_to_json_validates_minimal_params_graph() -> None:
    right = _ParamsNode("pkg.right")
    edge = CompositionGraphEdge(
        edge_name="field",
        is_dag=False,
        target_node_id=right.node_id,
        target_node=right,
    )
    left = _ParamsHarnessNode(host_id="pkg.left", companion=right, edge=edge)
    coord = NodeGraphCoordinator()
    coord.build([_HarnessInspector(left)], export_json_schema=GRAPH_JSON_SCHEMA)
    payload = json.loads(coord.to_json())
    assert payload["schema_version"] == "1.0"
    assert {n["id"] for n in payload["nodes"]} == {"pkg.left", "pkg.right"}
    assert len(payload["edges"]) == 1
    assert payload["edges"][0]["type"] == "field"


class _MiniAxisAction:
    """Isolated inspector root (no subclasses): emit a single ``ActionGraphNode``."""


class _MiniAxisDomain:
    """Isolated inspector root: emit ``DomainGraphNode(SystemDomain)``."""


class _MiniAxisApplication:
    """Isolated inspector root: emit ``ApplicationGraphNode``."""


class _MiniAxisParams:
    """Isolated inspector root: emit ``ParamsGraphNode(PingAction.Params)``."""


class _MiniAxisResult:
    """Isolated inspector root: emit ``ResultGraphNode(PingAction.Result)``."""


class _MiniAxisRole:
    """Isolated inspector root: emit ``RoleGraphNode(NoneRole)``."""


class _InspectPingAction(BaseGraphNodeInspector[_MiniAxisAction]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
        from tests.action_machine.scenarios.domain_model.ping_action import PingAction

        return ActionGraphNode(PingAction) if cls is _MiniAxisAction else None


class _InspectSystemDomain(BaseGraphNodeInspector[_MiniAxisDomain]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
        from tests.action_machine.scenarios.domain_model.domains import SystemDomain

        return DomainGraphNode(SystemDomain) if cls is _MiniAxisDomain else None


class _InspectApplication(BaseGraphNodeInspector[_MiniAxisApplication]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.application.application import Application
        from aoa.action_machine.graph_model.nodes.application_graph_node import ApplicationGraphNode

        return ApplicationGraphNode(Application) if cls is _MiniAxisApplication else None


class _InspectPingParams(BaseGraphNodeInspector[_MiniAxisParams]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.graph_model.nodes.params_graph_node import ParamsGraphNode
        from tests.action_machine.scenarios.domain_model.ping_action import PingAction

        return ParamsGraphNode(PingAction.Params) if cls is _MiniAxisParams else None


class _InspectPingResult(BaseGraphNodeInspector[_MiniAxisResult]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.graph_model.nodes.result_graph_node import ResultGraphNode
        from tests.action_machine.scenarios.domain_model.ping_action import PingAction

        return ResultGraphNode(PingAction.Result) if cls is _MiniAxisResult else None


class _InspectNoneRole(BaseGraphNodeInspector[_MiniAxisRole]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        from aoa.action_machine.auth.none_role import NoneRole
        from aoa.action_machine.graph_model.nodes.role_graph_node import RoleGraphNode

        return RoleGraphNode(NoneRole) if cls is _MiniAxisRole else None


def test_to_json_ping_action_mini_graph_round_trip() -> None:
    """Real ``PingAction`` interchange subgraph validates against ``GRAPH_JSON_SCHEMA`` and round-trips."""
    coord = NodeGraphCoordinator()
    coord.build(
        [
            _InspectPingAction(),
            _InspectSystemDomain(),
            _InspectApplication(),
            _InspectPingParams(),
            _InspectPingResult(),
            _InspectNoneRole(),
        ],
        export_json_schema=GRAPH_JSON_SCHEMA,
    )
    raw = coord.to_json()
    payload = json.loads(raw)
    assert payload["schema_version"] == "1.0"
    assert any(n.get("type") == "Action" for n in payload["nodes"])
    assert any(n.get("type") == "Domain" for n in payload["nodes"])
    assert any(n.get("type") == "Params" for n in payload["nodes"])
    assert any(n.get("type") == "Result" for n in payload["nodes"])
    edge_types = {e["type"] for e in payload["edges"]}
    assert "domain" in edge_types
    assert "generic:params" in edge_types
    assert "generic:result" in edge_types


def test_graph_json_schema_rejects_invalid_payload() -> None:
    validator = Draft202012Validator(GRAPH_JSON_SCHEMA)
    with pytest.raises(ValidationError):
        validator.validate({"schema_version": "1.0"})
    with pytest.raises(ValidationError):
        validator.validate(
            {
                "schema_version": "1.0",
                "nodes": [
                    {
                        "id": "x",
                        "type": "UnknownInterchangeNodeKind",
                        "label": "x",
                        "properties": {},
                    },
                ],
                "edges": [],
            },
        )


def _networkx_from_export_payload(payload: dict[str, Any]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in payload["nodes"]:
        nid = node["id"]
        graph.add_node(nid, **node)
    for edge in payload["edges"]:
        graph.add_edge(edge["source_id"], edge["target_id"], **edge)
    return graph


def test_to_json_payload_rebuilds_networkx_graph() -> None:
    right = _ParamsNode("pkg.right")
    edge = CompositionGraphEdge(
        edge_name="field",
        is_dag=False,
        target_node_id=right.node_id,
        target_node=right,
    )
    left = _ParamsHarnessNode(host_id="pkg.left", companion=right, edge=edge)
    coord = NodeGraphCoordinator()
    coord.build([_HarnessInspector(left)], export_json_schema=GRAPH_JSON_SCHEMA)
    payload = json.loads(coord.to_json())
    graph = _networkx_from_export_payload(payload)
    assert graph.number_of_nodes() == len(payload["nodes"])
    assert graph.number_of_edges() == len(payload["edges"])


def test_networkx_payload_supports_type_filters() -> None:
    coord = NodeGraphCoordinator()
    coord.build(
        [
            _InspectPingAction(),
            _InspectSystemDomain(),
            _InspectApplication(),
            _InspectPingParams(),
            _InspectPingResult(),
            _InspectNoneRole(),
        ],
        export_json_schema=GRAPH_JSON_SCHEMA,
    )
    payload = json.loads(coord.to_json())
    graph = _networkx_from_export_payload(payload)
    action_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "Action"]
    assert len(action_nodes) >= 1
    depends_edges = [(u, v) for u, v, data in graph.edges(data=True) if data.get("type") == "@depends"]
    assert depends_edges == []
