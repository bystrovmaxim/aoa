# src/action_machine/domain/entity_intent.py
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

All argument and target checks for ``@entity`` live in this module
(``validate_entity_*``). The ``entity`` decorator only calls them and then
writes ``_entity_info`` (scratch).

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
    #   reads _entity_info + model_fields → FacetPayload + typed snapshot

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@entity`` applies only to classes with ``EntityIntent`` in MRO.
- ``description`` must be a non-empty string.
- ``domain`` must be ``None`` or a ``BaseDomain`` subclass.
- ``@entity`` writes ``_entity_info`` scratch consumed later by inspectors.

Class-level scratch shape:

    _entity_info : dict[str, Any]
        {"description": str, "domain": type[BaseDomain] | None}

The attribute is created by the decorator, not declared on ``EntityIntent``.
A ``ClassVar`` annotation is provided for type checkers.

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
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Raises ``EntityDecoratorError`` for invalid decorator arguments or target type.
- This module validates declaration-level contracts only; graph-level checks run during coordinator build.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Marker and validator layer for entity declaration grammar.
CONTRACT: ``EntityIntent`` marks eligible classes; ``validate_entity_*`` enforces decorator invariants.
INVARIANTS: No runtime behavior, only declaration guards and scratch-shape assumptions.
FLOW: decorator -> validators -> ``_entity_info`` write -> inspector consumption at build.
FAILURES: ``EntityDecoratorError`` on invalid arguments, domain type, or missing marker inheritance.
EXTENSION POINTS: projects can reuse validators in custom entity decorators.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any, ClassVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.exceptions import EntityDecoratorError


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


def validate_entity_description(description: Any) -> None:
    """
    Invariant: ``description`` is a non-empty ``str`` (after strip).

    Raises:
        EntityDecoratorError: not a string, or blank after strip.
    """
    if not isinstance(description, str):
        raise EntityDecoratorError(
            f"@entity: parameter 'description' must be str, "
            f"got {type(description).__name__}: {description!r}."
        )

    if not description.strip():
        raise EntityDecoratorError(
            "@entity: description cannot be empty. "
            "Provide a non-empty entity description, e.g. "
            '@entity(description="Customer order").'
        )


def validate_entity_domain(domain: Any) -> None:
    """
    Invariant: ``domain`` is ``None`` or a ``BaseDomain`` subclass.

    Raises:
        EntityDecoratorError: invalid ``domain`` type or not a subclass of ``BaseDomain``.
    """
    if domain is None:
        return

    if not isinstance(domain, type):
        raise EntityDecoratorError(
            f"@entity: parameter 'domain' must be a BaseDomain subclass or None, "
            f"got {type(domain).__name__}: {domain!r}. "
            f"Pass a domain class, e.g. domain=ShopDomain."
        )

    if not issubclass(domain, BaseDomain):
        raise EntityDecoratorError(
            f"@entity: parameter 'domain' must inherit BaseDomain, "
            f"got {domain.__name__}. Define a domain class such as "
            f"class {domain.__name__}Domain(BaseDomain): name = \"...\"."
        )


def validate_entity_decorator_target(cls: Any) -> None:
    """
    Invariant: decorator target is a ``type`` with ``EntityIntent`` in the MRO.

    Raises:
        EntityDecoratorError: not a class, or missing ``EntityIntent``.
    """
    if not isinstance(cls, type):
        raise EntityDecoratorError(
            f"@entity applies only to a class. "
            f"Got {type(cls).__name__}: {cls!r}."
        )

    if not issubclass(cls, EntityIntent):
        raise EntityDecoratorError(
            f"@entity applied to {cls.__name__}, which does not inherit "
            f"EntityIntent. Subclass BaseEntity, e.g. "
            f"class {cls.__name__}(BaseEntity): ..."
        )
