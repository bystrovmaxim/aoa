"""Reject duplicate codes on one state type.

Declare two different labels under the same code.

Run: uv run python examples/step_22_lifecycle/12_duplicate_code.py
"""

from aoa.action_machine.domain import BaseStateEntity, value


# Run the case.
try:
    class OrderStateEntity(BaseStateEntity):
        """Intentionally declare an ambiguous code."""

        A = value(code="paid", display_name="Paid")
        B = value(code="paid", display_name="Settled")
except ValueError as error:
    assert "duplicate status code" in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
