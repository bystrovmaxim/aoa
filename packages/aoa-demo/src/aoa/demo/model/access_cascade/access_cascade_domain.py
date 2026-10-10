# packages/aoa-demo/src/aoa/demo/model/access_cascade/access_cascade_domain.py
"""
AccessCascadeDomain — the bounded context whose fixtures draw access-cascade shapes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``AccessCascadeDomain`` is the bounded context of the access-cascade
demonstrator. It carries no business meaning: every role, action and entity in
this domain exists to produce one shape Maxitor can draw — a cascade step, a
role chain, a matching path or a boundary. The drawing contract lives in
``specs/003-access-cascade-demonstrator/contracts/access-shapes.md``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    AccessCascadeDomain (marker)
        ├── roles/     — system, application and domain role branches
        ├── actions/   — one action per access-cascade shape
        └── entities/  — boundary-extreme entity fixtures

The domain is registered in ``aoa.demo.model.build._MODULES`` alongside the
other demo domains.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class AccessCascadeDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Bounded-context marker for the access-cascade drawing fixtures.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes; no
        member of this domain implies a business meaning.
    INVARIANTS: The domain exists for the diagram, not for a product.
    AI-CORE-END
    """

    name = "access_cascade"
    description = (
        "Drawing fixtures for access-cascade shapes: cascade steps, role chains, matching paths and boundaries"
    )
