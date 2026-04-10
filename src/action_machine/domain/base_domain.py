# src/action_machine/domain/base_domain.py
"""
Abstract base for all **domain markers** in ActionMachine.

A domain is a typed class-level tag that groups actions, entities, and other
facets under one business area. It carries no runtime behavior and no instance
state—only validated ``ClassVar`` metadata consumed by coordinators and
documentation exporters.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseDomain`` lets code refer to ``OrdersDomain`` instead of bare strings like
``"orders"``, so typos break at import time, IDEs can navigate and rename, and
metadata (name + human-readable description) stays attached to a single type.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Enforcing the ``*Domain`` class-name suffix.
    Validating ``name`` and ``description`` as non-empty strings on concrete
    domain classes (with a defined MRO escape hatch for intermediate bases).

**Out of scope**
    Domain logic, workflows, or persistence.
    Uniqueness of ``name`` across the whole program (multiple classes may
    legally share the same string until a higher layer forbids it).
    Registering domains in ``GateCoordinator``—that happens at **build** time
    via inspectors, not in this module.

═══════════════════════════════════════════════════════════════════════════════
TERMINOLOGY (USE CONSISTENTLY)
═══════════════════════════════════════════════════════════════════════════════

**Gate host / decorator / scratch / inspector / gate coordinator** — same
meaning as in ``action_machine.domain`` and metadata packages: domains are
**referenced** by type from decorators (e.g. ``@entity(..., domain=...)``); the
coordinator graph is built elsewhere from those references.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseDomain (ABC)
        ├── __init_subclass__  → suffix check → _validate_class_attr(name)
        │                                              → _validate_class_attr(description)
        └── concrete:  class OrdersDomain(BaseDomain):
                            name = "orders"
                            description = "…"

Conceptual use (declarations only)::

    @meta(..., domain=OrdersDomain)
    @entity(..., domain=OrdersDomain)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every subclass name **must** end with ``"Domain"`` → else ``NamingSuffixError``
  at **class definition** time (including intermediate abstract subclasses).
- Leaf domains must expose non-empty ``str`` values for ``name`` and
  ``description`` (after ``strip()``), either on the class or on an intermediate
  base **below** ``BaseDomain`` in the MRO.
- ``BaseDomain`` itself is not validated as a subclass body; rules apply when
  **subclasses** are defined.

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

String-only domain identifiers hide typos until runtime or log analysis. A class
per domain gives static checking, refactoring, and a natural place for
``description`` text used in diagrams and generated docs. Requiring non-empty
descriptions matches the rest of ActionMachine: undocumented models are treated
as incomplete specifications, not silent defaults.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import / class body**: ``__init_subclass__`` runs; suffix and attributes are
  validated immediately when the subclass statement executes.
- **Coordinator ``build()``**: reads domain types from scratch elsewhere; no
  extra validation in this file.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Valid — concrete domain::

    class OrdersDomain(BaseDomain):
        name = "orders"
        description = "Order capture, payment, and fulfillment"

Valid — intermediate base without ``name`` / ``description``, then concrete::

    class ExternalServiceDomain(BaseDomain):
        is_external = True

    class StripeDomain(ExternalServiceDomain):
        name = "stripe"
        description = "Card payments via Stripe"

Edge — bad class name::

    class Orders(BaseDomain):
        name = "orders"
        description = "Orders"
    # NamingSuffixError

Edge — missing ``description``::

    class OnlyNameDomain(BaseDomain):
        name = "only"
    # ValueError: missing 'description'

═══════════════════════════════════════════════════════════════════════════════
ERROR EXAMPLES (MESSAGE SHAPES)
═══════════════════════════════════════════════════════════════════════════════

Naming suffix::

    class Orders(BaseDomain):
        name = "orders"
        description = "Orders"
    # NamingSuffixError: ... inherits from BaseDomain ... suffix 'Domain' ...

Missing attribute::

    class BadDomain(BaseDomain):
        description = "Has description but no name"
    # ValueError: ... does not define ... 'name' ...

Empty string::

    class EmptyDomain(BaseDomain):
        name = ""
        description = "Has description"
    # ValueError: ... cannot be empty or whitespace-only ...

Wrong type::

    class IntDomain(BaseDomain):
        name = 42
        description = "text"
    # TypeError: ... must be str, got int ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``NamingSuffixError``: class name does not end with ``"Domain"``.
- ``ValueError``: missing ``name`` / ``description``, or empty after ``strip()``.
- ``TypeError``: ``name`` or ``description`` is not a ``str``.

This module does **not** deduplicate ``name`` strings or enforce global registry
uniqueness.
"""
from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from action_machine.core.exceptions import NamingSuffixError

