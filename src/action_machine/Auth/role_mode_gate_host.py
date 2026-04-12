# src/action_machine/auth/role_mode_gate_host.py
"""
Marker mixin that authorizes ``@role_mode`` on role declaration classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RoleModeGateHost`` mirrors the relationship between ``RoleGateHost`` and
``@check_roles``: only types that inherit this empty mixin may be decorated with
``@role_mode``. This fails fast at import time and keeps graph inspectors aligned
with a single discoverable MRO subtree.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The mixin defines **no** fields or methods; it is a pure capability marker.
- ``@role_mode`` raises ``TypeError`` if the target class does not inherit
  ``RoleModeGateHost`` (directly or indirectly).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole(RoleModeGateHost, ABC)
           │
           ├── concrete role classes
           │
    @role_mode(...)  ──requires──▶  issubclass(cls, RoleModeGateHost)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    class OrderViewerRole(BaseRole):  # BaseRole extends RoleModeGateHost
        ...

    @role_mode(RoleMode.ALIVE)
    class RegisteredRole(BaseRole):
        ...

Edge case: applying ``@role_mode`` to a plain ``object`` subclass →
``TypeError`` from the decorator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The mixin does not participate in action authorization; use ``RoleGateHost``
  on actions and ``BaseRole`` / ``RoleModeGateHost`` on role types.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Gate-host marker for role lifecycle decorator.
CONTRACT: Empty mixin; enables ``@role_mode`` the way ``RoleGateHost`` enables
    ``@check_roles``.
INVARIANTS: No behavior; subclass check in ``role_mode`` decorator.
FLOW: MRO marker → decorator guard → scratch on class.
FAILURES: TypeError when decorator applied without mixin.
EXTENSION POINTS: ``RoleModeGateHostInspector`` walks this mixin subtree.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from action_machine.auth.role_mode import RoleMode


class RoleModeGateHost:
    """
    Marker mixin: declares that a class may carry ``@role_mode`` metadata.

    ``BaseRole`` inherits this type; do not use ``RoleModeGateHost`` on actions.
    """

    __slots__ = ()

    if TYPE_CHECKING:
        _role_mode_info: ClassVar[dict[str, RoleMode]]
