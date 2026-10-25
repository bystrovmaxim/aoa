"""ActionGraphNode — the action node carries no condition data; the object rule is its own node."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import TestDomain
from ....support.domain_model.roles import AdminRole


@meta(description="with object rule", domain=TestDomain)
@check_roles(AdminRole)
class _RuledAction(BaseAction["_RuledAction.Params", "_RuledAction.Result"]):
    """An operation that declares an object rule."""

    class Params(BaseParams):
        dummy: str = Field(default="x")

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @access_decide("Refuse a caller who is not the owner")
    async def ruled_access_decide(
        self,
        params: _RuledAction.Params,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        return Allowed()

    @summary_aspect("s")
    async def build_summary(
        self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> BaseResult:
        return _RuledAction.Result()


class TestActionGraphNodeProperties:
    def test_the_node_carries_only_the_description(self) -> None:
        @meta(description="no condition", domain=TestDomain)
        @check_roles(AdminRole)
        class _Action(BaseAction["_Action.Params", "_Action.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(
                self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
            ) -> BaseResult:
                return _Action.Result()

        node = ActionGraphNode(_Action)
        assert node.properties == {"description": "no condition"}
        assert "guard" not in node.properties
        assert "guard_reason" not in node.properties

    def test_to_dict_exports_no_condition_data(self) -> None:
        @meta(description="no condition", domain=TestDomain)
        @check_roles(AdminRole)
        class _Action(BaseAction["_Action.Params", "_Action.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(
                self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
            ) -> BaseResult:
                return _Action.Result()

        node = ActionGraphNode(_Action)
        assert node.to_dict()["properties"] == {"description": "no condition"}


class TestActionGraphNodeAccessDecide:
    def test_the_node_is_absent_when_the_operation_declares_no_object_rule(self) -> None:
        @meta(description="roles only", domain=TestDomain)
        @check_roles(AdminRole)
        class _RolesOnlyAction(BaseAction["_RolesOnlyAction.Params", "_RolesOnlyAction.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(
                self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
            ) -> BaseResult:
                return _RolesOnlyAction.Result()

        assert ActionGraphNode(_RolesOnlyAction).get_access_decide_graph_node() is None

    def test_the_node_is_present_when_the_operation_declares_an_object_rule(self) -> None:
        node = ActionGraphNode(_RuledAction)
        decide_node = node.get_access_decide_graph_node()
        assert decide_node is not None
        assert "Refuse a caller who is not the owner" in str(decide_node.properties)
