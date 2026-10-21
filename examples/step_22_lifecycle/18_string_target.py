"""Reject a string transition target in the template.

Pass a code to the template builder instead of a status object.

Run: uv run python examples/step_22_lifecycle/18_string_target.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

draft = OrderStateEntity(code="draft", display_name="Draft")

# Run the case.
try:
    Lifecycle().state(draft).to("paid")
except TypeError as error:
    assert 'Transition target must be a state entity' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
