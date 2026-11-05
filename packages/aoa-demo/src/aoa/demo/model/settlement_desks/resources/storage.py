# packages/aoa-demo/src/aoa/demo/model/settlement_desks/resources/storage.py
"""SettlementDesksStorage — the store that holds the settlement desks domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.settlement_desks.settlement_desks_domain import SettlementDesksDomain


@meta(description="Stores the settlement desks model (stub)", domain=SettlementDesksDomain)
class SettlementDesksStorage(BaseStorage):
    """Hold the settlement desks domain's entities; the demo never opens it."""
