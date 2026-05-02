# src/action_machine/intents/check_roles/check_roles_intent.py
"""
CheckRolesIntent — marker mixin: declare participation in the role grammar (``@check_roles``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Types that carry ``CheckRolesIntent`` in MRO **commit** to expressing access rules via
``@check_roles`` (or explicit ``NoneRole`` / ``AnyRole``). The decorator checks
``issubclass`` at apply time and writes ``cls._role_info`` for ``ActionGraphNode`` / ``RoleChecker``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction (..., CheckRolesIntent, ...)
             |
             v
    @check_roles(...)
             |
             v
    cls._role_info = {"spec": ...}
             |
             v
    ``ActionGraphNode`` materializes ``RoleGraphEdge`` topology
             |
             v
    RoleChecker runtime authorization

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``CheckRolesIntent``: marker mixin for role-grammar participation.
- ``_role_info``: class-level storage populated by ``@check_roles``.

"""

from __future__ import annotations

from typing import Any, ClassVar


class CheckRolesIntent:
    """
    AI-CORE-BEGIN
    ROLE: Role declaration marker for action classes.
    CONTRACT: Required base for classes decorated with ``@check_roles``.
    INVARIANTS: No behavior; only class-level ``_role_info`` contract.
    AI-CORE-END
    """

    _role_info: ClassVar[dict[str, Any]]
