"""Reject an unknown current state.

Construct a lifecycle using a code absent from its template.

Run: uv run python examples/step_22_lifecycle/04_unknown_state.py
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

from aoa.action_machine.domain.lifecycle import InvalidStateError

# Run the case.
try:
    OrderLifecycle("missing")
except InvalidStateError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("An unknown state was accepted")
