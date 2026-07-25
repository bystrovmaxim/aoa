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

from collections.abc import Mapping
from typing import Final

from pydantic import Field

from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, AllowedVerdict, FailSecurityVerdict
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

# The one order_id whose check blows up, so the EVALUATION_FAILED path is reachable
# from a test without monkeypatching anything.
CRASHING_ORDER_ID: Final = 99


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


# Owner lookup for the object-level fixture below. Server-side on purpose: the
# request must not be able to state who owns an order (see aoa-demo's own
# CancelOrderAction for the same shape, and audit-11 finding 2 for what happens
# when it can).
_ORDERS: Final[Mapping[int, str]] = {1: "alice", 2: "bob"}


@meta(description="Archive an order (object-level check)", domain=OrdersDomain)
@check_roles(ManagerRole)
class ArchiveOrderAction(BaseAction["ArchiveOrderAction.Params", "ArchiveOrderAction.Result"]):
    """Drives the resolver's object-level outcomes end-to-end over real HTTP.

    Three reachable outcomes, one per wire code the object-level contract promises:
    an allowed check, the shared ``FORBIDDEN_OBJECT`` denial (for both "no such
    order" and "someone else's order"), and a crash inside ``access_decide``,
    which the machine must report as ``EVALUATION_FAILED`` rather than a denial.
    """

    class Params(BaseParams):
        """``ArchiveOrderAction`` parameters — the order to archive."""

        order_id: int = Field(description="Order identifier")

    class Result(BaseResult):
        """``ArchiveOrderAction`` result — the new order status."""

        status: str = Field(description="New order status")

    async def access_decide(
        self,
        params: "ArchiveOrderAction.Params",
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailSecurityVerdict | AllowedVerdict:
        if params.order_id == CRASHING_ORDER_ID:
            raise ConnectionError(f"orders_db unreachable while reading order {params.order_id}")
        owner = _ORDERS.get(params.order_id)
        if owner is None or owner != context.user.user_id:
            return FORBIDDEN_OBJECT
        return AllowedVerdict()

    @summary_aspect("Archive the order")
    async def archive_summary(
        self,
        params: "ArchiveOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "ArchiveOrderAction.Result":
        return ArchiveOrderAction.Result(status="archived")
