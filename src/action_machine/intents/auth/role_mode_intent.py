# src/action_machine/intents/auth/role_mode_intent.py
"""
Marker mixin: declare intent to use ``@role_mode`` on role declaration classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleModeIntent`` mirrors the relationship between ``RoleIntent`` and
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
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole(RoleModeIntent, ABC)
           │
           ├── concrete role classes
           │
    @role_mode(...)  ──requires──▶  issubclass(cls, RoleModeIntent)

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

- The mixin does not participate in action authorization; use ``RoleIntent``
  on actions and ``BaseRole`` / ``RoleModeIntent`` on role types.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Intent marker for role lifecycle decorator.
CONTRACT: Empty mixin; ``@role_mode`` applies only when this intent is in MRO,
    analogous to ``RoleIntent`` for ``@check_roles``.
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
    from action_machine.intents.auth.role_mode_decorator import RoleMode


class RoleModeIntent:
    """
    Marker mixin: declares that a class may carry ``@role_mode`` metadata.

    ``BaseRole`` inherits this type; do not use ``RoleModeIntent`` on actions.
    """

    __slots__ = ()

    if TYPE_CHECKING:
        _role_mode_info: ClassVar[dict[str, RoleMode]]
