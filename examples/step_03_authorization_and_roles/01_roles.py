"""
01_roles.py — Authorization with role classes

Roles in AOA are classes, not strings. Business roles subclass ApplicationRole;
privilege inheritance follows Python subclassing — RoleChecker grants access via
issubclass(user_role, required_role). Two engine sentinels are used only in
@check_roles: GuestRole (open to everyone) and AnyRole (any authenticated user).

This example declares a role hierarchy (AdminRole is-a ManagerRole) and three
actions guarded differently, then runs them under three principals (anonymous,
manager, admin) and prints the allow/deny matrix.

Tutorial: ../../docs/index_draft.md  ·  topic: Authorization and roles

Run:
    uv run python examples/step_03_authorization_and_roles/01_roles.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


# ---------------------------------------------------------------------------
# Role hierarchy. AdminRole subclasses ManagerRole, so an admin counts as a
# manager: issubclass(AdminRole, ManagerRole) is True. Business roles inherit
# RoleMode.ALIVE from ApplicationRole — no @role_mode needed for live roles.
# ---------------------------------------------------------------------------

class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Can manage orders"


class AdminRole(ManagerRole):
    name = "admin"
    description = "Full control; includes manager privileges"


# ---------------------------------------------------------------------------
# Params / Result
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    action: str = Field(description="What was performed")


# ---------------------------------------------------------------------------
# Three actions, three access policies.
#   GuestRole     — open to everyone (stated explicitly; silence is not allowed)
#   ManagerRole  — managers and, by inheritance, admins
#   AdminRole    — admins only
# ---------------------------------------------------------------------------

@meta(description="View an order", domain=StoreDomain)
@check_roles(GuestRole)
class GetOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Return the order")
    async def get_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="viewed")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")


@meta(description="Purge all orders", domain=StoreDomain)
@check_roles(AdminRole)
class PurgeOrdersAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Purge orders")
    async def purge_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="purged")


# ---------------------------------------------------------------------------
# Runner — access matrix
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()

    principals = [
        ("anonymous", Context()),
        ("manager", Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))),
        ("admin", Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))),
    ]
    actions = [
        ("GetOrder    [GuestRole]", GetOrderAction),
        ("CancelOrder [ManagerRole]", CancelOrderAction),
        ("PurgeOrders [AdminRole]", PurgeOrdersAction),
    ]

    for user_name, ctx in principals:
        print(f"\nUser: {user_name}")
        for action_name, action_cls in actions:
            try:
                await machine.run(ctx, action_cls(), OrderParams(order_id="ord-001"))
                print(f"  {action_name:<26} -> allowed")
            except AuthorizationError:
                print(f"  {action_name:<26} -> denied")


asyncio.run(main())
