# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/domain.py
"""
EntityProjectionDemoDomain — bounded context for ``BaseEntity.schema()`` samples.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Isolated demo domain so Maxitor can show customer/order entities plus an action
whose ``Result`` exposes a partial JSON projection of ``ProjectionDemoOrderEntity``.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class EntityProjectionDemoDomain(BaseDomain):
    name = "entity_projection_demo"
    description = "Sample slice for entity wire projections (partial order JSON in action results)"
