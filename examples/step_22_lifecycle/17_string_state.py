"""Reject a string in the template.

Use the removed string form of state().

Run: uv run python examples/step_22_lifecycle/17_string_state.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

# Run the case.
try:
    Lifecycle().state("draft")
except TypeError as error:
    assert 'State must be a state entity' in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
