# packages/aoa-demo/src/aoa/demo/model/settlement_desks/resources/storage.py
"""SettlementDesksStorage — the store that holds the settlement desks domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.settlement_desks.entities.clearing_instruction_row_entity import ClearingInstructionRowDetailEntity
from aoa.demo.model.settlement_desks.entities.desk_lane_exposure_marker_entity import DeskLaneExposureMarkerCoreEntity


@meta(description="Stores the settlement desks model (stub)")
@entities(
    ClearingInstructionRowDetailEntity,
    DeskLaneExposureMarkerCoreEntity,
)
class SettlementDesksStorage(BaseStorage):
    """Hold the settlement desks domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
