"""Reject a blank display_name.

Create a status with an empty or whitespace-only display_name.

Run: uv run python examples/step_22_lifecycle/10_blank_display_name.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

from pydantic import ValidationError

# Run the case.
try:
    OrderStateEntity(code="paid", display_name='')
except ValidationError as error:
    detail = error.errors()[0]
    print(type(error).__name__ + ": " + str(detail["loc"][0]) + " — " + detail["msg"])
else:
    raise AssertionError("The invalid declaration was accepted")
