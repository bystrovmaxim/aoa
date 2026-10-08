"""ActionProductMachine.check_access_decide() — one answer about one call, without running it.

One shape only: a single action with its params, and one verdict back — ``Allowed``,
``Refused`` naming its gate, or ``Undecided`` naming the step that could not tell. The
steps run in the order a real call would run them, and nothing of the operation itself
does: the tests below check the answer, the gate it names, and that the pipeline stays
untouched.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import (
    FORBIDDEN_OBJECT,
    Allowed,
    Gate,
    Refused,
    Verdict,
)
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
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

_regular_calls = {"n": 0}
_summary_calls = {"n": 0}
_access_decide_calls = {"n": 0}
_access_decide_result = {"value": True}
_guard_result = {"value": True}
_raise_for_keys: set[str] = set()
_guard_deny_keys: set[str] = set()
_access_decide_deny_keys: set[str] = set()


def _guard(user: object, params: object) -> bool:
    if params.key in _guard_deny_keys:  # type: ignore[attr-defined]
        return False
    return _guard_result["value"]


def _reset() -> None:
    _regular_calls["n"] = 0
    _summary_calls["n"] = 0
    _access_decide_calls["n"] = 0
    _access_decide_result["value"] = True
    _guard_result["value"] = True
    _raise_for_keys.clear()
    _guard_deny_keys.clear()
    _access_decide_deny_keys.clear()


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    return ActionProductMachine(cache_coordinator=None)


def _admin_context() -> Context:
    return Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))


@meta(description="machine.check_access_decide probe", domain=SystemDomain)
@check_roles(AdminRole, guard=_guard, guard_reason="CHECK_PROBE_GUARD")
class CheckProbeAction(BaseAction["CheckProbeAction.Params", "CheckProbeAction.Result"]):
    class Params(BaseParams):
        key: str = Field(default="")

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @access_decide("Allow every caller the role requirement admitted")
    async def check_probe_access_decide(
        self,
        params: CheckProbeAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Answer from the test's switches: raise, refuse, or the configured answer."""
        _access_decide_calls["n"] += 1
        if params.key in _raise_for_keys:
            raise RuntimeError(f"boom for key={params.key!r}")
        if params.key in _access_decide_deny_keys:
            return FORBIDDEN_OBJECT
        return Allowed() if _access_decide_result["value"] else FORBIDDEN_OBJECT

    @regular_aspect("noop")
    async def probe_regular_aspect(
        self,
        params: CheckProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict:
        _regular_calls["n"] += 1
        return {}

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: CheckProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> CheckProbeAction.Result:
        _summary_calls["n"] += 1
        return CheckProbeAction.Result(ok=True)


# ── Single-action form ──────────────────────────────────────────────────────


async def test_allowed_when_everything_passes(machine: ActionProductMachine) -> None:
    _reset()
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, Allowed)
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_check_roles_when_the_role_does_not_match(machine: ActionProductMachine) -> None:
    _reset()
    verdict = await machine.check_access_decide(Context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, Refused)
    assert verdict.gate is Gate.CHECK_ROLES
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_guard_when_the_condition_rejects(machine: ActionProductMachine) -> None:
    _reset()
    _guard_result["value"] = False
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, Refused)
    assert verdict.gate is Gate.GUARD
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_access_decide_when_the_object_check_rejects(machine: ActionProductMachine) -> None:
    _reset()
    _access_decide_result["value"] = False
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, Refused)
    assert verdict.gate is Gate.ACCESS_DECIDE
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_check_never_runs_the_pipeline_even_when_allowed(machine: ActionProductMachine) -> None:
    """Even a fully-allowed check must not execute @regular_aspect/@summary_aspect — check never runs()."""
    _reset()
    await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0
