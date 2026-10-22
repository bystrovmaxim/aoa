"""Reach the declared state object through a lifecycle.

Paid describes where an order stands in a process. The lifecycle defines how an order can reach it; the state object supplies its code, label and additional data.

Run: uv run python examples/step_20_entity/08_state.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model


class OrderStateEntity(BaseStateEntity):
    """Describe a possible order state."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is required")


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Allow an order to move from draft to paid."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")
    PAID = OrderStateEntity(code="paid", display_name="Payment received", requires_receipt=True)
    _template = Lifecycle().state(DRAFT).to(PAID).initial().state(PAID).final()

paid = OrderLifecycle("draft").transition("paid")
assert paid.current_status is OrderLifecycle.PAID
assert excluded_from_graph_model(OrderStateEntity)
print("code:", paid.current_state)
print("receipt required:", paid.current_status.requires_receipt)
print("shared declared object:", paid.current_status is OrderLifecycle.PAID)
print("excluded from entity graph:", excluded_from_graph_model(OrderStateEntity))
