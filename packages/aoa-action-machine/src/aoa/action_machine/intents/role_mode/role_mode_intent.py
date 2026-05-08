# packages/aoa-action-machine/src/aoa/action_machine/intents/role_mode/role_mode_intent.py
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

"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode


class RoleModeIntent:
    """
    AI-CORE-BEGIN
    ROLE: Lifecycle-intent marker for role classes.
    CONTRACT: Enables ``@role_mode`` decorator eligibility through MRO.
    INVARIANTS: No behavior/state beyond metadata contract slot.
    AI-CORE-END
    """

    __slots__ = ()

    if TYPE_CHECKING:
        _role_mode_info: ClassVar[dict[str, RoleMode]]
