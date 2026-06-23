# packages/aoa-examples/src/aoa/examples/model/settlement_desks/entities/desk_lane_exposure_marker_entity.py
"""Exposure marker aligning a clearing instruction slice to venue lane."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.settlement_desks.entities.clearing_instruction_row_entity import ClearingInstructionRowEntity
from aoa.examples.model.settlement_desks.settlement_desks_domain import SettlementDesksDomain


@entity(description="Desk-specific exposure marker keyed off clearing instruction slices", domain=SettlementDesksDomain)
class DeskLaneExposureMarkerEntity(BaseEntity):
    marker_id: str = Field(description="Exposure marker surrogate key")
    venue_lane: str = Field(description="atlantic_wire | pac_settlement_hub | synthetic")
    open_notional_stub: float = Field(description="Running exposure snapshot", ge=0)
    instruction_anchor: Annotated[
        AssociationOne[ClearingInstructionRowEntity],
        NoInverse(),
    ] = Rel(
        description="Clearing instruction slice this marker amortises across"
    )  # type: ignore[assignment]
