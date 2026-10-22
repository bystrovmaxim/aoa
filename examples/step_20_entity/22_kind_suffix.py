"""Refuse a generic Entity suffix.

OrderEntity says nothing about the kind. Descendants of BaseCoreEntity must end in CoreEntity.

Run: uv run python examples/step_20_entity/22_kind_suffix.py
"""

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError

try:
    class OrderEntity(BaseCoreEntity):
        """Attempt to omit Core from the suffix."""
except NamingSuffixError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
