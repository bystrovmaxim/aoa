"""Reject a blank code.

Create a status with an empty or whitespace-only code.

Run: uv run python examples/step_22_lifecycle/09_blank_code.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle, StateVocabulary


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

from pydantic import ValidationError

# Run the case.
try:
    OrderStateEntity(code='  ', display_name="Paid")
except ValidationError as error:
    detail = error.errors()[0]
    print(type(error).__name__ + ": " + str(detail["loc"][0]) + " — " + detail["msg"])
else:
    raise AssertionError("The invalid declaration was accepted")
