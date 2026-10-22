"""Inherit an existing status type.

Create a subtype without declaring replacement statuses, and an axis that narrows the type.

Run: uv run python examples/step_22_lifecycle/07_inherited_vocabulary.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    DRAFT = OrderStateEntity(code="draft", display_name="Draft")  # noqa: F821
    PAID = OrderStateEntity(code="paid", display_name="Payment received")  # noqa: F821


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow a draft order to become paid."""

    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
        .state(OrderStateEntity.PAID).final()
    )


class SpecialOrderStateEntity(OrderStateEntity):
    """Reuse the parent statuses."""


class SpecialOrderLifecycle(OrderLifecycle, Lifecycle[SpecialOrderStateEntity]):
    """Reuse the parent template with a narrowed state type."""


# Run the case.
assert SpecialOrderStateEntity.members == OrderStateEntity.members
assert SpecialOrderStateEntity.by_code("paid") is OrderStateEntity.PAID
print(SpecialOrderStateEntity.codes())
print(SpecialOrderLifecycle("draft").transition("paid").current_state)
