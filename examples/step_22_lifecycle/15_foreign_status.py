"""Reject an undeclared transition target.

Reference a status which is not a member of the lifecycle class.

Run: uv run python examples/step_22_lifecycle/15_foreign_status.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

foreign = OrderStateEntity(code="foreign", display_name="Foreign")

# Run the case.
try:
    class BrokenLifecycle(Lifecycle, StateVocabulary):
        """Intentionally reference a status outside this vocabulary."""
        DRAFT = OrderStateEntity(code="draft", display_name="Draft")
        _template = Lifecycle().state(DRAFT).to(foreign).initial()
except TypeError as error:
    assert 'is not a status of this lifecycle' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
