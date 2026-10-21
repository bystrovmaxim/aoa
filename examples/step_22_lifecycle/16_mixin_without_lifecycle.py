"""Require Lifecycle beside StateVocabulary.

Use the vocabulary mixin on an unrelated class.

Run: uv run python examples/step_22_lifecycle/16_mixin_without_lifecycle.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

# Run the case.
try:
    class NotALifecycle(StateVocabulary):
        """Intentionally omit the Lifecycle base class."""
except TypeError as error:
    assert 'Lifecycle subclass' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
