# src/action_machine/intents/domain/entity_decorator.py
"""
The ``@entity`` decorator — declare a class as a domain entity.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@entity`` is the declaration entry point for entities in the domain model.
It performs three responsibilities:

1. **Intent check** — the target class must inherit ``EntityIntent``
   (``BaseEntity`` does this for you). Otherwise → ``EntityDecoratorError``.

2. **Scratch metadata** — writes ``_entity_info`` on the class with keys
   ``"description"`` and ``"domain"``. This is the **grammar trace** decorators
   leave for tools and for ``EntityIntentInspector``.

3. **Discovery** — ``EntityIntentInspector`` finds decorated classes during
   ``GraphCoordinator.build()`` and emits facet payloads / snapshots. The
   decorator itself never touches the coordinator.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ``@meta``
═══════════════════════════════════════════════════════════════════════════════

Actions and resource managers use ``@meta``. Entities use ``@entity``. Different
intent markers, different scratch keys:

    @meta   → ActionMetaIntent or ResourceMetaIntent  → ``_meta_info``
    @entity → EntityIntent                             → ``_entity_info``

Reasons:
- Entities belong to the **domain** package; actions belong to **core**.
  Mixing intent markers would couple layers unnecessarily.
- Entities do not use aspects, roles, or dependency wiring — they should not
  pull in action-centric validation paths.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Required human-readable description (non-empty after ``strip()``).
        Feeds diagram-oriented and OCEL-style exports and generated docs. Whitespace-only
        strings → ``ValueError`` / ``EntityDecoratorError`` from validators.

    domain : type[BaseDomain] | None
        Optional bounded-context marker. Must be a ``BaseDomain`` subclass when
        set. ``None`` means no domain edge in the graph (policy depends on your
        invariants).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to **classes**, not functions or methods.
- Target must inherit ``EntityIntent`` (typically via ``BaseEntity``).
- ``description`` — non-empty ``str``.
- ``domain`` — ``None`` or ``BaseDomain`` subclass.
- Decorator order relative to other class decorators is otherwise unconstrained.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Customer order", domain=ShopDomain)
        │
        ▼  writes scratch on cls
    _entity_info = {"description": ..., "domain": ShopDomain}
        │
        ▼  EntityIntentInspector at GraphCoordinator.build()
    Reads _entity_info + pydantic model_fields → FacetVertex / snapshot
        │
        ▼
    Facet graph: ``entity`` node, optional ``belongs_to`` domain edge, …

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from action_machine.domain import BaseEntity, BaseDomain
    from action_machine.intents.domain.entity_decorator import entity

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop"

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        id: str = Field(description="Order id")
        amount: float = Field(description="Order total", ge=0)
        status: str = Field(description="Workflow status")

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

    EntityDecoratorError — wrong target type, missing ``EntityIntent``, bad
                           ``description`` / ``domain``.

The decorator validates declaration metadata only. Graph-level consistency is
validated later during coordinator ``build()`` by inspectors.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Domain entity declaration decorator.
CONTRACT: Validate declaration metadata and write ``_entity_info`` scratch on class.
INVARIANTS: Target must satisfy ``EntityIntent`` contract; metadata is import-time validated.
FLOW: decorator args validation -> class target validation -> scratch write -> inspector consumption at build.
FAILURES: ``EntityDecoratorError`` for invalid arguments or invalid target classes.
EXTENSION POINTS: Applications specialize domain modeling by combining ``@entity`` with custom BaseDomain hierarchies.
AI-CORE-END
"""

from __future__ import annotations

from collections.abc import Callable

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.domain.entity_intent import (
    validate_entity_decorator_target,
    validate_entity_description,
    validate_entity_domain,
)
from action_machine.domain.exceptions import EntityDecoratorError

__all__ = ("EntityDecoratorError", "entity")


def entity(
    description: str,
    *,
    domain: type[BaseDomain] | None = None,
) -> Callable[[type], type]:
    """
    Class decorator: declare a domain entity.

    Writes ``_entity_info`` on the target class. ``EntityIntentInspector``
    reads it when the coordinator graph is built.

    Args:
        description:
            Non-empty string describing the entity in business language.
        domain:
            Optional ``BaseDomain`` subclass, or ``None``.

    Returns:
        A decorator that mutates the class (adds ``_entity_info``) and returns it.

    Raises:
        EntityDecoratorError:
            Invalid ``description`` / ``domain``, or target is not an
            ``EntityIntent`` subclass.

    Example:
        @entity(description="Customer order", domain=ShopDomain)
        class OrderEntity(BaseEntity):
            id: str = Field(description="Order id")

    AI-CORE-BEGIN
    PURPOSE: Import-time declaration point for entity metadata.
    INPUT/OUTPUT: Accepts validated ``description``/``domain`` and returns a class decorator.
    SIDE EFFECTS: Writes ``cls._entity_info`` used later by ``EntityIntentInspector``.
    FAILURES: Raises ``EntityDecoratorError`` via target/argument validators.
    ORDER: Runs at class definition time before coordinator graph build.
    AI-CORE-END
    """
    validate_entity_description(description)
    validate_entity_domain(domain)

    def decorator(cls: type) -> type:
        validate_entity_decorator_target(cls)

        cls._entity_info = {  # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }

        return cls

    return decorator
