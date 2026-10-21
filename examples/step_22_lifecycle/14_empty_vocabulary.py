"""Reject a new template without status attributes.

Declare a new template but no status members on its class.

Run: uv run python examples/step_22_lifecycle/14_empty_vocabulary.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

# Run the case.
try:
    class EmptyLifecycle(Lifecycle, StateVocabulary):
        """Intentionally omit the status attributes."""
        _template = Lifecycle()
except ValueError as error:
    assert 'at least one status' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
