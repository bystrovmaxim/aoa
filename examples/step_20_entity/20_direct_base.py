"""Refuse an entity that does not choose a kind.

BaseEntity provides shared mechanics. An ordinary domain class must choose a kind base.

Run: uv run python examples/step_20_entity/20_direct_base.py
"""

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError

try:
    class OrderEntity(BaseEntity):
        """Attempt to omit the entity kind."""
except DeclarationStructureError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
