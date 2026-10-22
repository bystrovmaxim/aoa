"""Refuse a name that claims a different kind.

The inherited kind is Core, while the proposed name says Detail.

Run: uv run python examples/step_20_entity/23_wrong_kind_suffix.py
"""

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError

try:
    class OrderDetailEntity(BaseCoreEntity):
        """Attempt to name a Core object as a Detail."""
except NamingSuffixError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
