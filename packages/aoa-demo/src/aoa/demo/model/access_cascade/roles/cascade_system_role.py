# packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_system_role.py
"""
CascadeSystemGateRole — the system-level branch of the access-cascade drawing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``CascadeSystemGateRole`` is a ``SystemRole`` fixture. It exists so the
diagram shows a system-level role branch; it is not an assignable business
role and carries no business meaning.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole → SystemRole → CascadeSystemGateRole   (system branch, drawn as a node)
"""

from __future__ import annotations

from aoa.action_machine.auth import SystemRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class CascadeSystemGateRole(SystemRole):
    """
    AI-CORE-BEGIN
    ROLE: System-level role fixture for the access-cascade drawing.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture, never an assignable role.
    AI-CORE-END
    """

    name = "access_cascade_system_gate"
    description = "System-level role fixture: the engine sentinel branch the drawing shows"
