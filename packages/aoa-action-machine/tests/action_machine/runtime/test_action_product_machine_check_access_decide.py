"""ActionProductMachine.check_access_decide() — AccessVerdict(s) without executing the action.

One method, two ``@overload`` shapes: a single action, or a list of ``(action, params)``
pairs. The list shape is the primitive; the single-action shape recurses into this same
method with a one-item list and unwraps the result — see the method's own docstring.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import CheckAccessDecideBatchSizeExceededError
from aoa.action_machine.intents.access_control import (
    FORBIDDEN_OBJECT,
    Allowed,
    Gate,
    Refused,
    Undecided,
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
from ...support.domain_model.roles import AdminRole, ManagerRole

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

    @access_decide
    async def check_probe_access_decide(
        self,
        params: CheckProbeAction.Params,
        context: Context,
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


@meta(description="machine.check_access_decide probe — a second, distinct action class", domain=SystemDomain)
@check_roles(ManagerRole)
class OtherCheckProbeAction(BaseAction["OtherCheckProbeAction.Params", "OtherCheckProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(default=True)

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: OtherCheckProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OtherCheckProbeAction.Result:
        return OtherCheckProbeAction.Result(ok=True)


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


# ── List form ────────────────────────────────────────────────────────────────


async def test_list_form_returns_verdicts_in_input_order(machine: ActionProductMachine) -> None:
    _reset()
    verdicts = await machine.check_access_decide(
        _admin_context(),
        [
            (CheckProbeAction, CheckProbeAction.Params(key="A")),
            (CheckProbeAction, CheckProbeAction.Params(key="B")),
        ],
    )
    assert all(isinstance(verdict, Allowed) for verdict in verdicts)
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_list_form_handles_two_different_action_classes(machine: ActionProductMachine) -> None:
    """Each item resolves its own action_node/role graph — admin-only vs manager-only."""
    _reset()
    verdicts = await machine.check_access_decide(
        _admin_context(),
        [
            (CheckProbeAction, CheckProbeAction.Params()),
            (OtherCheckProbeAction, OtherCheckProbeAction.Params()),
        ],
    )
    assert isinstance(verdicts[0], Allowed)
    assert isinstance(verdicts[1], Refused)
    assert verdicts[1].gate is Gate.CHECK_ROLES  # the admin context carries no ManagerRole


async def test_one_failing_item_does_not_affect_the_others(machine: ActionProductMachine) -> None:
    _reset()
    _raise_for_keys.add("B")
    verdicts = await machine.check_access_decide(
        _admin_context(),
        [
            (CheckProbeAction, CheckProbeAction.Params(key="A")),
            (CheckProbeAction, CheckProbeAction.Params(key="B")),
            (CheckProbeAction, CheckProbeAction.Params(key="C")),
        ],
    )
    assert isinstance(verdicts[0], Allowed)
    assert isinstance(verdicts[1], Undecided)
    assert verdicts[1].gate is Gate.ACCESS_DECIDE
    assert "boom for key='B'" not in str(verdicts[1].model_dump())
    assert isinstance(verdicts[2], Allowed)


async def test_list_form_reports_each_item_independently(machine: ActionProductMachine) -> None:
    """One list call, four items: allowed, the roles step, the condition step, the object
    step — and none of them bleeds into another."""
    _reset()
    _guard_deny_keys.add("guard-denied")
    _access_decide_deny_keys.add("decide-denied")
    verdicts = await machine.check_access_decide(
        _admin_context(),
        [
            (CheckProbeAction, CheckProbeAction.Params(key="ok")),
            (OtherCheckProbeAction, OtherCheckProbeAction.Params()),
            (CheckProbeAction, CheckProbeAction.Params(key="guard-denied")),
            (CheckProbeAction, CheckProbeAction.Params(key="decide-denied")),
        ],
    )
    allowed_verdict, roles_verdict, guard_verdict, object_verdict = verdicts
    assert isinstance(allowed_verdict, Allowed)
    assert isinstance(roles_verdict, Refused) and roles_verdict.gate is Gate.CHECK_ROLES
    assert isinstance(guard_verdict, Refused) and guard_verdict.gate is Gate.GUARD
    assert isinstance(object_verdict, Refused) and object_verdict.gate is Gate.ACCESS_DECIDE


async def test_batch_larger_than_max_check_access_decide_batch_size_is_rejected_up_front() -> None:
    _reset()
    small_machine = ActionProductMachine(cache_coordinator=None, max_check_access_decide_batch_size=2)
    items = [(CheckProbeAction, CheckProbeAction.Params(key=k)) for k in ("A", "B", "C")]
    with pytest.raises(CheckAccessDecideBatchSizeExceededError) as exc_info:
        await small_machine.check_access_decide(_admin_context(), items)
    assert exc_info.value.item_count == 3
    assert exc_info.value.max_check_access_decide_batch_size == 2
    assert _access_decide_calls["n"] == 0


async def test_single_form_matches_first_item_of_equivalent_list_call(machine: ActionProductMachine) -> None:
    _reset()
    single = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params(key="A"))
    _reset()
    (from_list,) = await machine.check_access_decide(
        _admin_context(), [(CheckProbeAction, CheckProbeAction.Params(key="A"))]
    )
    assert single == from_list
