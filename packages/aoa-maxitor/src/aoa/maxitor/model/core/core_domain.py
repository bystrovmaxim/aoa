# packages/aoa-maxitor/src/aoa/maxitor/model/core/core_domain.py
"""
CoreDomain — bounded-context marker for Maxitor core surface.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declares a :class:`~aoa.action_machine.domain.base_domain.BaseDomain` subclass for
user management, authentication, authorization, and related core actions and entities
in the Maxitor model layer.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class CoreDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Marker domain for core platform capabilities in Maxitor (identity, authz).
    CONTRACT: ``name`` is ``core``; use with ``@meta(domain=CoreDomain)`` / ``@entity(domain=CoreDomain)``.
    INVARIANTS: Marker only — no I/O on the class.
    AI-CORE-END
    """

    name = "core"
    description = (
        "Core domain: user management, authentication, authorization, "
        "and other core functionalities"
    )
