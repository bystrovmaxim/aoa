"""
02_grant.py — grant(role, when=...): per-role conditions

A bare role in @check_roles means "this role, no extra condition" — that's still
the plain, permanent shorthand, not a legacy form. grant(role, when=...) adds an
optional per-role condition, evaluated against the caller (UserInfo) only, after
its role has matched. Multiple grants are tried in declaration order with any()
semantics: the first grant whose role matches AND whose when=, if any, returns
True wins.

This example gives two roles their own conditions: a regional manager may only
act while their user_id carries their region's prefix; a global admin has no
condition at all and always passes once the role itself matches.

Tutorial: ../../docs/index_draft.md  ·  topic: Authorization and roles

Run:
    uv run python examples/step_03_authorization_and_roles/02_grant.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


# ---------------------------------------------------------------------------
# Roles. Both are plain business roles (no hierarchy) — grant() is what gives
# each one its own condition, not the role class itself.
# ---------------------------------------------------------------------------

class RegionalManagerRole(ApplicationRole):
    name = "regional_manager"
    description = "Can manage orders placed in their own region"


class GlobalAdminRole(ApplicationRole):
    name = "global_admin"
    description = "Can manage orders in any region"


# ---------------------------------------------------------------------------
# Params / Result
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    action: str = Field(description="What was performed")


# ---------------------------------------------------------------------------
# One action, two grants with different conditions:
#   grant(RegionalManagerRole, when=...) — role matches, but the condition also
#       has to hold: the caller's user_id must carry the "eu-" region prefix.
#   grant(GlobalAdminRole)               — role matches, no condition at all.
# grant()/guard= stay opt-in even here: this action has no guard=, since the
# per-role when= conditions are already enough to express the policy.
# ---------------------------------------------------------------------------

@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(
    grant(RegionalManagerRole, when=lambda user: user.user_id.startswith("eu-")),
    grant(GlobalAdminRole),
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")


# ---------------------------------------------------------------------------
# Runner — access matrix
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()

    principals = [
        ("anonymous", Context()),
        ("eu regional manager", Context(user=UserInfo(user_id="eu-m1", roles=(RegionalManagerRole,)))),
        ("us regional manager", Context(user=UserInfo(user_id="us-m1", roles=(RegionalManagerRole,)))),
        ("global admin", Context(user=UserInfo(user_id="a1", roles=(GlobalAdminRole,)))),
    ]

    for user_name, ctx in principals:
        try:
            await machine.run(ctx, CancelOrderAction(), OrderParams(order_id="ord-001"))
            print(f"{user_name:<24} -> allowed")
        except AuthorizationError:
            print(f"{user_name:<24} -> denied")


asyncio.run(main())
