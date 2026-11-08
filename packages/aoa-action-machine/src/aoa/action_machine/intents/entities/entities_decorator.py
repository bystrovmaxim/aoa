# packages/aoa-action-machine/src/aoa/action_machine/intents/entities/entities_decorator.py
"""
The ``@entities`` decorator — declare the entities of a resource's database.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource **is** a database: ``@entities(*classes)`` lists the entities that lie in
it and that the resource may assemble. It performs three responsibilities:

1. **Target check** — the target must be a ``BaseResource`` subclass. Every resource
   kind (storage, gateway, controller) may declare its entities.
2. **Argument check** — every argument must be a class that carries ``_entity_info``,
   that is, a class declared with ``@entity``. A class repeated in one declaration is
   refused, because a database lists each of its entities once. An empty list is
   allowed: a resource that never returns an entity declares none.
3. **Scratch metadata** — writes ``_entities_info`` on the class as an ordered tuple,
   preserving the order the author wrote.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ``@meta``
═══════════════════════════════════════════════════════════════════════════════

``@meta`` describes a host; ``@entities`` says what a database holds. The two are
separate intents with separate scratch keys:

    @meta     → MetaIntent     → ``_meta_info``
    @entities → EntitiesIntent → ``_entities_info``

A resource's ``@meta`` takes no ``domain``: a database is shared by domains, and its
domains are the domains of the entities it lists.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    *classes : type
        Zero or more ``@entity`` classes. Each is listed once; order is kept.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entities(OrderCoreEntity, OrderLineDetailEntity)
        │
        ▼  checks each argument is an @entity and appears once, writes scratch on cls
    _entities_info = (OrderCoreEntity, OrderLineDetailEntity)
        │
        ▼  EntitiesIntentResolver, the return check and, from protocol 2.0, the graph builder
    resource node ──resource_entity──► each listed entity (protocol 2.0)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.entities import entities
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseStorage

    @meta(description="The shop database")
    @entities(OrderCoreEntity, OrderLineDetailEntity, CustomerCoreEntity)
    class ShopDatabaseStorage(BaseStorage):
        pass
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.entities_decorator_error import EntitiesDecoratorError
from aoa.action_machine.intents.entity.entity_intent import entity_info_is_set

__all__ = ("EntitiesDecoratorError", "entities", "entities_info_tuple")


def validate_entities_target(cls: Any) -> None:
    """
    Invariant: the decorator target is a ``BaseResource`` subclass.

    The import sits inside the function because ``BaseResource`` itself imports the
    intent marker of this package; importing the resource root here at module scope
    would close that cycle.

    Raises:
        EntitiesDecoratorError: target is not a class, or not a ``BaseResource`` subclass.
    """
    # Imported here: the resources package imports this intent's marker.
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

    if not isinstance(cls, type):
        raise EntitiesDecoratorError(f"@entities applies only to a class. Got {type(cls).__name__}: {cls!r}.")
    if not issubclass(cls, BaseResource):
        raise EntitiesDecoratorError(
            f"@entities applies only to a resource (a BaseResource subclass); {cls.__name__!r} is not one. "
            "A resource is a database, and it lists the entities that lie in it."
        )


def validate_entities_arguments(classes: tuple[Any, ...]) -> None:
    """
    Invariant: every argument is an ``@entity`` class, and no class appears twice.

    Raises:
        EntitiesDecoratorError: a non-class or non-``@entity`` argument, or a repeated class.
    """
    seen: set[type] = set()
    for cls in classes:
        if not isinstance(cls, type):
            raise EntitiesDecoratorError(
                f"@entities: every argument must be a class decorated with @entity. "
                f"Got {type(cls).__name__}: {cls!r}."
            )
        if not entity_info_is_set(cls):
            raise EntitiesDecoratorError(
                f"@entities: {cls.__name__!r} is not an @entity. "
                "Every @entities argument must be a class decorated with @entity(description=..., domain=...)."
            )
        if cls in seen:
            raise EntitiesDecoratorError(
                f"@entities: class {cls.__name__!r} is listed twice. A database lists each of its entities once."
            )
        seen.add(cls)


def entities_info_tuple(host_cls: type) -> tuple[type[Any], ...]:
    """
    Return the ``_entities_info`` tuple written by ``@entities`` on ``host_cls``, or ``()``.

    Only the class's own declaration counts: a subclass resource never inherits its
    parent's list, because each resource states what its own database holds.
    """
    raw = host_cls.__dict__.get("_entities_info")
    return raw if isinstance(raw, tuple) else ()


def entities(*classes: type[Any]) -> Callable[[type], type]:
    """
    Class decorator: declare the entities that lie in a resource's database.

    Writes ``_entities_info`` on the target class as an ordered tuple. Resolvers, the
    return check and the graph builder read it.

    Args:
        *classes:
            Zero or more ``@entity`` classes. An empty list is allowed; a repeated
            class is refused.

    Returns:
        A decorator that mutates the class (adds ``_entities_info``) and returns it.

    Raises:
        EntitiesDecoratorError:
            The target is not a ``BaseResource`` subclass, an argument is not an
            ``@entity`` class, or one class is listed twice.

    Example:
        @meta(description="The shop database")
        @entities(OrderCoreEntity, CustomerCoreEntity)
        class ShopDatabaseStorage(BaseStorage):
            pass

    AI-CORE-BEGIN
    PURPOSE: Import-time declaration point for the entities a resource's database holds.
    INPUT/OUTPUT: Accepts zero or more ``@entity`` classes and returns a class decorator.
    SIDE EFFECTS: Writes ``cls._entities_info`` as an ordered tuple.
    FAILURES: Raises ``EntitiesDecoratorError`` naming the refused target, argument or repeat.
    ORDER: Runs at class definition time, before the model build.
    AI-CORE-END
    """
    validate_entities_arguments(classes)

    def decorator(cls: type) -> type:
        validate_entities_target(cls)
        cls._entities_info = tuple(classes)  # type: ignore[attr-defined]
        return cls

    return decorator
