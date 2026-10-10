# packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_application_roles.py
"""
Cascade application roles — the four-level application chain of the access-cascade drawing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The four roles form one inheritance chain under ``ApplicationRole``. The
chain exists so the diagram draws ``parent_role`` edges several levels deep
instead of isolated role nodes; none of the names is a business duty.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ApplicationRole
        └── CascadeStaffRole
                └── CascadeOfficerRole
                        └── CascadeLineLeadRole
                                └── CascadeTraineeRole
"""

from __future__ import annotations

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class CascadeStaffRole(ApplicationRole):
    """
    AI-CORE-BEGIN
    ROLE: Root of the drawn application-level role chain.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is the chain it starts.
    AI-CORE-END
    """

    name = "access_cascade_staff"
    description = "Application-level chain root: the first level of the drawn hierarchy"


@role_mode(RoleMode.ALIVE)
class CascadeOfficerRole(CascadeStaffRole):
    """
    AI-CORE-BEGIN
    ROLE: Second link of the drawn application-level role chain.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is its place in the chain.
    AI-CORE-END
    """

    name = "access_cascade_officer"
    description = "Application-level chain link: child of CascadeStaffRole — the second drawn level"


@role_mode(RoleMode.ALIVE)
class CascadeLineLeadRole(CascadeOfficerRole):
    """
    AI-CORE-BEGIN
    ROLE: Third link of the drawn application-level role chain.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is its place in the chain.
    AI-CORE-END
    """

    name = "access_cascade_line_lead"
    description = "Application-level chain link: child of CascadeOfficerRole — the third drawn level"


@role_mode(RoleMode.ALIVE)
class CascadeTraineeRole(CascadeLineLeadRole):
    """
    AI-CORE-BEGIN
    ROLE: Leaf of the drawn application-level role chain.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is the fourth chain level.
    AI-CORE-END
    """

    name = "access_cascade_trainee"
    description = "Application-level chain leaf: child of CascadeLineLeadRole — the fourth drawn level"
