"""Reject mixed status types.

Put two status classes in one vocabulary.

Run: uv run python examples/step_22_lifecycle/13_mixed_types.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""


class PaymentStateEntity(BaseStateEntity):
    """Describe a different kind of status."""

# Run the case.
try:
    class MixedLifecycle(Lifecycle, StateVocabulary):
        """Intentionally mix two status types."""
        A = OrderStateEntity(code="a", display_name="A")
        B = PaymentStateEntity(code="b", display_name="B")
        _template = Lifecycle().state(A).to(B).initial().state(B).final()
except TypeError as error:
    assert 'different types' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
