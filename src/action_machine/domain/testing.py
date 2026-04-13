# src/action_machine/domain/testing.py
"""
Test helpers for constructing domain entities quickly.

═══════════════════════════════════════════════════════════════════════════════
make() — ENTITY FACTORY WITH SIMPLE AUTO-DEFAULTS
═══════════════════════════════════════════════════════════════════════════════

`make()` builds an entity instance with **heuristic defaults** per field type,
then applies your overrides. It is meant for **tests**, examples, and
prototyping — **not** for production persistence logic.

Example:

    order = make(OrderEntity, amount=100.0)
    # `id` and other string fields may become "test_<field_name>", etc.

The implementation is intentionally small and extensible: add more branches
when new primitive patterns appear in your test entities.
"""

from __future__ import annotations

from typing import Any, cast

from action_machine.domain.entity import BaseEntity
from action_machine.domain.lifecycle import Lifecycle


def make[T](entity_cls: type[T], **overrides: Any) -> T:
    """
    Create a test entity with auto-generated defaults merged with ``overrides``.

    Args:
        entity_cls:
            Concrete `BaseEntity` subclass.
        **overrides:
            Field values that replace or supplement generated defaults.

    Returns:
        A validated entity instance (`entity_cls(...)`).

    Note:
        Relation containers and complex nested types are not fully handled;
        pass them explicitly via ``overrides`` when needed.
    """
    defaults: dict[str, Any] = {}
    model_cls = cast(type[BaseEntity], entity_cls)
    for name, field in model_cls.model_fields.items():
        if name in overrides:
            continue
        ann = field.annotation
        if ann is str:
            defaults[name] = f"test_{name}"
        elif ann is int:
            defaults[name] = 1
        elif ann is float:
            defaults[name] = 1.0
        elif ann is Lifecycle:
            getter = f"get_{name}"
            if hasattr(entity_cls, getter):
                try:
                    defaults[name] = getattr(entity_cls, getter)()
                except Exception:
                    pass
        # Extend with more types as your test model grows.

    data = {**defaults, **overrides}
    return entity_cls(**data)
