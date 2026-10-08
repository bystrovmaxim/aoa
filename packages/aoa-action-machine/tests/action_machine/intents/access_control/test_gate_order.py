"""The order of the steps: what the early ones need, and what a refusal does not wait for.

The first steps decide who is calling and what they may do, and they decide it
before the call's parameters are looked at — which is why a caller without the
role receives a refusal even when there are no usable parameters at all, and why
a refusal is never a parameter error.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Allowed, Gate, Refused
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

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole, UserRole

_SEEN: dict[str, list[Any]] = {"guard": [], "object": []}


@pytest.fixture(autouse=True)
def _reset_seen() -> None:
    """Forget what the later steps were handed in the previous test."""
    for key in _SEEN:
        _SEEN[key].clear()


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    """The machine under test, without a cache."""
    return ActionProductMachine(cache_coordinator=None)


def _guard_records(user: Any, params: Any) -> bool:
    """Record the parameters the shared condition was handed, and allow."""
    _SEEN["guard"].append(params)
    return True


@meta(description="order: role-gated with a guard and an object step", domain=SystemDomain)
@check_roles(AdminRole, guard=_guard_records, guard_reason="RECORDS_ONLY")
class GuardedAction(BaseAction["GuardedAction.Params", "GuardedAction.Result"]):
    """An operation whose later steps may read the parameters."""

    class Params(BaseParams):
        """One input the later steps could read."""

        order_id: str = "ORD-1"

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow every caller the role requirement admitted")
    async def guarded_access_decide(
        self,
        params: GuardedAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Allowed:
        """Record the parameters the object step was handed, and allow."""
        _SEEN["object"].append(params)
        return Allowed()

    @summary_aspect("S")
    async def probe_summary(
        self, params: GuardedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuardedAction.Result:
        """Produce the operation's result."""
        return GuardedAction.Result()


@meta(description="order: open to guests", domain=SystemDomain)
@check_roles(GuestRole)
class GuestAction(BaseAction["GuestAction.Params", "GuestAction.Result"]):
    """An operation declared open to guests."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("S")
    async def probe_summary(
        self, params: GuestAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuestAction.Result:
        """Produce the operation's result."""
        return GuestAction.Result()


@meta(description="order: any role at all", domain=SystemDomain)
@check_roles(AnyRole)
class AnyRoleAction(BaseAction["AnyRoleAction.Params", "AnyRoleAction.Result"]):
    """An operation that asks only for a caller who holds some role."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("S")
    async def probe_summary(
        self, params: AnyRoleAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> AnyRoleAction.Result:
        """Produce the operation's result."""
        return AnyRoleAction.Result()


def _admin() -> Context:
    """A caller holding the role the operation lists."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)))


def _user_without_the_role() -> Context:
    """A caller who holds a role, just not the one the operation lists."""
    return Context(user=UserInfo(user_id="u-2", roles=(UserRole,)))


def _caller_without_roles() -> Context:
    """A caller who holds no active role at all."""
    return Context(user=UserInfo(user_id="u-3", roles=()))


def _malformed_params() -> GuardedAction.Params:
    """Parameters that never passed validation: a field of the wrong type."""
    return GuardedAction.Params.model_construct(order_id=12345)


@pytest.mark.parametrize("params", [None, "malformed"], ids=["no parameters", "malformed parameters"])
async def test_an_early_refusal_does_not_wait_for_the_parameters(
    machine: ActionProductMachine, params: str | None
) -> None:
    """A caller without the role is refused whether the parameters exist, are usable, or are not."""
    handed = None if params is None else _malformed_params()
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(_user_without_the_role(), GuardedAction(), handed)
    assert excinfo.value.verdict.gate is Gate.CHECK_ROLES
    assert _SEEN == {"guard": [], "object": []}


async def test_a_refusal_is_never_a_parameter_error(machine: ActionProductMachine) -> None:
    """Malformed parameters do not turn a refusal into a validation failure."""
    with pytest.raises(AccessDenied):
        await machine.run(_user_without_the_role(), GuardedAction(), _malformed_params())
    assert _SEEN == {"guard": [], "object": []}


async def test_the_question_path_decides_without_parameters_too(machine: ActionProductMachine) -> None:
    """Asking in advance needs no parameters to answer about the early steps."""
    verdict = await machine.check_access_decide(_user_without_the_role(), GuardedAction, None)
    assert isinstance(verdict, Refused)
    assert verdict.gate is Gate.CHECK_ROLES
    assert _SEEN == {"guard": [], "object": []}


def test_the_later_steps_are_handed_exactly_the_parameters_of_the_call() -> None:
    """A condition and an object step read the call's own parameters, not a copy of them."""
    assert GuardedAction.Params(order_id="ORD-7").order_id == "ORD-7"
    assert _malformed_params().order_id == 12345


@pytest.mark.parametrize("params", ["proper", "malformed"], ids=["proper parameters", "malformed parameters"])
async def test_the_later_steps_receive_the_parameters_once_the_early_ones_pass(
    machine: ActionProductMachine, params: str
) -> None:
    """When the early steps pass, the condition and the object step are handed the call's parameters."""
    handed = GuardedAction.Params(order_id="ORD-7") if params == "proper" else _malformed_params()
    await machine.run(_admin(), GuardedAction(), handed)
    assert _SEEN["guard"] == [handed]
    assert _SEEN["object"] == [handed]


async def test_an_operation_open_to_guests_admits_a_caller_without_credentials(
    machine: ActionProductMachine,
) -> None:
    """A guest declaration means an anonymous caller may pass; rejected credentials land with T018."""
    await machine.run(Context(), GuestAction(), GuestAction.Params())


async def test_an_operation_that_asks_for_any_role_refuses_a_caller_without_roles(
    machine: ActionProductMachine,
) -> None:
    """Asking for "any role" refuses a caller who holds none — today's shape of an identity refusal."""
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(_caller_without_roles(), AnyRoleAction(), AnyRoleAction.Params())
    assert excinfo.value.verdict.gate is Gate.CHECK_ROLES
