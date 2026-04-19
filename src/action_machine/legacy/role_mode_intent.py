# src/action_machine/legacy/role_mode_intent.py
"""
Marker mixin: declare intent to use ``@role_mode`` on role declaration classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleModeIntent`` mirrors the relationship between ``CheckRolesIntent`` and
``@check_roles``: only types that inherit this empty mixin may be decorated with
``@role_mode``. This fails fast at import time and keeps graph inspectors aligned
with a single discoverable MRO subtree.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The mixin defines **no** fields or methods; it is a pure capability marker.
- ``@role_mode`` raises ``TypeError`` if the target class does not inherit
  ``RoleModeIntent`` (directly or indirectly).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRole (..., RoleModeIntent, ...)
              |
              v
    concrete role subclasses
              |
              v
    @role_mode(...) decorator
              |
              v
    issubclass(target, RoleModeIntent) guard
              |
              v
    _role_mode_info metadata on class

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``RoleModeIntent``: pure marker mixin for role lifecycle declarations.
- ``role_mode`` decorator (neighbor module): requires this marker in MRO.
- ``_role_mode_info``: class-level metadata slot populated by decorator.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class OrderViewerRole(BaseRole):  # BaseRole extends RoleModeIntent
        ...

    @role_mode(RoleMode.ALIVE)
    class RegisteredRole(BaseRole):
        ...

Edge case: applying ``@role_mode`` to a plain ``object`` subclass →
``TypeError`` from the decorator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The mixin does not participate in action authorization; use ``CheckRolesIntent``
  on actions and ``BaseRole`` / ``RoleModeIntent`` on role types.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Intent marker for role lifecycle decorator.
CONTRACT: Empty mixin; ``@role_mode`` applies only when this intent is in MRO,
    analogous to ``CheckRolesIntent`` for ``@check_roles``.
INVARIANTS: No behavior; subclass check in ``role_mode`` decorator.
FLOW: MRO marker → decorator guard → scratch on class.
FAILURES: TypeError when decorator applied without mixin.
EXTENSION POINTS: ``RoleModeIntentInspector`` walks this mixin subtree.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from action_machine.intents.role_mode.role_mode_decorator import RoleMode


class RoleModeIntent:
    """
    Marker mixin: declares that a class may carry ``@role_mode`` metadata.

    AI-CORE-BEGIN
    ROLE: Lifecycle-intent marker for role classes.
    CONTRACT: Enables ``@role_mode`` decorator eligibility through MRO.
    INVARIANTS: No behavior/state beyond metadata contract slot.
    AI-CORE-END
    """

    __slots__ = ()

    if TYPE_CHECKING:
        _role_mode_info: ClassVar[dict[str, RoleMode]]
