"""ActionProductMachine — the declared object check gates run() before any aspect executes."""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Gate, Refused
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole

_summary_calls = {"n": 0}


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    return ActionProductMachine(cache_coordinator=None)


def _admin_context() -> Context:
    return Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))


@meta(description="the declared object check denies unconditionally", domain=SystemDomain)
@check_roles(AdminRole)
class DenyAllAccessDecideAction(BaseAction["DenyAllAccessDecideAction.Params", "DenyAllAccessDecideAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @access_decide("Refuse every caller")
    async def deny_all_access_decide(
        self,
        params: DenyAllAccessDecideAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Refused:
        """Refuse every object, without a reason of its own."""
        return FORBIDDEN_OBJECT

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: DenyAllAccessDecideAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> DenyAllAccessDecideAction.Result:
        _summary_calls["n"] += 1
        return DenyAllAccessDecideAction.Result(ok=True)


async def test_the_declared_check_refuses_before_any_aspect(machine: ActionProductMachine) -> None:
    _summary_calls["n"] = 0
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(_admin_context(), DenyAllAccessDecideAction(), DenyAllAccessDecideAction.Params())
    assert excinfo.value.verdict.gate is Gate.ACCESS_DECIDE
    assert _summary_calls["n"] == 0


async def test_role_check_still_denies_before_the_object_check(machine: ActionProductMachine) -> None:
    """Level 1 (role) must still win over level 3 (the object check) for an anonymous user —
    the declared check (which refuses every object here) is never even reached."""
    _summary_calls["n"] = 0
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(Context(), DenyAllAccessDecideAction(), DenyAllAccessDecideAction.Params())
    assert excinfo.value.verdict.gate is Gate.CHECK_ROLES
    assert _summary_calls["n"] == 0


@meta(description="the declared object check allows explicitly", domain=SystemDomain)
@check_roles(AdminRole)
class AllowAccessDecideAction(BaseAction["AllowAccessDecideAction.Params", "AllowAccessDecideAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @access_decide("Allow every caller")
    async def allow_everything_access_decide(
        self,
        params: AllowAccessDecideAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Allowed:
        """Allow every object."""
        return Allowed()

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: AllowAccessDecideAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AllowAccessDecideAction.Result:
        return AllowAccessDecideAction.Result(ok=True)


async def test_a_declared_check_that_allows_lets_the_run_continue(machine: ActionProductMachine) -> None:
    result = await machine.run(_admin_context(), AllowAccessDecideAction(), AllowAccessDecideAction.Params())
    assert result.ok is True


@meta(description="no object check declared at all", domain=SystemDomain)
@check_roles(AdminRole)
class NoDeclaredCheckAction(BaseAction["NoDeclaredCheckAction.Params", "NoDeclaredCheckAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: NoDeclaredCheckAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> NoDeclaredCheckAction.Result:
        return NoDeclaredCheckAction.Result(ok=True)


async def test_an_operation_that_declares_no_check_still_runs(machine: ActionProductMachine) -> None:
    """Regression: an operation with no object check is not restricted by one."""
    result = await machine.run(_admin_context(), NoDeclaredCheckAction(), NoDeclaredCheckAction.Params())
    assert result.ok is True
