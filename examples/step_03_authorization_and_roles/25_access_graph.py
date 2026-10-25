"""The access graph separates roles from the declared object rule.
Run: .venv/bin/python examples/step_03_authorization_and_roles/25_access_graph.py
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
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
@check_roles(ManagerRole, ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse a manager whose account is not in the EU team")
    @context_requires("user.user_id")
    async def cancel_order_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> Verdict:
        """The role admits any manager; only the EU team passes the object rule."""
        if ctx.get("user.user_id").startswith("eu-"):
            return Allowed()
        return Refused("EU_TEAM_ONLY")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


def main() -> None:
    """Inspect the role choice and the object's declared context."""
    node = ActionGraphNode(CancelOrderAction)
    assert node.to_dict()["properties"] == {"description": "Cancel an order"}
    print("action:", node.to_dict()["properties"])
    assert len(node.roles) == 1
    role = node.roles[0].to_dict(source_id=node.node_id)
    assert role["properties"] == {}
    print("role:", role["type"], role["properties"])

    assert len(node.access_decide) == 1
    check = node.access_decide[0].target_node
    assert check.node_type == "AccessDecide"
    assert check.get_required_context_keys() == frozenset({"user.user_id"})
    print("object rule:", check.node_type, check.properties["description"])
    print("required context:", sorted(check.get_required_context_keys()))


if __name__ == "__main__":
    main()
