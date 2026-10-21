"""Inherit an existing vocabulary.

Create a subclass without declaring replacement statuses.

Run: uv run python examples/step_22_lifecycle/07_inherited_vocabulary.py
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


class SpecialOrderLifecycle(OrderLifecycle):
    """Reuse the parent statuses and template."""

# Run the case.
assert SpecialOrderLifecycle.members == OrderLifecycle.members
assert SpecialOrderLifecycle.by_code("paid") is OrderLifecycle.PAID
print(SpecialOrderLifecycle.codes())
print(SpecialOrderLifecycle("draft").transition("paid").current_state)
