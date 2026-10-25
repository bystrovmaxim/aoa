"""Check and run carry the same refusal.
Run: .venv/bin/python examples/step_03_authorization_and_roles/07_three_answers.py
"""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
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
    """Identify the order to cancel."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the cancelled order."""

    order_id: str = Field(description="Cancelled order identifier")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse every cancellation while the service is paused")
    async def cancel_order_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """The object rule always refuses, with a reason."""
        return Refused("CANCELLATIONS_PAUSED")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """Check and run carry the same refusal."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    assert answer.model_dump(mode="json") == {
        "kind": "refused",
        "gate": "ACCESS_DECIDE",
        "reason": "CANCELLATIONS_PAUSED",
    }
    print("check:", answer.model_dump(mode="json"))
    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        assert exc.verdict == answer
        assert str(exc) == "Access denied by ACCESS_DECIDE: CANCELLATIONS_PAUSED"
        print("run raises:", type(exc).__name__, str(exc))
        print("run verdict:", exc.verdict.model_dump(mode="json"))
    else:
        raise AssertionError("The refused execution must raise AccessDenied.")


if __name__ == "__main__":
    asyncio.run(main())
