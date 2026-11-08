# packages/aoa-action-machine/src/aoa/action_machine/intents/entity/entity_decorator.py
"""
The ``@entity`` decorator — declare a class as an entity and name its domain.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@entity`` is the declaration entry point for entities in the domain model.
It performs three responsibilities:

1. **Target check** — the target must be a class (``type``).
2. **Domain check** — ``domain`` must be a ``BaseDomain`` subclass. An entity
   names its own domain; it names no resource, because a resource is a database
   that may hold the entities of several domains.
3. **Scratch metadata** — writes ``_entity_info`` on the class with keys
   ``"description"`` and ``"domain"``. ``EntityIntentResolver`` and the entity
   validators read it when the model and its graph are built.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ``@meta``
═══════════════════════════════════════════════════════════════════════════════

Actions and resources use ``@meta``. Entities use ``@entity``. Different
intent markers, different scratch keys:

    @meta   → MetaIntent    → ``_meta_info``
    @entity → EntityIntent  → ``_entity_info``

An entity names a domain of its own, the way an action's ``@meta`` does; a
resource names no domain at all.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Required human-readable description (non-empty after ``strip()``).
    domain : type[BaseDomain]
        Required keyword-only. The one ``BaseDomain`` subclass the entity
        belongs to.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entity(description="Customer order", domain=ShopDomain)
        │
        ▼  checks the domain, writes scratch on cls
    _entity_info = {"description": ..., "domain": ShopDomain}
        │
        ▼  EntityIntentResolver, entity validators, EntityGraphNode
    entity node ──domain──► ShopDomain   (read from the entity's own declaration)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from aoa.action_machine.domain import BaseCoreEntity, BaseDomain
    from aoa.action_machine.intents.entity.entity_decorator import entity

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop"

    @entity(description="Customer order", domain=ShopDomain)
    class OrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.exceptions import EntityDecoratorError

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
            '@entity(description="Customer order", domain=ShopDomain).'
        )


def validate_entity_domain(domain: Any) -> None:
    """
    Invariant: ``domain`` is a ``BaseDomain`` subclass.

    Mirrors the checks ``@meta`` applies to its own ``domain`` argument.

    Raises:
        EntityDecoratorError: no domain, not a class, or not a ``BaseDomain`` subclass.
    """
    if domain is None:
        raise EntityDecoratorError(
            "@entity: domain is required (keyword-only). " "Pass a BaseDomain subclass, e.g. domain=OrdersDomain."
        )
    if not isinstance(domain, type):
        raise EntityDecoratorError(
            f"@entity: domain must be a BaseDomain subclass, got {type(domain).__name__}: {domain!r}."
        )
    if not issubclass(domain, BaseDomain):
        raise EntityDecoratorError(f"@entity: domain must be a BaseDomain subclass; {domain.__name__!r} is not.")


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
    domain: type[BaseDomain],
) -> Callable[[type], type]:
    """
    Class decorator: declare an entity and the domain it belongs to.

    Writes ``_entity_info`` on the target class. Resolvers and validators read it
    when the model and its graph are built.

    Args:
        description:
            Non-empty string describing the entity in business language.
        domain:
            The one ``BaseDomain`` subclass the entity belongs to. Required:
            ``None`` is refused.

    Returns:
        A decorator that mutates the class (adds ``_entity_info``) and returns it.

    Raises:
        EntityDecoratorError:
            Invalid ``description`` or ``domain``, or target is not a class.

    Example:
        @entity(description="Customer order", domain=ShopDomain)
        class OrderCoreEntity(BaseCoreEntity):
            id: str = Field(description="Order id")

    AI-CORE-BEGIN
    PURPOSE: Import-time declaration point for entity metadata and the domain the entity names.
    INPUT/OUTPUT: Accepts ``description`` and one ``domain`` and returns a class decorator.
    SIDE EFFECTS: Writes ``cls._entity_info`` with ``description`` and ``domain``.
    FAILURES: Raises ``EntityDecoratorError`` naming the refused description or domain.
    ORDER: Runs at class definition time, before the model build.
    AI-CORE-END
    """
    validate_entity_description(description)
    validate_entity_domain(domain)

    def decorator(cls: type) -> type:
        validate_entity_decorator_target(cls)
        # A kind that must declare its values may refuse a concrete class; the class
        # itself knows the rule, so the decorator only asks.
        require = getattr(cls, "_require_declared_values", None)
        if require is not None:
            require()
        cls._entity_info = {  # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }
        return cls

    return decorator
