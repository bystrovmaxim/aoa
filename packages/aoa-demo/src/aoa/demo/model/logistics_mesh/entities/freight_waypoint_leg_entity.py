# packages/aoa-demo/src/aoa/demo/model/logistics_mesh/entities/freight_waypoint_leg_entity.py
"""Single hop along facility relay mesh."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@entity(description="Facility relay hop with synthetic mileage + dwell metrics", domain=LogisticsMeshDomain)
class FreightWaypointLegEntity(BaseEntity):
    waypoint_id: str = Field(description="Hop surrogate identifier")
    mode_stub: str = Field(description="dray | linehaul_short | shuttle")
    dwell_minutes: int = Field(description="Planned dwell for swap activity", ge=0)
