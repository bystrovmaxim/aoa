# src/action_machine/domain/testing.py
"""
Test helpers for constructing domain entities quickly.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``make()`` builds an entity instance with heuristic defaults per field type and
then applies explicit overrides. It is intended for tests, examples, and quick
prototyping, not for production persistence logic.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    entity_cls.model_fields
            │
            ▼
    infer lightweight defaults
      (str/int/float/Lifecycle getter)
            │
            ▼
    merge with **overrides
            │
            ▼
    entity_cls(**data)  -> validated test entity instance

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Overrides always win over inferred defaults.
- Construction still goes through ``entity_cls(...)`` and uses normal validation.
- Complex relation/nested defaults are intentionally minimal and caller-supplied.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Example:

    order = make(OrderEntity, amount=100.0)
    # `id` and other string fields may become "test_<field_name>", etc.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This helper intentionally covers only a small set of primitive defaults.
- Lifecycle fallback via ``get_<field>()`` is best-effort and silently ignored on errors.
- Not suitable for production object assembly policies.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Lightweight test entity factory helper.
CONTRACT: Generate minimal defaults and construct validated entities with override precedence.
INVARIANTS: No persistence/I-O; always delegates final validation to entity constructor.
FLOW: inspect model fields -> infer defaults -> merge overrides -> instantiate entity.
FAILURES: Validation errors are surfaced by entity constructor; lifecycle getter errors are ignored.
EXTENSION POINTS: Add new type branches as test model primitives evolve.
AI-CORE-END
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
