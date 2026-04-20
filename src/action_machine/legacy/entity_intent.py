# src/action_machine/legacy/entity_intent.py
"""
EntityIntent — marker mixin and invariant validators for ``@entity``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``EntityIntent`` is a marker mixin that declares participation in the
``@entity`` grammar. The decorator checks:

    if not issubclass(cls, EntityIntent):
        raise EntityDecoratorError(...)

Without ``EntityIntent`` in the MRO, ``@entity`` raises
``EntityDecoratorError``. This prevents accidentally tagging arbitrary classes
as entities.

``BaseEntity`` already inherits ``EntityIntent``, so normal entities need no
extra mixin. If someone applies ``@entity`` to a “bare” class, they get an
explicit, early error.

All ``@entity`` argument and target checks live in
:mod:`action_machine.intents.entity.entity_decorator`
(``validate_entity_description``, ``validate_entity_domain``,
``validate_entity_decorator_target``). The decorator then writes ``_entity_info`` (scratch).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseEntity(..., EntityIntent, DescribedFieldsIntent):
        ...                             # marker: @entity grammar declared

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        ...

    # Decorator checks:
    #   issubclass(OrderEntity, EntityIntent) → OK
    #   cls._entity_info = {"description": ..., "domain": ...}   # scratch

    # EntityIntentInspector during GraphCoordinator.build():
    #   reads _entity_info + model_fields → FacetVertex + typed snapshot

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # BaseEntity already includes EntityIntent:
    @entity(description="Customer", domain=CrmDomain)
    class CustomerEntity(BaseEntity):
        id: str = Field(description="Customer id")
        name: str = Field(description="Display name")

    # @entity on a class without EntityIntent -> EntityDecoratorError

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Marker and validator layer for entity declaration grammar.
CONTRACT: ``EntityIntent`` marks eligible classes for ``@entity``; decorator enforces MRO in entity_decorator.
INVARIANTS: No runtime behavior, only declaration guards and scratch-shape assumptions.
FLOW: decorator -> validators -> ``_entity_info`` write -> inspector consumption at build.
FAILURES: ``EntityDecoratorError`` on invalid arguments, domain type, or missing marker inheritance.
EXTENSION POINTS: projects can reuse validators in custom entity decorators.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any, ClassVar


class EntityIntent:
    """
    Marker mixin: ``@entity`` may be applied to this class.

    A class **without** ``EntityIntent`` in its MRO cannot be decorated with
    ``@entity`` — the decorator raises ``EntityDecoratorError``.

    The mixin has no methods or instance state; it exists for ``issubclass``
    checks in the decorator and in entity facet validation during
    ``GraphCoordinator.build()``.

    Class attributes (written by ``@entity``):
        _entity_info : dict[str, Any]
            ``{"description": str, "domain": type[BaseDomain] | None}``.

    AI-CORE-BEGIN
    ROLE: Marker mixin declaring eligibility for ``@entity``.
    CONTRACT: Presence in MRO is required by decorator target validation.
    INVARIANTS: Holds no methods or instance state; only class-level marker semantics.
    AI-CORE-END
    """

    _entity_info: ClassVar[dict[str, Any]]


# ═════════════════════════════════════════════════════════════════════════════
# @entity invariants (decorator + graph inspectors)
# ═════════════════════════════════════════════════════════════════════════════


def entity_info_is_set(cls: type) -> bool:
    """
    Graph invariant: class was decorated with ``@entity`` (has ``_entity_info``).

    Does not validate dict shape — only presence of the scratch attribute.
    """
    return getattr(cls, "_entity_info", None) is not None
