# src/action_machine/intents/role_mode/role_mode_decorator.py
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
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar, cast

from action_machine.auth.base_role import BaseRole

_RT = TypeVar("_RT", bound=type)


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

    """

    def decorator(cls: _RT) -> _RT:
        if not isinstance(cls, type):
            raise TypeError(f"@role_mode applies only to classes, got {type(cls)!r}.")
        cast(Any, cls)._role_mode_info = {"mode": mode}
        return cls

    return decorator
