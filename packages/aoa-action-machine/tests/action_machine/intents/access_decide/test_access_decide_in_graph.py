"""The declared object check is reachable from the assembled graph.

The graph is what everything else reads — introspection, the introspection UI, and
anything built on top of the interchange form — so an object check that only the
runtime could find would be a declaration nobody could see (FR-019).
"""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from aoa.action_machine.graph.edges.access_decide_graph_edge import AccessDecideGraphEdge
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.nodes.access_decide_graph_node import AccessDecideGraphNode
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import Allowed
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole


@meta(description="graph: an operation that declares an object check", domain=SystemDomain)
@check_roles(AdminRole)
class VisibleCheckAction(BaseAction["VisibleCheckAction.Params", "VisibleCheckAction.Result"]):
    """An operation whose declared check must appear in the graph."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow every caller the role requirement admitted")
    async def visible_access_decide(
        self,
        params: VisibleCheckAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Allowed:
        """Answer that the object may be touched."""
        return Allowed()


@meta(description="graph: an operation that declares nothing", domain=SystemDomain)
@check_roles(AdminRole)
class InvisibleCheckAction(BaseAction["InvisibleCheckAction.Params", "InvisibleCheckAction.Result"]):
    """An operation with no object check to show."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@pytest.fixture(scope="module")
def action_node() -> ActionGraphNode[Any]:
    """The interchange node of the operation that declares a check."""
    return ActionGraphNode(VisibleCheckAction)


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    """The whole assembled graph, in its interchange form."""
    return cast("dict[str, Any]", json.loads(create_node_graph_coordinator().to_json()))


class TestTheNodeOfTheOperation:
    def test_the_edge_carries_the_declaration(self, action_node: ActionGraphNode[Any]) -> None:
        assert len(action_node.access_decide) == 1
        assert isinstance(action_node.access_decide[0], AccessDecideGraphEdge)
        assert action_node.access_decide[0].edge_name == "@access_decide"

    def test_the_check_is_reachable_from_the_operation(self, action_node: ActionGraphNode[Any]) -> None:
        node = action_node.get_access_decide_graph_node()
        assert isinstance(node, AccessDecideGraphNode)
        assert node.label == "visible_access_decide"

    def test_the_node_is_identified_by_the_operation_and_the_method(self, action_node: ActionGraphNode[Any]) -> None:
        node = action_node.get_access_decide_graph_node()
        assert node is not None
        assert node.node_id == f"{TypeIntrospection.full_qualname(VisibleCheckAction)}:visible_access_decide"
        assert node.node_type == "AccessDecide"

    def test_the_node_carries_the_callable_itself(self, action_node: ActionGraphNode[Any]) -> None:
        node = action_node.get_access_decide_graph_node()
        assert node is not None
        assert node.node_obj is VisibleCheckAction.__dict__["visible_access_decide"]

    def test_the_check_travels_with_the_operation(self, action_node: ActionGraphNode[Any]) -> None:
        companions = action_node.get_companion_nodes()
        assert action_node.get_access_decide_graph_node() in companions

    def test_the_edge_is_among_the_operation_edges(self, action_node: ActionGraphNode[Any]) -> None:
        assert action_node.access_decide[0] in action_node.get_all_edges()

    def test_an_operation_without_a_check_has_no_edge(self) -> None:
        silent = ActionGraphNode(InvisibleCheckAction)
        assert silent.access_decide == []
        assert silent.get_access_decide_graph_node() is None


class TestTheAssembledGraph:
    def test_the_check_is_a_node_of_its_own_type(self, payload: dict[str, Any]) -> None:
        expected = f"{TypeIntrospection.full_qualname(VisibleCheckAction)}:visible_access_decide"
        nodes = [node for node in payload["nodes"] if node["type"] == "AccessDecide"]
        assert [node["id"] for node in nodes if node["id"] == expected] == [expected]
        assert all(node["label"] == "visible_access_decide" for node in nodes if node["id"] == expected)

    def test_the_edge_is_published(self, payload: dict[str, Any]) -> None:
        source = TypeIntrospection.full_qualname(VisibleCheckAction)
        target = f"{source}:visible_access_decide"
        edges = [
            edge
            for edge in payload["edges"]
            if edge["type"] == "@access_decide" and edge["source_id"] == source
        ]
        assert len(edges) == 1
        assert edges[0]["target_id"] == target

    def test_the_coordinator_indexes_the_node_type(self) -> None:
        coordinator = create_node_graph_coordinator()
        labels = [node.label for node in coordinator.get_nodes_by_type("AccessDecide")]
        assert "visible_access_decide" in labels

    def test_the_operation_without_a_check_adds_nothing(self, payload: dict[str, Any]) -> None:
        source = TypeIntrospection.full_qualname(InvisibleCheckAction)
        edges = [edge for edge in payload["edges"] if edge["type"] == "@access_decide"]
        assert all(edge["source_id"] != source for edge in edges)
