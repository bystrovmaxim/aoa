# src/action_machine/legacy/check_roles_intent.py
"""
CheckRolesIntent — marker mixin: declare participation in the role grammar (``@check_roles``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Types that carry ``CheckRolesIntent`` in MRO **commit** to expressing access rules via
``@check_roles`` (or explicit ``NoneRole`` / ``AnyRole``). The decorator checks
``issubclass`` at apply time and writes ``cls._role_info``; ``RoleIntentInspector``
and ``GraphCoordinator`` validate completeness during ``build()``.

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
    RoleIntentInspector facet snapshot
             |
             v
    RoleChecker runtime authorization

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``CheckRolesIntent`` is a pure marker; no logic, fields, or methods on the mixin.
- Classes that declare ``@check_roles`` must inherit ``CheckRolesIntent``.
- The decorator writes ``_role_info`` on the target class; the inspector reads
  it for graph construction.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``CheckRolesIntent``: marker mixin for role-grammar participation.
- ``_role_info``: class-level storage populated by ``@check_roles``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from action_machine.intents.check_roles import CheckRolesIntent, check_roles

    @check_roles(AdminRole)
    class AdminAction(BaseAction[P, R]):   # BaseAction already inherits CheckRolesIntent
        ...

Edge case (raises TypeError)::

    @check_roles(EditorRole)
    class NotAnAction:                     # does not inherit CheckRolesIntent
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Applying ``@check_roles`` to a class missing ``CheckRolesIntent`` raises ``TypeError``
  at import time.
- The marker performs no runtime enforcement; ``RoleChecker`` applies the spec.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Intent marker for role declarations on actions.
CONTRACT: Subclass required for ``@check_roles``; ``_role_info`` slot on decorated class.
INVARIANTS: Pure marker; decorated classes must be subclasses.
FLOW: decorator → _role_info → inspector → runtime role check.
FAILURES: TypeError on missing inheritance.
EXTENSION POINTS: None (marker only).
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any, ClassVar


class CheckRolesIntent:
    """
    Marker mixin declaring participation in ``@check_roles`` role grammar.

    AI-CORE-BEGIN
    ROLE: Role declaration marker for action classes.
    CONTRACT: Required base for classes decorated with ``@check_roles``.
    INVARIANTS: No behavior; only class-level ``_role_info`` contract.
    AI-CORE-END
    """

    _role_info: ClassVar[dict[str, Any]]
