"""ActionGraphNode.properties["guard"]/["guard_reason"] — carries @check_roles guard=/reason= (access-control-cascade step 4)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import FailSecurityVerdict
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult

from ....support.domain_model.domains import TestDomain
from ....support.domain_model.roles import AdminRole


def _own_order_only(user: object, params: object) -> bool:
    return True


class TestActionGraphNodeGuard:
    def test_guard_defaults_to_none(self) -> None:
        @meta(description="no guard", domain=TestDomain)
        @check_roles(AdminRole)
        class _NoGuardAction(BaseAction["_NoGuardAction.Params", "_NoGuardAction.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(self, params, state, box, connections):
                return _NoGuardAction.Result()

        node = ActionGraphNode(_NoGuardAction)
        assert node.properties["guard"] is None
        assert node.properties["guard_reason"] is None

    def test_guard_carried_on_node_properties(self) -> None:
        @meta(description="with guard", domain=TestDomain)
        @check_roles(AdminRole, guard=_own_order_only, reason=FailSecurityVerdict("not the order owner"))
        class _GuardedAction(BaseAction["_GuardedAction.Params", "_GuardedAction.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(self, params, state, box, connections):
                return _GuardedAction.Result()

        node = ActionGraphNode(_GuardedAction)
        assert node.properties["guard"] is _own_order_only
        assert node.properties["guard_reason"] == FailSecurityVerdict("not the order owner")

    def test_to_dict_never_exports_guard(self) -> None:
        """``guard`` is runtime-only, like ``DependsGraphEdge``'s ``factory`` — never serialized."""

        @meta(description="with guard", domain=TestDomain)
        @check_roles(AdminRole, guard=_own_order_only, reason=FailSecurityVerdict("not the order owner"))
        class _GuardedAction(BaseAction["_GuardedAction.Params", "_GuardedAction.Result"]):
            class Params(BaseParams):
                dummy: str = Field(default="x")

            class Result(BaseResult):
                ok: bool = Field(default=True)

            @summary_aspect("s")
            async def build_summary(self, params, state, box, connections):
                return _GuardedAction.Result()

        node = ActionGraphNode(_GuardedAction)
        assert node.to_dict()["properties"] == {"description": "with guard"}
