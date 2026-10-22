"""Refuse construction of a kind base.

A marker describes a category of model classes. An application constructs a concrete descendant.

Run: uv run python examples/step_20_entity/25_marker_instance.py
"""

from aoa.action_machine.domain import BaseCoreEntity

try:
    BaseCoreEntity()
except TypeError as exc:
    print(type(exc).__name__ + ": " + str(exc))
else:
    raise AssertionError("The invalid declaration must be refused")
