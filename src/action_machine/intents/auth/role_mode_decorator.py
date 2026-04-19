# src/action_machine/intents/auth/role_mode_decorator.py
"""
Lifecycle mode for role marker classes and ``@role_mode`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleMode`` classifies how a ``BaseRole`` subclass participates in access
checks and graph validation. Modes are assigned **only** via ``@role_mode``;
they are never set as plain class attributes on the role body.

``@role_mode`` stores ``RoleMode`` on a role class (``cls._role_mode_info``) so
``RoleChecker`` and graph inspectors share one source of truth, analogous to
how ``@check_roles`` writes ``_role_info`` on actions.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Enum members are stable public API values.
- Runtime and graph inspectors read the mode from ``cls._role_mode_info``
  (written by ``@role_mode``), not from ad-hoc class attributes.
- The decorated class must inherit ``RoleModeIntent`` (``TypeError`` otherwise).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @role_mode(RoleMode.ALIVE)
            |
            v
    role class _role_mode_info["mode"]
            |
            v
    RoleMode.declared_for(role_cls)
            |
            v
    RoleChecker + role inspectors

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleMode``: lifecycle enum for role classes.
- ``role_mode``: decorator attaching mode metadata on class.
- ``RoleMode.declared_for``: validated accessor used by runtime and inspectors.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: ``RoleMode.ALIVE`` on a concrete role class.

Edge case: ``RoleMode.UNUSED`` in ``@check_roles`` raises ``ValueError`` at import
time; ``RoleClassInspector`` rejects ``UNUSED`` in the role MRO at ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleChecker`` and ``@check_roles`` enforce ``SILENCED``, ``DEPRECATED``, and
  ``UNUSED`` at runtime / decoration time (see ``RoleMode.declared_for``).
  ``RoleClassInspector`` / ``RoleModeIntentInspector`` add graph-level facets.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role lifecycle enum + decorator + declared-mode accessor.
CONTRACT: Members ALIVE, DEPRECATED, SILENCED, UNUSED; ``@role_mode`` scratch;
    ``RoleMode.declared_for(role_cls)`` reads validated mode.
INVARIANTS: Mode assigned only through ``@role_mode`` on ``RoleModeIntent`` types.
FLOW: Decorator writes ``_role_mode_info`` → consumers call ``declared_for``.
FAILURES: TypeError for bad decorator target or missing/invalid scratch.
EXTENSION POINTS: New modes require coordinated updates to checker + inspectors.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from action_machine.auth.base_role import BaseRole
from action_machine.intents.auth.role_mode_intent import RoleModeIntent

_RT = TypeVar("_RT", bound=type[RoleModeIntent])


class RoleMode(Enum):
    """Lifecycle mode for a role class (set exclusively via ``@role_mode``)."""

    ALIVE = "alive"
    DEPRECATED = "deprecated"
    SILENCED = "silenced"
    UNUSED = "unused"

    @classmethod
    def declared_for(cls, role: type[BaseRole]) -> RoleMode:
        """
        Return the ``RoleMode`` stored by ``@role_mode`` on a ``BaseRole`` subclass.

        Raises:
            TypeError: ``role`` is not a ``BaseRole`` subtype or lacks
                ``_role_mode_info`` / a valid ``mode`` entry.
        """
        if not issubclass(role, BaseRole):
            raise TypeError(
                f"{cls.__name__}.declared_for expects a BaseRole subclass, got {role!r}."
            )
        info = getattr(role, "_role_mode_info", None)
        if not isinstance(info, dict):
            raise TypeError(
                f"Role {role.__qualname__} has no _role_mode_info; apply @role_mode(...)."
            )
        raw = info.get("mode")
        if not isinstance(raw, RoleMode):
            raise TypeError(
                f"Role {role.__qualname__} has invalid _role_mode_info['mode']: {raw!r}."
            )
        return raw


def role_mode(mode: RoleMode) -> Callable[[_RT], _RT]:
    """
    Attach ``RoleMode`` metadata to a role class (``_role_mode_info``).

    Must be applied to classes that inherit ``RoleModeIntent`` (e.g. via
    ``BaseRole``).
    """

    def decorator(cls: _RT) -> _RT:
        if not isinstance(cls, type):
            raise TypeError(f"@role_mode applies only to classes, got {type(cls)!r}.")
        if not issubclass(cls, RoleModeIntent):
            raise TypeError(
                f"@role_mode was applied to {cls.__name__!r}, which does not inherit "
                f"RoleModeIntent. Role classes must extend BaseRole (or another "
                f"RoleModeIntent subtype)."
            )
        cls._role_mode_info = {"mode": mode}
        return cls

    return decorator
