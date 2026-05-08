# packages/aoa-action-machine/src/aoa/action_machine/domain/hydration.py
"""
Entity hydration utilities.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module provides ``build()`` for constructing validated entities from
flat dictionaries, with an optional typed mapper for key translation.
``EntityProxy`` enables IDE-safe field-name mapping without string literals.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    storage row / API payload (dict)
                │
                ├─ mapper is None ───────────────┐
                │                                 ▼
                └─ mapper(proxy, data) -> dict   entity_cls(**mapped_data)
                          │                        │
                          ▼                        ▼
                    EntityProxy[T]            Pydantic validation
                     e.id -> "id"                  │
                          │                        ▼
                          └──────────────>   validated entity instance

═══════════════════════════════════════════════════════════════════════════════
ENTITYPROXY — TYPED FIELD ACCESS
═══════════════════════════════════════════════════════════════════════════════

``EntityProxy[T]`` returns field names as strings and is intended for mapper
functions:

    build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],        # e.id → "id"
        e.amount: r["total"],       # e.amount → "amount"
    })

The IDE sees type ``T`` and suggests real entity fields. Accessing a missing
field raises ``AttributeError``.

═══════════════════════════════════════════════════════════════════════════════
RELATIONS AND DEFAULT_FACTORY
═══════════════════════════════════════════════════════════════════════════════

Relation fields (``AggregateMany``, ``AssociationOne``, etc.) are often
declared with ``default_factory=list`` or ``default=None``. When ``build()``
does not provide a relation value, Pydantic applies that default and may
produce plain runtime values (e.g. ``[]``), not relation container classes.

This is expected: relation containers are annotation-level semantics for
inspector/coordinator metadata, not mandatory runtime wrappers.

═══════════════════════════════════════════════════════════════════════════════
USAGE EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

Direct mapping (dictionary keys match entity fields):

    order = build(
        {"id": "ORD-001", "amount": 100.0, "status": "new"},
        OrderEntity,
    )

Mapping via lambda (dictionary keys differ from fields):

    order = build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],
        e.customer: build(r, CustomerEntity, lambda e2, r2: {
            e2.id: r2["customer_id"],
            e2.name: r2["customer_name"],
        }),
    })

Proxy e is typed — the IDE suggests OrderEntity fields.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from aoa.action_machine.domain.entity import BaseEntity


class EntityProxy[T]:
    """
AI-CORE-BEGIN
    ROLE: Typed field-name provider for mapper functions.
    CONTRACT: Return field name strings only for declared entity fields.
    INVARIANTS: No value lookup, no mutation, no fallback for unknown fields.
    AI-CORE-END
"""

    def __init__(self, cls: type[BaseEntity]) -> None:
        self._cls = cls

    def __getattr__(self, name: str) -> str:
        """
        Returns the field name for mapping.

        Verifies that the requested attribute is a declared field of the model
        (model_fields). If not, raises AttributeError [10].

        Args:
            name: the name of the requested attribute.

        Returns:
            str — the field name (matches name).

        Raises:
            AttributeError: if the field is not declared in the model.
        """
        if name in self._cls.model_fields:
            return name
        raise AttributeError(f"'{self._cls.__name__}' has no field '{name}'")


def build[T](
    data: dict[str, Any],
    entity_cls: type[T],
    mapper: Callable[[EntityProxy[T], dict[str, Any]], dict[str, Any]] | None = None,
) -> T:
    """
    Assembles an entity from a flat dictionary with typed mapping.

    Args:
        data:       a flat dictionary of data from storage.
        entity_cls: the entity class to create.
        mapper:     a mapping function (proxy, data) -> dict of fields.
                    If None — direct mapping (data keys = entity fields).

    Returns:
        T — an entity instance created via Pydantic constructor
        with full validation of types and field requirements.

    Example of direct mapping:
        entity = build({"id": "123", "name": "Test", "value": 42}, TestEntity)

    Example of mapping via lambda:
        entity = build(row, OrderEntity, lambda e, r: {
            e.id: r["order_id"],
            e.amount: r["total"],
        })
    """
    if mapper is None:
        return entity_cls(**data)

    proxy = cast(EntityProxy[T], EntityProxy(cast(type[BaseEntity], entity_cls)))
    mapped = mapper(proxy, data)
    return entity_cls(**mapped)
