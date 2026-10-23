"""Keep a status object immutable.

Try to rename a status after creating it.

Run: uv run python examples/step_22_lifecycle/11_immutable_status.py
"""

from pydantic import ValidationError

from aoa.action_machine.domain import BaseStateEntity


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""


status = OrderStateEntity(code="paid", display_name="Paid")

# Run the case.
try:
    status.display_name = "Renamed"
except ValidationError as error:
    detail = error.errors()[0]
    print(type(error).__name__ + ": " + str(detail["loc"][0]) + " — " + detail["msg"])
else:
    raise AssertionError("The invalid declaration was accepted")
