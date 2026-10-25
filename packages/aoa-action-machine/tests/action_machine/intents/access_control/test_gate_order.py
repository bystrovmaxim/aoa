"""The order of the steps: what the early ones need, and what a refusal does not wait for.

The first steps decide who is calling and which roles they hold, and they decide it
before the call's parameters are looked at — which is why a caller without the role
receives a refusal even when there are no usable parameters at all, and why a refusal
is never a parameter error.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import (
    GATES,
    GATES_AT_OBJECT,
    GATES_BEFORE_RUN,
    Allowed,
    Gate,
    Refused,
    cascade,
)
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole, UserRole

_SEEN: dict[str, list[Any]] = {"object": []}


@pytest.fixture(autouse=True)
def _reset_seen() -> None:
    """Forget what the later step was handed in the previous test."""
    for key in _SEEN:
        _SEEN[key].clear()


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    """The machine under test, without a cache."""
    return ActionProductMachine(cache_coordinator=None)


@meta(description="order: role-gated with an object step", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectGatedAction(BaseAction["ObjectGatedAction.Params", "ObjectGatedAction.Result"]):
    """An operation whose object step may read the parameters."""

    class Params(BaseParams):
        """One input the later step could read."""

        order_id: str = "ORD-1"

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow every caller the role requirement admitted")
    async def object_gated_access_decide(
        self,
        params: ObjectGatedAction.Params,
        box: ToolsBox,
        connections: Connections,
    ) -> Allowed:
        """Record the parameters the object step was handed, and allow."""
        _SEEN["object"].append(params)
        return Allowed()

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectGatedAction.Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ObjectGatedAction.Result:
        """Produce the operation's result."""
        return ObjectGatedAction.Result()


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
        self, params: GuestAction.Params, state: BaseState, box: ToolsBox, connections: Connections
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
        self, params: AnyRoleAction.Params, state: BaseState, box: ToolsBox, connections: Connections
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


def _malformed_params() -> ObjectGatedAction.Params:
    """Parameters that never passed validation: a field of the wrong type."""
    return ObjectGatedAction.Params.model_construct(order_id=12345)


def test_the_pre_run_phase_is_the_two_early_steps() -> None:
    """The run exists only between the phases; the early phase is two steps, the later one."""
    assert GATES_BEFORE_RUN == (Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES)
    assert GATES_AT_OBJECT == (Gate.ACCESS_DECIDE,)
    assert GATES == GATES_BEFORE_RUN + GATES_AT_OBJECT


def test_the_condition_steps_are_gone() -> None:
    """The shared condition and its helper left with the mechanism."""
    assert not hasattr(cascade, "guard_gate")
    assert not hasattr(cascade, "guard_answer")


@pytest.mark.parametrize("params", [None, "malformed"], ids=["no parameters", "malformed parameters"])
async def test_an_early_refusal_does_not_wait_for_the_parameters(
    machine: ActionProductMachine, params: str | None
) -> None:
    """A caller without the role is refused whether the parameters exist, are usable, or are not."""
    handed = None if params is None else _malformed_params()
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(_user_without_the_role(), ObjectGatedAction(), handed)
    assert excinfo.value.verdict.gate is Gate.CHECK_ROLES
    assert _SEEN == {"object": []}


async def test_a_refusal_is_never_a_parameter_error(machine: ActionProductMachine) -> None:
    """Malformed parameters do not turn a refusal into a validation failure."""
    with pytest.raises(AccessDenied):
        await machine.run(_user_without_the_role(), ObjectGatedAction(), _malformed_params())
    assert _SEEN == {"object": []}


async def test_the_question_path_decides_without_parameters_too(machine: ActionProductMachine) -> None:
    """Asking in advance needs no parameters to answer about the early steps."""
    verdict = await machine.check_access_decide(_user_without_the_role(), ObjectGatedAction, None)
    assert isinstance(verdict, Refused)
    assert verdict.gate is Gate.CHECK_ROLES
    assert _SEEN == {"object": []}


@pytest.mark.parametrize("params", ["proper", "malformed"], ids=["proper parameters", "malformed parameters"])
async def test_the_object_step_receives_the_parameters_once_the_early_steps_pass(
    machine: ActionProductMachine, params: str
) -> None:
    """When the role step passes, the object step is handed the call's parameters."""
    handed = ObjectGatedAction.Params(order_id="ORD-7") if params == "proper" else _malformed_params()
    await machine.run(_admin(), ObjectGatedAction(), handed)
    assert _SEEN["object"] == [handed]


async def test_an_operation_open_to_guests_admits_a_caller_without_credentials(
    machine: ActionProductMachine,
) -> None:
    """A guest declaration means an anonymous caller may pass."""
    await machine.run(Context(), GuestAction(), GuestAction.Params())


async def test_an_operation_that_asks_for_any_role_refuses_a_caller_without_roles(
    machine: ActionProductMachine,
) -> None:
    """Asking for "any role" refuses a caller who holds none — today's shape of an identity refusal."""
    with pytest.raises(AccessDenied) as excinfo:
        await machine.run(_caller_without_roles(), AnyRoleAction(), AnyRoleAction.Params())
    assert excinfo.value.verdict.gate is Gate.CHECK_ROLES
