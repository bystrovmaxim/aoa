"""Apply one allowed transition.

Move an order from draft to paid while keeping the original order unchanged.

Run: uv run python examples/step_22_lifecycle/01_lifecycle.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Allow a draft order to become paid."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")
    PAID = OrderStateEntity(code="paid", display_name="Payment received")

    _template = (
        Lifecycle()
        .state(DRAFT).to(PAID).initial()
        .state(PAID).final()
    )

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity


class OrderCoreEntity(BaseCoreEntity):
    """Hold the current lifecycle value of one order."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Current order state")

# Run the case.
order = OrderCoreEntity(id="ord-1", lifecycle=OrderLifecycle("draft"))
paid = order.lifecycle.transition("paid")
updated = order.model_copy(update={"lifecycle": paid})
assert order.lifecycle.current_state == "draft"
assert updated.lifecycle.current_state == "paid"
assert paid is not order.lifecycle
assert paid.current_status is OrderLifecycle.PAID
assert order.lifecycle.current_status is OrderLifecycle.DRAFT
print("original:", order.lifecycle.current_state)
print("updated:", updated.lifecycle.current_state)
print("final:", updated.lifecycle.is_final)
print("declared target:", paid.current_status is OrderLifecycle.PAID)
