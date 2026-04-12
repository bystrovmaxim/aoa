# src/action_machine/auth/base_role.py
"""
Abstract base for typed **role marker** classes (frozen declaration, like domains).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseRole`` is the typed counterpart to string role names: each role is a
**class** carrying stable ``name`` / ``description`` metadata and an optional
``includes`` tuple for compositional privileges. The design mirrors
``BaseDomain`` — immutable class-level declaration, no product instance state.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Subclass names must end with the suffix ``Role`` (``NamingSuffixError`` at
  class definition time, including intermediate bases).
- Concrete branches define non-empty ``str`` values for ``name`` and
  ``description`` (possibly inherited from an intermediate base below
  ``BaseRole`` in the MRO).
- ``includes`` is a ``ClassVar`` **tuple** of ``BaseRole`` subclasses (possibly
  empty). Each entry must be a ``type`` that is a subclass of ``BaseRole``.
- Lifecycle mode is **not** set on the class body; use ``@role_mode`` (see
  ``role_mode_decorator`` module).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class OrderViewerRole(BaseRole):
        name = "order_viewer"
        description = "Read-only order visibility."
        includes = ()

    @role_mode(RoleMode.ALIVE)
    class OrderManagerRole(BaseRole):
        name = "order_manager"
        description = "Full order control."
        includes = (OrderViewerRole,)

    @check_roles(OrderManagerRole)   # action decorator (separate module)
    class CancelOrderAction(...):
        ...

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Valid concrete role with ``includes = ()``.

Edge case: ``includes = (NotARole,)`` where ``NotARole`` is not a ``BaseRole``
subclass → ``TypeError`` at class definition time.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``NamingSuffixError``, ``ValueError``, ``TypeError`` from ``__init_subclass__``
  mirror ``BaseDomain`` rules for metadata quality.
- Global uniqueness of ``name``, acyclic ``includes``, and related topology
  rules are validated at ``GateCoordinator.build()`` (``RoleClassInspector``),
  not in this module.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Abstract role marker (parallel to ``BaseDomain`` for domains).
CONTRACT: ClassVar ``name``, ``description``, ``includes`` tuple; ``*Role`` suffix.
INVARIANTS: Validation only in ``__init_subclass__``; graph does not re-validate
    string emptiness (topology via ``RoleClassInspector``).
FLOW: Import defines role type → ``@role_mode`` adds scratch → actions reference
    role types in ``@check_roles``.
FAILURES: NamingSuffixError, ValueError, TypeError on bad subclass bodies.
EXTENSION POINTS: Runtime string tokens resolved via ``StringRoleRegistry`` when
    no declared role ``name`` matches.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from action_machine.auth.role_mode_gate_host import RoleModeGateHost
from action_machine.core.exceptions import NamingSuffixError

_REQUIRED_SUFFIX = "Role"


class BaseRole(RoleModeGateHost, ABC):
    """
    Abstract base for role marker classes (type-as-capability, like ``BaseDomain``).

    **Contract**
        Supply ``name``, ``description``, and ``includes`` as class attributes.
        Subclass names end with ``Role``. Use ``@role_mode`` for lifecycle mode.

    **Neighbors**
        Referenced from ``@check_roles`` on actions; token resolution uses
        ``StringRoleRegistry`` only in ``resolve_role_name_to_type``.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    includes: ClassVar[tuple[type[BaseRole], ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits from BaseRole but its name must "
                f"end with the suffix '{_REQUIRED_SUFFIX}'. "
                f"Rename it to e.g. '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

        _validate_role_class_attr(cls, "name")
        _validate_role_class_attr(cls, "description")
        _validate_includes(cls)


def _validate_role_class_attr(cls: type, attr_name: str) -> None:
    """Ensure ``name`` / ``description`` exist, are ``str``, and are non-empty."""
    if attr_name not in cls.__dict__:
        for base in cls.__mro__[1:]:
            if base is BaseRole:
                continue
            if attr_name in base.__dict__:
                return
        raise ValueError(
            f"Class '{cls.__name__}' inherits from BaseRole but does not define "
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
            f"or whitespace-only."
        )


def _validate_includes(cls: type) -> None:
    """Ensure ``includes`` override is a tuple of ``BaseRole`` subclasses."""
    if "includes" not in cls.__dict__:
        return

    raw = cls.__dict__["includes"]
    if not isinstance(raw, tuple):
        raise TypeError(
            f"Class '{cls.__name__}': 'includes' must be a tuple of role types, "
            f"got {type(raw).__name__}."
        )
    for i, item in enumerate(raw):
        if not isinstance(item, type) or not issubclass(item, BaseRole):
            raise TypeError(
                f"Class '{cls.__name__}': includes[{i}] must be a BaseRole "
                f"subclass, got {item!r}."
            )
