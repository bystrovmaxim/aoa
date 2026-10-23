"""Read the description of the current state.

Read the label and a domain field directly from the selected status object.

Run: uv run python examples/step_22_lifecycle/02_lifecycle_axis.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, value


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Payment received", requires_receipt=True)



class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Collect statuses and declare their allowed transition."""

    _template = Lifecycle().state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial().state(OrderStateEntity.PAID).final()

# Run the case.
row = {"id": "ord-1", "status": "paid"}
current = OrderLifecycle(row["status"])
status = current.current_status
assert status is OrderStateEntity.PAID
assert current.current_state == status.code
assert status.requires_receipt is True
assert OrderStateEntity.entity_type is OrderStateEntity
assert tuple(OrderStateEntity.by_code(code) for code in OrderStateEntity.codes()) == OrderStateEntity.members
print("codes:", OrderStateEntity.codes())
print("current code:", current.current_state)
print("label:", status.display_name)
print("requires receipt:", status.requires_receipt)
print("declared object:", status is OrderStateEntity.PAID)
