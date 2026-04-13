# src/action_machine/domain/hydration.py
"""
Entity hydration utilities.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module provides a build() function for assembling frozen entities
from flat data dictionaries with typed mapping via lambda.

build() is the primary way to create entities from data obtained from
storage (database, API, files). Mapping through EntityProxy provides
autocomplete for fields in the IDE.

═══════════════════════════════════════════════════════════════════════════════
ENTITYPROXY — TYPED FIELD ACCESS
═══════════════════════════════════════════════════════════════════════════════

EntityProxy[T] is a proxy object that returns entity field names as strings.
It's used inside the build() mapper for typed field access:

    build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],        # e.id → "id"
        e.amount: r["total"],       # e.amount → "amount"
    })

The IDE sees type T and suggests fields. Accessing a non-existent field
raises AttributeError.

═══════════════════════════════════════════════════════════════════════════════
RELATIONS AND DEFAULT_FACTORY
═══════════════════════════════════════════════════════════════════════════════

Relation fields (AggregateMany, AssociationOne, etc.) are declared with
default_factory=list or default=None in Pydantic Field [5]. When creating
an entity via build() without explicitly specifying a relation value, Pydantic
uses default_factory and creates a plain list [], not a container instance
(AggregateMany, etc.).

This is expected behavior: relation containers are type annotations for
coordinator metadata (ArchiMate, OCEL), not runtime wrappers [5].
The coordinator reads the annotation via get_origin() and extracts
ownership_type and cardinality.

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

from action_machine.domain.entity import BaseEntity


class EntityProxy[T]:
    """
    Proxy for typed field access to entities in build().

    When accessing an attribute, returns the field name as a string.
    Used as the first argument to the mapper in build().

    Attributes:
        _cls: the entity class whose fields are being proxied.

    Example:
        proxy = EntityProxy(OrderEntity)
        proxy.id      # → "id"
        proxy.amount  # → "amount"
        proxy.foo     # → AttributeError
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
