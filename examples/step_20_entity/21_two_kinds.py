"""Refuse two different kinds.

A single instance cannot be both an independent object and its owner-dependent part.

Run: uv run python examples/step_20_entity/21_two_kinds.py
"""

from aoa.action_machine.domain import BaseCoreEntity, BaseDetailEntity
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError

try:
    class OrderCoreEntity(BaseCoreEntity, BaseDetailEntity):
        """Attempt to combine incompatible kinds."""
except DeclarationStructureError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
