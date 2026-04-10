# src/action_machine/domain/entity_decorator.py
"""
The ``@entity`` decorator — declare a class as a domain entity.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@entity`` is the single entry point for declaring an **entity** in the
ActionMachine domain model. It does three things:

1. **Gate-host check** — the target class must inherit ``EntityGateHost``
   (``BaseEntity`` does this for you). Otherwise → ``EntityDecoratorError``.

2. **Scratch metadata** — writes ``_entity_info`` on the class with keys
   ``"description"`` and ``"domain"``. This is the **grammar trace** decorators
   leave for tools and for ``EntityGateHostInspector``.

3. **Discovery** — ``EntityGateHostInspector`` finds decorated classes during
   ``GateCoordinator.build()`` and emits facet payloads / snapshots. The
   decorator itself never touches the coordinator.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ``@meta``
═══════════════════════════════════════════════════════════════════════════════

Actions and resource managers use ``@meta``. Entities use ``@entity``. Different
gate hosts, different scratch keys:

    @meta   → ActionMetaGateHost or ResourceMetaGateHost  → ``_meta_info``
    @entity → EntityGateHost                             → ``_entity_info``

Reasons:
- Entities belong to the **domain** package; actions belong to **core**.
  Mixing gate hosts would couple layers unnecessarily.
- Entities do not use aspects, roles, or dependency wiring — they should not
  pull in action-centric validation paths.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Required human-readable description (non-empty after ``strip()``).
        Feeds ArchiMate / OCEL style exports and generated docs. Whitespace-only
        strings → ``ValueError`` / ``EntityDecoratorError`` from validators.

    domain : type[BaseDomain] | None
        Optional bounded-context marker. Must be a ``BaseDomain`` subclass when
        set. ``None`` means no domain edge in the graph (policy depends on your
        invariants).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to **classes**, not functions or methods.
- Target must inherit ``EntityGateHost`` (typically via ``BaseEntity``).
- ``description`` — non-empty ``str``.
- ``domain`` — ``None`` or ``BaseDomain`` subclass.
- Decorator order relative to other class decorators is otherwise unconstrained.

═══════════════════════════════════════════════════════════════════════════════
INTEGRATION (SCRATCH → COORDINATOR)
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Customer order", domain=ShopDomain)
        │
        ▼  writes scratch on cls
    _entity_info = {"description": ..., "domain": ShopDomain}
        │
        ▼  EntityGateHostInspector at GateCoordinator.build()
    Reads _entity_info + pydantic model_fields → FacetPayload / snapshot
        │
        ▼
    Facet graph: ``entity`` node, optional ``belongs_to`` domain edge, …

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field

    from action_machine.domain import BaseEntity, BaseDomain
    from action_machine.domain.entity_decorator import entity

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "E-commerce shop"

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        id: str = Field(description="Order id")
        amount: float = Field(description="Order total", ge=0)
        status: str = Field(description="Workflow status")

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    EntityDecoratorError — wrong target type, missing gate host, bad
                           ``description`` / ``domain``.
"""

from __future__ import annotations

from collections.abc import Callable

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity_gate_host import (
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

    Writes ``_entity_info`` on the target class. ``EntityGateHostInspector``
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
            ``EntityGateHost`` subclass.

    Example:
        @entity(description="Customer order", domain=ShopDomain)
        class OrderEntity(BaseEntity):
            id: str = Field(description="Order id")
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
