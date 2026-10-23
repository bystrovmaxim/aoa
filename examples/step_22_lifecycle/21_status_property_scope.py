"""Distinguish status properties from dictionary properties.

The dictionary annotation restriction does not apply to lifecycle statuses.
Run: uv run python examples/step_22_lifecycle/21_status_property_scope.py
"""

from aoa.action_machine.domain import BaseStateEntity, value


class OrderStateEntity(BaseStateEntity):
    """Describe a status using the existing state property contract."""
    labels: list[str]
    DRAFT = value(code="draft", display_name="Draft", labels=["new"])


def main() -> None:
    """Run this one learning experiment."""
    print("Status accepted:", OrderStateEntity.DRAFT.labels)
    print("Property type:", type(OrderStateEntity.DRAFT.labels).__name__)
    assert OrderStateEntity.by_code("draft") is OrderStateEntity.DRAFT


if __name__ == "__main__":
    main()
