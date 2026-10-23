"""Reject a status of another type.

Reference a status object that is not a declared member of the axis's state type.

Run: uv run python examples/step_22_lifecycle/15_foreign_status.py
"""

from aoa.action_machine.domain import BaseStateEntity, ForeignStateError, Lifecycle, value


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    DRAFT = value(code="draft", display_name="Draft")


class OtherStateEntity(BaseStateEntity):
    """A second state type, not the one the axis names."""

    FOREIGN = value(code="foreign", display_name="Foreign")


# Run the case.
try:
    class BrokenLifecycle(Lifecycle[OrderStateEntity]):
        """Intentionally reference a status outside the axis's type."""

        _template = Lifecycle().state(OrderStateEntity.DRAFT).to(OtherStateEntity.FOREIGN).initial()
except ForeignStateError as error:
    assert "is not a declared status" in str(error)
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
