# src/action_machine/domain/base_domain.py
"""
Abstract base for all domain marker types in ActionMachine.

A domain is a typed class-level tag that groups actions, entities, and other
facets under one business area. It carries no runtime behavior and no instance
state, only validated ``ClassVar`` metadata consumed by inspectors and tooling.

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
    Domain registration enters the interchange graph **at build time** when inspectors
    emit vertices; that wiring is not declared in this module.

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
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

String-only domain identifiers hide typos until runtime or log analysis. A class
per domain gives static checking, refactoring, and a natural place for
``description`` text used in diagrams and generated docs. Requiring non-empty
descriptions matches the rest of ActionMachine: undocumented models are treated
as incomplete specifications, not silent defaults.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD)
═══════════════════════════════════════════════════════════════════════════════

- **Import / class body**: ``__init_subclass__`` runs; suffix and attributes are
  validated immediately when the subclass statement executes.
- **Coordinator ``build()``**: reads domain types from scratch elsewhere; no
  extra validation in this file.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from action_machine.exceptions.naming_suffix_error import NamingSuffixError
from graph.exclude_graph_model import exclude_graph_model

# Suffix required for every class that inherits BaseDomain (directly or indirectly).
_REQUIRED_SUFFIX = "Domain"

@exclude_graph_model
class BaseDomain(ABC):
    """
    AI-CORE-BEGIN
        ROLE: Typed domain identity marker.
        CONTRACT: Exposes validated class metadata used by decorators and inspectors.
        INVARIANTS: No instances required; class definition enforces suffix and metadata quality.
        AI-CORE-END
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain machine-readable name supplied as a class attribute by subclasses."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Domain human-readable description supplied as a class attribute by subclasses."""
        raise NotImplementedError

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
            f'Set e.g. {attr_name} = "..." in the class body.'
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
            f'or whitespace-only. Set a non-empty string, e.g. {attr_name} = "...".'
        )
