# src/action_machine/auth/role_mode.py
"""
Lifecycle mode for role marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleMode`` classifies how a ``BaseRole`` subclass participates in access
checks and graph validation. Modes are assigned **only** via ``@role_mode``;
they are never set as plain class attributes on the role body.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Enum members are stable public API values.
- Runtime and graph inspectors read the mode from ``cls._role_mode_info``
  (written by ``@role_mode``), not from ad-hoc class attributes.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @role_mode(RoleMode.ALIVE)
    class ExampleRole(BaseRole):
        ...

    import → role_mode decorator → cls._role_mode_info["mode"] == RoleMode.ALIVE
                → RoleChecker (runtime) / GateCoordinator inspectors (PR-3)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: ``RoleMode.ALIVE`` on a concrete role class.

Edge case: ``RoleMode.UNUSED`` in ``@check_roles`` raises ``ValueError`` at import
time; ``RoleClassInspector`` rejects ``UNUSED`` in ``includes`` / MRO at ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleChecker`` and ``@check_roles`` enforce ``SILENCED``, ``DEPRECATED``, and
  ``UNUSED`` at runtime / decoration time (see ``get_declared_role_mode``).
  ``RoleClassInspector`` / ``RoleModeGateHostInspector`` add graph-level facets.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role lifecycle enum (single source of mode values).
CONTRACT: Members ALIVE, DEPRECATED, SILENCED, UNUSED as per product plan.
INVARIANTS: Assigned only through ``@role_mode`` scratch on role classes.
FLOW: Decorator writes mode → consumers read ``_role_mode_info``.
FAILURES: N/A at enum level.
EXTENSION POINTS: New modes require coordinated updates to checker + inspectors.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from enum import Enum

from action_machine.auth.base_role import BaseRole


class RoleMode(Enum):
    """Lifecycle mode for a role class (set exclusively via ``@role_mode``)."""

    ALIVE = "alive"
    DEPRECATED = "deprecated"
    SILENCED = "silenced"
    UNUSED = "unused"


def get_declared_role_mode(role: type[BaseRole]) -> RoleMode:
    """
    Return the ``RoleMode`` stored by ``@role_mode`` on a ``BaseRole`` subclass.

    Raises:
        TypeError: ``role`` is not a ``BaseRole`` subtype or lacks
            ``_role_mode_info`` / a valid ``mode`` entry.
    """
    if not issubclass(role, BaseRole):
        raise TypeError(
            f"get_declared_role_mode expects a BaseRole subclass, got {role!r}."
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
