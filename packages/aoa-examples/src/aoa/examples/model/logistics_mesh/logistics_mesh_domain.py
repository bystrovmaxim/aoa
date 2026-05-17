# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/logistics_mesh_domain.py
"""LogisticsMeshDomain — multi-hub freight hand-offs and relay orchestration."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class LogisticsMeshDomain(BaseDomain):
    """Cross-dock relay mesh with marshalling orchestration overlays."""

    name = "logistics_mesh"
    description = "Facility hand-offs, gated relay legs, orchestrated marshalling waves"
