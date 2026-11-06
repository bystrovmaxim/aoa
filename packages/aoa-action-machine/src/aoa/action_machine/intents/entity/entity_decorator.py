# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_decorator.py
"""
The ``@entity`` decorator — declare a class as an entity stored by one resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@entity`` is the declaration entry point for entities in the domain model.
It performs three responsibilities:

1. **Target check** — the target must be a class (``type``).
2. **Resource check** — ``resource`` must be exactly one concrete ``BaseResource``
   subclass that declares its domain with ``@meta``. An entity is a row stored
   somewhere; the resource is where, and the resource's domain is the entity's domain.
3. **Scratch metadata** — writes ``_entity_info`` on the class with keys
   ``"description"`` and ``"resource"``. ``EntityIntentResolver`` and the entity
   validators read it when the model and its graph are built.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ``@meta``
═══════════════════════════════════════════════════════════════════════════════

Actions and resources use ``@meta``. Entities use ``@entity``. Different
intent markers, different scratch keys:

    @meta   → MetaIntent    → ``_meta_info``
    @entity → EntityIntent  → ``_entity_info``

An entity does not name a domain of its own: it takes the domain of the
resource that stores it, so there is one source for it and nothing to compare.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Required human-readable description (non-empty after ``strip()``).
    resource : type[BaseResource]
        Required. One concrete resource class — a storage, a gateway or a
        controller — carrying ``@meta(domain=...)``. A kind base class excluded
        from the graph model (``BaseStorage`` and its siblings) is refused: its
        node never exists, so the entity could not point at it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entity(description="Customer order", resource=ShopDatabase)
        │
        ▼  checks the resource, writes scratch on cls
    _entity_info = {"description": ..., "resource": ShopDatabase}
        │
        ▼  EntityIntentResolver, entity validators, EntityGraphNode
    entity node ──entity_resource──► ShopDatabase ──domain──► ShopDomain
    entity node ──domain──► ShopDomain   (read from ShopDatabase's @meta)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.intents.entity.entity_decorator import entity
    from aoa.action_machine.intents.meta import meta
    from aoa.action_machine.resources import BaseStorage, InMemoryDataSource

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop"

    @meta(description="Where the shop's rows live")
    class ShopDataSource(InMemoryDataSource):
        \"\"\"The store the shop database works with.\"\"\"

    @meta(description="Stores the shop model", domain=ShopDomain)
    class ShopDatabase(BaseStorage[ShopDataSource]):
        \"\"\"Hold the shop's entities.\"\"\"

    @entity(description="Customer order", resource=ShopDatabase)
    class OrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

# The module, not the name: ``base_resource`` reaches this module through ``@meta`` while it is
# still loading, and only a module reference resolves its class at call time.
import aoa.action_machine.resources.base_resource as base_resource_module
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityDecoratorError
from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model

if TYPE_CHECKING:
    from aoa.action_machine.resources.base_resource import BaseResource

__all__ = ("EntityDecoratorError", "entity", "entity_info_dict")


def validate_entity_description(description: Any) -> None:
    """
    Invariant: ``description`` is a non-empty ``str`` (after strip).

    Raises:
        EntityDecoratorError: not a string, or blank after strip.
    """
    if not isinstance(description, str):
        raise EntityDecoratorError(
            f"@entity: parameter 'description' must be str, " f"got {type(description).__name__}: {description!r}."
        )
    if not description.strip():
        raise EntityDecoratorError(
            "@entity: description cannot be empty. "
            "Provide a non-empty entity description, e.g. "
            '@entity(description="Customer order", resource=ShopDatabase).'
        )


def _given_name(value: Any) -> str:
    """Name a value the way a refusal shows it: a class by its name, anything else by its repr."""
    return value.__name__ if isinstance(value, type) else repr(value)


def validate_entity_resource(cls: type, resource: Any) -> None:
    """
    Invariant: ``resource`` is one concrete ``BaseResource`` subclass with a ``@meta`` domain.

    Raises:
        EntityDecoratorError: no resource, several, not a resource class, a kind base
            excluded from the graph model, or a resource that declares no domain.
    """
    name = cls.__name__
    if resource is None:
        raise EntityDecoratorError(f"{name} — @entity needs resource=: an entity is stored by a resource.")
    if isinstance(resource, (tuple, list, set, frozenset)):
        given = ", ".join(_given_name(item) for item in resource)
        raise EntityDecoratorError(f"{name} — @entity takes one resource, got {len(resource)}: {given}.")
    if not isinstance(resource, type) or not issubclass(resource, base_resource_module.BaseResource):
        raise EntityDecoratorError(
            f"{name} — @entity resource= must be a BaseResource subclass, got {_given_name(resource)}."
        )
    if excluded_from_graph_model(resource):
        raise EntityDecoratorError(
            f"{name} — @entity resource= must be a concrete resource, got {resource.__name__}, "
            f"which is excluded from the graph model."
        )
    meta_info = getattr(resource, "_meta_info", None)
    domain = meta_info.get("domain") if isinstance(meta_info, dict) else None
    if not isinstance(domain, type) or not issubclass(domain, BaseDomain):
        raise EntityDecoratorError(
            f"{name} — @entity resource= {resource.__name__} declares no domain: decorate it with @meta(domain=...)."
        )


def validate_entity_decorator_target(cls: Any) -> None:
    """
    Invariant: decorator target is a ``type``.

    Raises:
        EntityDecoratorError: not a class.
    """
    if not isinstance(cls, type):
        raise EntityDecoratorError(f"@entity applies only to a class. " f"Got {type(cls).__name__}: {cls!r}.")


def entity_info_dict(host_cls: type) -> dict[str, Any]:
    """
    Return ``_entity_info`` written by ``@entity`` on ``host_cls``, or ``{}`` when absent or not a mapping.

    Mirrors :meth:`aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.meta_info_dict`
    for the ``_meta_info`` / ``@meta`` grammar.
    """
    raw = getattr(host_cls, "_entity_info", None)
    return raw if isinstance(raw, dict) else {}


def entity(
    description: str,
    *,
    resource: type[BaseResource] | None = None,
) -> Callable[[type], type]:
    """
    Class decorator: declare an entity stored by one resource.

    Writes ``_entity_info`` on the target class. Resolvers and validators read it
    when the model and its graph are built.

    Args:
        description:
            Non-empty string describing the entity in business language.
        resource:
            The one concrete ``BaseResource`` subclass that stores the entity; it
            must carry ``@meta(domain=...)``. Required: ``None`` is refused.

    Returns:
        A decorator that mutates the class (adds ``_entity_info``) and returns it.

    Raises:
        EntityDecoratorError:
            Invalid ``description`` or ``resource``, or target is not a class.

    Example:
        @entity(description="Customer order", resource=ShopDatabase)
        class OrderCoreEntity(BaseCoreEntity):
            id: str = Field(description="Order id")

    AI-CORE-BEGIN
    PURPOSE: Import-time declaration point for entity metadata and the resource that stores the entity.
    INPUT/OUTPUT: Accepts ``description`` and one ``resource`` and returns a class decorator.
    SIDE EFFECTS: Writes ``cls._entity_info`` with ``description`` and ``resource``.
    FAILURES: Raises ``EntityDecoratorError`` naming the entity for every refused resource.
    ORDER: Runs at class definition time, after the resource's ``@meta`` and before the model build.
    AI-CORE-END
    """
    validate_entity_description(description)

    def decorator(cls: type) -> type:
        validate_entity_decorator_target(cls)
        validate_entity_resource(cls, resource)
        # A kind that must declare its values may refuse a concrete class; the class
        # itself knows the rule, so the decorator only asks.
        require = getattr(cls, "_require_declared_values", None)
        if require is not None:
            require()
        cls._entity_info = {  # type: ignore[attr-defined]
            "description": description,
            "resource": resource,
        }
        return cls

    return decorator
