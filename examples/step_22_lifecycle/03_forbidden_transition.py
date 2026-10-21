"""Reject a forbidden transition.

Try to return a paid order to draft.

Run: uv run python examples/step_22_lifecycle/03_forbidden_transition.py
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

from aoa.action_machine.domain.lifecycle import InvalidTransitionError

# Run the case.
current = OrderLifecycle("paid")
assert not current.can_transition("draft")
try:
    current.transition("draft")
except InvalidTransitionError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("A final state accepted a transition")
assert current.current_state == "paid"
