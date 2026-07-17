# packages/aoa-fastapi-adapter/tests/support/permissions_fixtures.py
"""
Role and action fixtures for the ``/permissions/resolve`` test suite (issue #130, PR 1).

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

A minimal, self-contained role cascade (mirroring ``aoa-action-machine``'s own
test-support convention, not imported from it — see ``domain_model.py``'s
docstring on why this package's tests don't reach into another package's test
tree) plus one manager-only action, so the resolver's role-gate (levels 1/2)
can be exercised end-to-end against a real ``ActionProductMachine``.
"""

from pydantic import Field

from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domain_model import OrdersDomain


@role_mode(RoleMode.ALIVE)
class ManagerRole(ApplicationRole):
    """Manager — granted access to ``CancelOrderAction`` below."""

    name = "manager"
    description = "Manager."


@role_mode(RoleMode.ALIVE)
class UserRole(ApplicationRole):
    """Ordinary user — not granted access to ``CancelOrderAction`` below."""

    name = "user"
    description = "Standard user."


@meta(description="Cancel an order (manager only)", domain=OrdersDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction["CancelOrderAction.Params", "CancelOrderAction.Result"]):
    """Manager-only action — drives role-gate allow/deny resolver tests."""

    class Params(BaseParams):
        """``CancelOrderAction`` parameters — the order to cancel."""

        order_id: int = Field(description="Order identifier")

    class Result(BaseResult):
        """``CancelOrderAction`` result — the new order status."""

        status: str = Field(description="New order status")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self,
        params: "CancelOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "CancelOrderAction.Result":
        return CancelOrderAction.Result(status="cancelled")
