# src/action_machine/auth/role_intent.py
"""
RoleIntent — marker mixin: declare participation in the role grammar (``@check_roles``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Types that carry ``RoleIntent`` in MRO **commit** to expressing access rules via
``@check_roles`` (or explicit ``ROLE_NONE`` / ``ROLE_ANY``). The decorator checks
``issubclass`` at apply time and writes ``cls._role_info``; ``RoleIntentInspector``
and ``GateCoordinator`` validate completeness during ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class BaseAction(ABC, RoleIntent, ...):
        pass

    @check_roles(AdminRole)
    class AdminAction(BaseAction):
        ...

    # @check_roles checks:
    #   issubclass(AdminAction, RoleIntent) → True
    #   writes cls._role_info = {"spec": AdminRole}

    # RoleIntentInspector reads _role_info → Snapshot → graph node "role"
    # ActionProductMachine reads spec via GateCoordinator.get_snapshot(cls, "role")

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleIntent`` is a pure marker; no logic, fields, or methods on the mixin.
- Classes that declare ``@check_roles`` must inherit ``RoleIntent``.
- The decorator writes ``_role_info`` on the target class; the inspector reads
  it for graph construction.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    from action_machine.auth import RoleIntent, check_roles

    @check_roles(AdminRole)
    class AdminAction(BaseAction[P, R]):   # BaseAction already inherits RoleIntent
        ...

Edge case (raises TypeError)::

    @check_roles(EditorRole)
    class NotAnAction:                     # does not inherit RoleIntent
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Applying ``@check_roles`` to a class missing ``RoleIntent`` raises ``TypeError``
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


class RoleIntent:
    """
    Intent marker: the class participates in the **role** grammar (``@check_roles`` only).

    Without this mixin, ``@check_roles`` raises ``TypeError``. The decorator
    stores the role specification in ``_role_info``. This is unrelated to
    ``CheckerIntent`` / result or field checkers on aspect methods.
    """

    _role_info: ClassVar[dict[str, Any]]
