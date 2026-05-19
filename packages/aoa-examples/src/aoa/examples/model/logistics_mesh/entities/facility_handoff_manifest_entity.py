# packages/aoa-examples/src/aoa/examples/model/logistics_mesh/entities/facility_handoff_manifest_entity.py
"""Hand-off manifest aligning seal numbers to waypoint legs."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.logistics_mesh.entities.freight_waypoint_leg_entity import FreightWaypointLegEntity
from aoa.examples.model.logistics_mesh.logistics_mesh_domain import LogisticsMeshDomain


@entity(description="Cross-dock hand-off manifest row", domain=LogisticsMeshDomain)
class FacilityHandoffManifestEntity(BaseEntity):
    manifest_id: str = Field(description="Cargo manifest surrogate key")
    customs_seal_stub: str = Field(description="Tamper-evident seal token")
    next_leg_placeholder: Annotated[
        AssociationOne[FreightWaypointLegEntity],
        NoInverse(),
    ] = Rel(description="Next relay leg reserved for cargo slice")  # type: ignore[assignment]