# Suffix required for every class that inherits BaseDomain (directly or indirectly).
_REQUIRED_SUFFIX = "Domain"


class BaseDomain(ABC):
    """
    Abstract base for all domain marker classes.

    **Role**
        Supply ``name`` and ``description`` as ``ClassVar[str]`` metadata for a
        business area. Subclasses are never instantiated for domain identity;
        the **type** is the handle.

    **Invariants**
        - Subclass names end with the suffix ``Domain`` (``__init_subclass__``).
        - Concrete branches define non-empty string ``name`` and ``description``
          (possibly inherited from an intermediate base above ``BaseDomain``).

    **Neighbors**
        - Referenced from decorators such as ``@entity`` and ``@meta``.
        - Consumed by metadata inspectors when building the gate coordinator graph.

    **Class attributes**
        ``name``
            Short stable identifier (e.g. ``"orders"``).
        ``description``
            Human-readable specification text for docs and diagrams.
    """

    name: ClassVar[str]
    description: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Validate naming and required class attributes for each subclass.

        Order:
            1. Class name must end with ``Domain`` (always, including
               intermediate bases).
            2. ``name`` — present in MRO, ``str``, non-empty after ``strip()``.
            3. ``description`` — same rules.

        Intermediate abstract subclasses may omit ``name`` and ``description``
        in their own ``__dict__`` if a base between them and ``BaseDomain`` defines
        those attributes; suffix validation still runs.

        Args:
            **kwargs: Forwarded to ``type.__init_subclass__``.

        Raises:
            NamingSuffixError: Class name does not end with ``Domain``.
            ValueError: Missing ``name`` / ``description``, or whitespace-only value.
            TypeError: ``name`` or ``description`` is not a ``str``.
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits from BaseDomain but its name must "
                f"end with the suffix '{_REQUIRED_SUFFIX}'. "
                f"Rename it to '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

        _validate_class_attr(cls, "name")
        _validate_class_attr(cls, "description")


def _validate_class_attr(cls: type, attr_name: str) -> None:
    """
    Ensure a required class attribute exists, is a ``str``, and is non-empty.

    If ``attr_name`` is absent from ``cls.__dict__``, walk the MRO: if an
    intermediate base (not ``BaseDomain``) defines it, treat the subclass as
    inheriting a valid value and return. Otherwise raise ``ValueError``.

    Args:
        cls: Subclass being validated.
        attr_name: ``"name"`` or ``"description"``.

    Raises:
        ValueError: Attribute missing from the class and from qualifying bases,
            or empty / whitespace-only when set on ``cls``.
        TypeError: Value on ``cls`` is not a ``str``.
    """
    if attr_name not in cls.__dict__:
        for base in cls.__mro__[1:]:
            if base is BaseDomain:
                continue
            if attr_name in base.__dict__:
                return
        raise ValueError(
            f"Class '{cls.__name__}' inherits from BaseDomain but does not define "
            f"the class attribute '{attr_name}'. "
            f"Set e.g. {attr_name} = \"...\" in the class body."
        )

    raw_value = cls.__dict__[attr_name]

    if not isinstance(raw_value, str):
        raise TypeError(
            f"Class attribute '{attr_name}' on '{cls.__name__}' must be str, "
            f"got {type(raw_value).__name__}: {raw_value!r}."
        )

    if not raw_value.strip():
        raise ValueError(
            f"Class attribute '{attr_name}' on '{cls.__name__}' cannot be empty "
            f"or whitespace-only. Set a non-empty string, e.g. {attr_name} = \"...\"."
        )
