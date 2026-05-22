# tests/action_machine/graph_model/test_graph_node_generalization_edges.py
"""PR-3: ``parent_*`` edges included in ``get_all_edges()`` on axis graph nodes (plan §I.6)."""

from __future__ import annotations

from pydantic import Field
from tests.action_machine.graph_model.test_parent_generalization_edges import (
    _ChildGenDomain,
    _ChildGenRole,
)
from tests.action_machine.scenarios.domain_model.domains import TestDomain

from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.nodes.domain_graph_node import DomainGraphNode
from aoa.action_machine.graph.nodes.role_graph_node import RoleGraphNode
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


@meta(description="PR-3 parent action for graph node tests", domain=TestDomain)
@check_roles(NoneRole)
class _Pr3ParentAction(BaseAction["_Pr3ParentAction.Params", "_Pr3ParentAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        message: str = Field(description="Message")

    @summary_aspect("Summary")
    async def pong_summary(
        self,
        params: _Pr3ParentAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> _Pr3ParentAction.Result:
        return self.Result(message="p")


@meta(description="PR-3 child action", domain=TestDomain)
@check_roles(NoneRole)
class _Pr3ChildAction(_Pr3ParentAction):
    @summary_aspect("Summary")
    async def pong_summary(
        self,
        params: _Pr3ParentAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> _Pr3ParentAction.Result:
        return _Pr3ParentAction.Result(message="c")


def test_action_graph_node_appends_parent_action_last() -> None:
    node = ActionGraphNode(_Pr3ChildAction)
    names = [e.edge_name for e in node.get_all_edges()]
    assert names[-1] == "parent_action"
    pa = [e for e in node.get_all_edges() if e.edge_name == "parent_action"]
    assert len(pa) == 1
    assert pa[0].target_node_id == TypeIntrospection.full_qualname(_Pr3ParentAction)


def test_role_graph_node_application_then_parent_role() -> None:
    node = RoleGraphNode(_ChildGenRole)
    assert [e.edge_name for e in node.get_all_edges()] == ["application", "parent_role"]


def test_domain_graph_node_application_then_parent_domain() -> None:
    node = DomainGraphNode(_ChildGenDomain)
    assert [e.edge_name for e in node.get_all_edges()] == ["application", "parent_domain"]


def test_role_graph_node_none_role_no_parent_when_system_role_excluded() -> None:
    node = RoleGraphNode(NoneRole)
    assert [e.edge_name for e in node.get_all_edges()] == ["application"]
