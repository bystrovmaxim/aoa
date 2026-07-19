"""ActionProductMachine.check_access_decide() — BaseVerdict(s) without executing the action (step 7).

One method, two ``@overload`` shapes: a single action, or a list of ``(action, params)``
pairs. The list shape is the primitive; the single-action shape recurses into this same
method with a one-item list and unwraps the result — see the method's own docstring.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
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
@check_roles(AdminRole, guard=_guard, reason=FailSecurityVerdict("guard rejected"))
class CheckProbeAction(BaseAction["CheckProbeAction.Params", "CheckProbeAction.Result"]):
    class Params(BaseParams):
        key: str = Field(default="")

    class Result(BaseResult):
        ok: bool = Field(default=True)

    async def access_decide(
        self,
        params: CheckProbeAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailSecurityVerdict | AllowedVerdict:
        _access_decide_calls["n"] += 1
        if params.key in _raise_for_keys:
            raise RuntimeError(f"boom for key={params.key!r}")
        if not _access_decide_result["value"] or params.key in _access_decide_deny_keys:
            return FailSecurityVerdict("access_decide rejected")
        return AllowedVerdict()

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


async def test_allowed_true_when_everything_passes(machine: ActionProductMachine) -> None:
    _reset()
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert verdict == AllowedVerdict()
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_level_1_when_role_does_not_match(machine: ActionProductMachine) -> None:
    _reset()
    verdict = await machine.check_access_decide(Context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, FailSecurityVerdict)
    assert verdict.reason == "FORBIDDEN_ROLE"
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_level_2_when_guard_rejects(machine: ActionProductMachine) -> None:
    _reset()
    _guard_result["value"] = False
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, FailSecurityVerdict)
    assert verdict.reason == "guard rejected"
    assert _regular_calls["n"] == 0
    assert _summary_calls["n"] == 0


async def test_level_3_when_access_decide_rejects(machine: ActionProductMachine) -> None:
    """access_decide's own denial-reason mechanism: it returns FailSecurityVerdict
    directly, with whatever reason the action's author chose -- no more raw
    AuthorizationError text."""
    _reset()
    _access_decide_result["value"] = False
    verdict = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params())
    assert isinstance(verdict, FailSecurityVerdict)
    assert verdict.reason == "access_decide rejected"
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
    assert verdicts == [AllowedVerdict(), AllowedVerdict()]
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
    assert verdicts[0] == AllowedVerdict()
    assert isinstance(verdicts[1], FailSecurityVerdict)
    assert verdicts[1].reason == "FORBIDDEN_ROLE"  # admin context does not carry ManagerRole


async def test_one_failing_item_does_not_affect_the_others(machine: ActionProductMachine) -> None:
    """An unexpected exception becomes a FailErrorVerdict -- the check itself failed,
    it is not a real "no", and must not be confused with one."""
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
    assert verdicts[0] == AllowedVerdict()
    assert verdicts[1].kind == "FailErrorVerdict"
    # An unexpected exception's reason is its class name, not its message text.
    assert verdicts[1].reason == "RuntimeError"
    assert verdicts[2] == AllowedVerdict()


async def test_list_form_reports_independent_reasons_for_all_three_gates(machine: ActionProductMachine) -> None:
    """One list call, four items: allowed, role-denied, guard-denied, access_decide-denied — none bleed into another."""
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
    allowed_verdict, role_denied_verdict, guard_denied_verdict, decide_denied_verdict = verdicts
    assert allowed_verdict == AllowedVerdict()
    assert isinstance(role_denied_verdict, FailSecurityVerdict) and role_denied_verdict.reason == "FORBIDDEN_ROLE"
    assert isinstance(guard_denied_verdict, FailSecurityVerdict) and guard_denied_verdict.reason == "guard rejected"
    assert isinstance(decide_denied_verdict, FailSecurityVerdict)
    assert decide_denied_verdict.reason == "access_decide rejected"


async def test_single_form_matches_first_item_of_equivalent_list_call(machine: ActionProductMachine) -> None:
    _reset()
    single = await machine.check_access_decide(_admin_context(), CheckProbeAction, CheckProbeAction.Params(key="A"))
    _reset()
    (from_list,) = await machine.check_access_decide(
        _admin_context(), [(CheckProbeAction, CheckProbeAction.Params(key="A"))]
    )
    assert single == from_list
