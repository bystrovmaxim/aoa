"""GuestRole and AnyRole express different requirements.
Run: .venv/bin/python examples/step_03_authorization_and_roles/14_guest_and_any.py
"""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import AnyRole, ApplicationRole, GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.role_mode import RoleMode, role_mode
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

# %% Setup


class StoreDomain(BaseDomain):
    """Group the order operations."""

    name = "store"
    description = "Order management"


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    """Identify the order to view."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the requested order."""

    order_id: str = Field(description="Requested order identifier")


@meta(description="View an order", domain=StoreDomain)
@check_roles(GuestRole)
class PublicAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


@meta(description="View an order", domain=StoreDomain)
@check_roles(AnyRole)
class ProfileAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


@meta(description="View a public order subject to an object rule", domain=StoreDomain)
@check_roles(GuestRole)
class RestrictedPublicAction(PublicAction):
    """Leave roles open while refusing a closed order."""

    @access_decide("Refuse a closed order")
    async def public_access_decide(self, params: OrderParams, box: ToolsBox, connections: Connections) -> Verdict:
        """Check the order independently of caller roles."""
        if params.order_id.startswith("CLOSED-"):
            return Refused("ORDER_CLOSED")
        return Allowed()


@meta(description="Permit guests beside a manager alternative", domain=StoreDomain)
@check_roles(GuestRole, ManagerRole)
class GuestChoiceAction(PublicAction):
    """Keep the guest alternative open."""


@meta(description="Permit any active role beside a manager alternative", domain=StoreDomain)
@check_roles(AnyRole, ManagerRole)
class AnyChoiceAction(PublicAction):
    """Require an active role without narrowing to managers."""


class AuditorRole(ApplicationRole):
    """Permit independent auditing."""

    name = "auditor"
    description = "Review orders"


@role_mode(RoleMode.SILENCED)
class SuspendedRole(ManagerRole):
    """Suspend a manager's role permissions."""

    name = "suspended"
    description = "Suspended manager"


# %% Run


async def main() -> None:
    """GuestRole and AnyRole express different requirements."""
    machine = ActionProductMachine(cache_coordinator=None)
    anonymous = Context()
    member = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(anonymous, PublicAction, params)
    assert answer.model_dump(mode="json") == {"kind": "allowed"}
    print("guest, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(anonymous, ProfileAction, params)
    assert answer.model_dump(mode="json") == {"kind": "refused", "gate": "CHECK_ROLES", "reason": None}
    print("any, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(member, ProfileAction, params)
    assert answer.model_dump(mode="json") == {"kind": "allowed"}
    print("any, manager:", answer.model_dump(mode="json"))

    result = await machine.run(anonymous, PublicAction(), params)
    assert result.order_id == "ord-001"
    print("guest run:", result.model_dump(mode="json"))

    answer = await machine.check_access_decide(anonymous, RestrictedPublicAction, params)
    assert isinstance(answer, Allowed)
    closed = OrderParams(order_id="CLOSED-9")
    answer = await machine.check_access_decide(anonymous, RestrictedPublicAction, closed)
    assert answer == Refused("ORDER_CLOSED")
    print("guest with object rule:", answer.model_dump(mode="json"))
    try:
        await machine.run(anonymous, RestrictedPublicAction(), closed)
    except AccessDenied as exc:
        assert exc.verdict == answer
        assert str(exc) == "Access denied by ACCESS_DECIDE: ORDER_CLOSED"
        print(type(exc).__name__ + ":", str(exc))
    else:
        raise AssertionError("A guest must still obey the object rule.")

    answer = await machine.check_access_decide(anonymous, GuestChoiceAction, params)
    assert isinstance(answer, Allowed)
    print("guest beside manager:", answer.model_dump(mode="json"))
    auditor = Context(user=UserInfo(user_id="a-1", roles=(AuditorRole,)))
    answer = await machine.check_access_decide(auditor, AnyChoiceAction, params)
    assert isinstance(answer, Allowed)
    print("any beside manager, auditor:", answer.model_dump(mode="json"))
    identified = Context(user=UserInfo(user_id="known", roles=()))
    answer = await machine.check_access_decide(identified, AnyChoiceAction, params)
    assert answer.kind == "refused" and answer.gate.value == "CHECK_ROLES"
    print("any, identified without roles:", answer.model_dump(mode="json"))
    suspended = Context(user=UserInfo(user_id="s-1", roles=(SuspendedRole,)))
    answer = await machine.check_access_decide(suspended, AnyChoiceAction, params)
    assert answer.kind == "refused" and answer.gate.value == "CHECK_ROLES"
    print("any, silenced only:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
