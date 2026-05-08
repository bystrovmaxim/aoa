# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_consumable_sku_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from aoa.maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from aoa.maxitor.samples.clinical_supply.entities.cs_material_anchor import ClinicalMaterialAnchorEntity
from aoa.maxitor.samples.inventory.entities.inv_lot_snapshot_ledger import LotSnapshotLedgerEntity


@entity(
    description="Stock-keeping instrument row (detail / part master analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalConsumableSkuEntity(BaseEntity):
    id: str = Field(description="SKU id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="SKU lifecycle")

    sterility_claim_code: str = Field(description="Sterile-environment handling claim discriminator")
    lot_trace_handle: str = Field(description="Serialized trace corridor locator")
    temperature_ceiling_k: float = Field(description="Max allowed ambient storage kelvin snapshot")
    recall_watch_state: str = Field(description="Recall / embargo disposition label")
    quarantine_fence_id: str = Field(description="Facility quarantine corridor moniker")
    regulatory_territory: str = Field(description="Governing geography for distribution assertions")
    material_anchor: Annotated[
        AssociationOne[ClinicalMaterialAnchorEntity],
        NoInverse(),
    ] = Rel(description="Compound / sterility anchor")  # type: ignore[assignment]

    inventory_lot_mirror: Annotated[
        AssociationOne[LotSnapshotLedgerEntity],
        NoInverse(),
    ] = Rel(description="Inventory lot snapshot keyed for sterile consumable traceability")  # type: ignore[assignment]

ClinicalConsumableSkuEntity.model_rebuild()
