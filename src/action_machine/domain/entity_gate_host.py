# src/action_machine/domain/entity_gate_host.py
"""
EntityGateHost — marker mixin and invariants for the ``@entity`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``EntityGateHost`` is a **marker mixin** that **authorizes** applying ``@entity``
to a class. The decorator checks:

    if not issubclass(cls, EntityGateHost):
        raise EntityDecoratorError(...)

Without ``EntityGateHost`` in the MRO, ``@entity`` raises ``EntityDecoratorError``.
That prevents accidentally tagging arbitrary classes as domain entities.

``BaseEntity`` already inherits ``EntityGateHost``, so normal entities need no
extra mixin. If someone applies ``@entity`` to a “bare” class, they get an
explicit, early error.

All **argument** and **target** checks for ``@entity`` live in this module
(``validate_entity_*``). The ``entity`` decorator only calls them and then
writes ``_entity_info`` (scratch).

═══════════════════════════════════════════════════════════════════════════════
GATE-HOST PATTERN (AOA)
═══════════════════════════════════════════════════════════════════════════════

Gate hosts are a cross-cutting pattern in ActionMachine: each **class-level**
decorator expects a matching **marker mixin** in the MRO:

    ActionMetaGateHost       → authorizes ``@meta`` on Action
    ResourceMetaGateHost     → authorizes ``@meta`` on ResourceManager
    RoleGateHost             → authorizes ``@check_roles``
    DependencyGateHost       → authorizes ``@depends``
    ConnectionGateHost       → authorizes ``@connection``
    EntityGateHost           → authorizes ``@entity``

Mixins carry **no behavior** — they exist so ``issubclass`` expresses **opt-in**
to a grammar fragment. That is deliberate, not magic.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE (SCRATCH → INSPECTOR → COORDINATOR)
═══════════════════════════════════════════════════════════════════════════════

    class BaseEntity(..., EntityGateHost, DescribedFieldsGateHost):
        ...                             # marker: @entity is allowed

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        ...

    # Decorator checks:
    #   issubclass(OrderEntity, EntityGateHost) → OK
    #   cls._entity_info = {"description": ..., "domain": ...}   # scratch

    # EntityGateHostInspector during GateCoordinator.build():
    #   reads _entity_info + model_fields → FacetPayload + typed snapshot

═══════════════════════════════════════════════════════════════════════════════
CLASS-LEVEL SCRATCH
═══════════════════════════════════════════════════════════════════════════════

``@entity`` writes ``_entity_info`` on the class — a dict with ``"description"``
and ``"domain"``. ``EntityGateHostInspector`` and graph tooling read it when the
coordinator is built.

    _entity_info : dict[str, Any]
        {"description": str, "domain": type[BaseDomain] | None}

The attribute is created by the decorator, not declared on ``EntityGateHost``.
A ``ClassVar`` annotation is provided for type checkers.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    # BaseEntity already includes EntityGateHost:
    @entity(description="Customer", domain=CrmDomain)
    class CustomerEntity(BaseEntity):
        id: str = Field(description="Customer id")
        name: str = Field(description="Display name")

    # @entity on a class without EntityGateHost → EntityDecoratorError
"""

from __future__ import annotations

from typing import Any, ClassVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.exceptions import EntityDecoratorError


class EntityGateHost:
    """
    Marker mixin: ``@entity`` may be applied to this class.

    A class **without** ``EntityGateHost`` in its MRO cannot be decorated with
    ``@entity`` — the decorator raises ``EntityDecoratorError``.

    The mixin has no methods or instance state; it exists for ``issubclass``
    checks in the decorator and in entity facet validation during
    ``GateCoordinator.build()``.

    Class attributes (written by ``@entity``):
        _entity_info : dict[str, Any]
            ``{"description": str, "domain": type[BaseDomain] | None}``.
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
    Invariant: decorator target is a ``type`` with ``EntityGateHost`` in the MRO.

    Raises:
        EntityDecoratorError: not a class, or missing ``EntityGateHost``.
    """
    if not isinstance(cls, type):
        raise EntityDecoratorError(
            f"@entity applies only to a class. "
            f"Got {type(cls).__name__}: {cls!r}."
        )

    if not issubclass(cls, EntityGateHost):
        raise EntityDecoratorError(
            f"@entity applied to {cls.__name__}, which does not inherit "
            f"EntityGateHost. Subclass BaseEntity, e.g. "
            f"class {cls.__name__}(BaseEntity): ..."
        )
