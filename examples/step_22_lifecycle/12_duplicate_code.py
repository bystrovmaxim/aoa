"""Reject duplicate codes in one vocabulary.

Declare two different labels under the same code.

Run: uv run python examples/step_22_lifecycle/12_duplicate_code.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

# Run the case.
try:
    class DuplicateLifecycle(Lifecycle, StateVocabulary):
        """Intentionally declare an ambiguous code."""
        A = OrderStateEntity(code="paid", display_name="Paid")
        B = OrderStateEntity(code="paid", display_name="Settled")
        _template = Lifecycle().state(A).initial()
except ValueError as error:
    assert 'duplicate status code' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
