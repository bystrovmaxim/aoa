# packages/aoa-action-machine/tests/action_machine/intents/access_decide/test_access_decide_session.py
"""
An object check may base its verdict on the caller's session id.

The session id is ordinary typed context data: a ``@access_decide`` method declares
``@context_requires(Ctx.User.session_id)`` and reads the value through its
``ContextView``, exactly like any other context field. Built-in role checks stay
independent of it — two callers with the same roles but different sessions get the
same built-in verdict.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Ctx
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import Allowed, Gate, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole


@meta(description="session: a check that allows only the trusted session", domain=SystemDomain)
@check_roles(GuestRole)
class SessionAwareAction(BaseAction["SessionAwareAction.Params", "SessionAwareAction.Result"]):
    """An object check that bases its verdict on the caller's session id."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Allow only the trusted session")
    @context_requires(Ctx.User.session_id)
    async def session_aware_access_decide(
        self,
        params: SessionAwareAction.Params,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> Verdict:
        """Refuse every caller whose session is not the trusted one."""
        if ctx.get(Ctx.User.session_id) != "session-A":
            return Refused("UNTRUSTED_SESSION")
        return Allowed()

    @summary_aspect("Answer")
    async def session_aware_summary(
        self,
        params: SessionAwareAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> SessionAwareAction.Result:
        """Produce the operation's result."""
        return SessionAwareAction.Result()


@meta(description="session: built-in roles only", domain=SystemDomain)
@check_roles(AdminRole)
class PlainRolesAction(BaseAction["PlainRolesAction.Params", "PlainRolesAction.Result"]):
    """No object check — the built-in role gate alone decides."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("Answer")
    async def plain_roles_summary(
        self,
        params: PlainRolesAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> PlainRolesAction.Result:
        """Produce the operation's result."""
        return PlainRolesAction.Result()


@pytest.fixture
def machine() -> ActionProductMachine:
    """A machine without a cache."""
    return ActionProductMachine(cache_coordinator=None)


def _caller(session_id: str, *, admin: bool = False) -> Context:
    """A caller whose sub is fixed and whose session (and optionally roles) vary."""
    roles = (AdminRole,) if admin else (GuestRole,)
    return Context(user=UserInfo(user_id="u-1", session_id=session_id, roles=roles))


async def test_a_policy_may_allow_one_session_and_refuse_another(machine: ActionProductMachine) -> None:
    trusted = await machine.check_access_decide(_caller("session-A"), SessionAwareAction, SessionAwareAction.Params())
    other = await machine.check_access_decide(_caller("session-B"), SessionAwareAction, SessionAwareAction.Params())

    assert isinstance(trusted, Allowed)
    assert isinstance(other, Refused)
    assert other.gate is Gate.ACCESS_DECIDE
    assert other.reason == "UNTRUSTED_SESSION"


async def test_built_in_role_gate_is_unchanged_across_sessions(machine: ActionProductMachine) -> None:
    """Two callers with the same roles but different sessions get the same built-in verdict."""
    verdict_a = await machine.check_access_decide(_caller("session-A", admin=True), PlainRolesAction, PlainRolesAction.Params())
    verdict_b = await machine.check_access_decide(_caller("session-B", admin=True), PlainRolesAction, PlainRolesAction.Params())

    assert isinstance(verdict_a, Allowed)
    assert isinstance(verdict_b, Allowed)
