"""ActionProductMachine — access_decide() gates run() before any aspect executes (step 6)."""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
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


@meta(description="access_decide denies unconditionally", domain=SystemDomain)
@check_roles(AdminRole)
class DenyAllAccessDecideAction(BaseAction["DenyAllAccessDecideAction.Params", "DenyAllAccessDecideAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    async def access_decide(
        self,
        params: DenyAllAccessDecideAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailSecurityVerdict | AllowedVerdict:
        return FailSecurityVerdict("denied unconditionally")

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


async def test_access_decide_false_raises_before_any_aspect(machine: ActionProductMachine) -> None:
    _summary_calls["n"] = 0
    with pytest.raises(AuthorizationError) as excinfo:
        await machine.run(_admin_context(), DenyAllAccessDecideAction(), DenyAllAccessDecideAction.Params())
    assert excinfo.value.level == 3
    assert excinfo.value.verdict == FailSecurityVerdict("denied unconditionally")
    assert _summary_calls["n"] == 0


async def test_role_check_still_denies_before_access_decide(machine: ActionProductMachine) -> None:
    """Level 1 (role) must still win over level 3 (access_decide) for an anonymous user —
    access_decide (which unconditionally returns False here) is never even reached."""
    _summary_calls["n"] = 0
    with pytest.raises(AuthorizationError) as excinfo:
        await machine.run(Context(), DenyAllAccessDecideAction(), DenyAllAccessDecideAction.Params())
    assert excinfo.value.level == 1
    assert _summary_calls["n"] == 0


@meta(description="access_decide allows explicitly", domain=SystemDomain)
@check_roles(AdminRole)
class AllowAccessDecideAction(BaseAction["AllowAccessDecideAction.Params", "AllowAccessDecideAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    async def access_decide(
        self,
        params: AllowAccessDecideAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailSecurityVerdict | AllowedVerdict:
        return AllowedVerdict()

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: AllowAccessDecideAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AllowAccessDecideAction.Result:
        return AllowAccessDecideAction.Result(ok=True)


async def test_access_decide_true_allows_run(machine: ActionProductMachine) -> None:
    result = await machine.run(_admin_context(), AllowAccessDecideAction(), AllowAccessDecideAction.Params())
    assert result.ok is True


@meta(description="access_decide not overridden — default True", domain=SystemDomain)
@check_roles(AdminRole)
class DefaultAccessDecideAction(BaseAction["DefaultAccessDecideAction.Params", "DefaultAccessDecideAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: DefaultAccessDecideAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> DefaultAccessDecideAction.Result:
        return DefaultAccessDecideAction.Result(ok=True)


async def test_default_access_decide_true_does_not_block_run(machine: ActionProductMachine) -> None:
    """Regression: actions that never override access_decide must keep working exactly as before."""
    result = await machine.run(_admin_context(), DefaultAccessDecideAction(), DefaultAccessDecideAction.Params())
    assert result.ok is True
