"""Apply one allowed transition.

Move an order from draft to paid while keeping the original order unchanged.

Run: uv run python examples/step_22_lifecycle/01_lifecycle.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, value


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Payment received")



class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow a draft order to become paid."""


    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
        .state(OrderStateEntity.PAID).final()
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
assert paid.current_status is OrderStateEntity.PAID
assert order.lifecycle.current_status is OrderStateEntity.DRAFT
print("original:", order.lifecycle.current_state)
print("updated:", updated.lifecycle.current_state)
print("final:", updated.lifecycle.is_final)
print("declared target:", paid.current_status is OrderStateEntity.PAID)
