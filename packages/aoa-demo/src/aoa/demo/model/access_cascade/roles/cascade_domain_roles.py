# packages/aoa-demo/src/aoa/demo/model/access_cascade/roles/cascade_domain_roles.py
"""
Cascade domain roles — the two-level BaseRole branch of the access-cascade drawing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The two roles form a ``BaseRole`` branch apart from the application chain.
The branch exists so the diagram shows a second, shorter hierarchy path —
one of the two ways a role can match an operation.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole
        └── CascadeDomainRole
                └── CascadeDomainSpecialistRole
"""

from __future__ import annotations

from aoa.action_machine.auth import BaseRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class CascadeDomainRole(BaseRole):
    """
    AI-CORE-BEGIN
    ROLE: Root of the drawn domain-level role branch.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is the branch it starts.
    AI-CORE-END
    """

    name = "access_cascade_domain"
    description = "Domain-level branch root: a BaseRole branch apart from the application chain"


@role_mode(RoleMode.ALIVE)
class CascadeDomainSpecialistRole(CascadeDomainRole):
    """
    AI-CORE-BEGIN
    ROLE: Child of the drawn domain-level role branch.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes.
    INVARIANTS: A drawing fixture; its only meaning is the second branch level.
    AI-CORE-END
    """

    name = "access_cascade_domain_specialist"
    description = "Domain-level branch child: the second level of the domain branch chain"
