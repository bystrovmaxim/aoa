# packages/aoa-examples/src/aoa/examples/model/settlement_desks/entities/clearing_instruction_row_entity.py
"""Netting mandate row produced by chartered clearing steward."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.settlement_desks.settlement_desks_domain import SettlementDesksDomain


@entity(description="Corporate clearing netting instruction", domain=SettlementDesksDomain)
class ClearingInstructionRowEntity(BaseEntity):
    instruction_key: str = Field(description="Reference into clearing charter")
    notional_ceiling_minor: int = Field(description="Maximum open notional in minor currency units", ge=0)
    allowed_venues_stub: str = Field(description="Serialized venue bitmask placeholder")
