"""Reach the declared state object through a lifecycle.

Paid describes where an order stands in a process. The lifecycle defines how an order can reach it; the state object supplies its code, label and additional data.

Run: uv run python examples/step_20_entity/08_state.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseStateEntity, Lifecycle
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model


class OrderStateEntity(BaseStateEntity):
    """Describe a possible order state."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is required")

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")  # noqa: F821
    PAID = OrderStateEntity(code="paid", display_name="Payment received", requires_receipt=True)  # noqa: F821



class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow an order to move from draft to paid."""

    _template = Lifecycle().state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial().state(OrderStateEntity.PAID).final()

paid = OrderLifecycle("draft").transition("paid")
assert paid.current_status is OrderStateEntity.PAID
assert excluded_from_graph_model(OrderStateEntity)
print("code:", paid.current_state)
print("receipt required:", paid.current_status.requires_receipt)
print("shared declared object:", paid.current_status is OrderStateEntity.PAID)
print("excluded from entity graph:", excluded_from_graph_model(OrderStateEntity))
