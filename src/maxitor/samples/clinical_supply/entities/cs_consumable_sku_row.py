# src/maxitor/samples/clinical_supply/entities/cs_consumable_sku_row.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.clinical_supply.domain import ClinicalSupplyDomain
from maxitor.samples.clinical_supply.entities.cs_lifecycle import ClinicalSupplyLifecycle
from maxitor.samples.clinical_supply.entities.cs_material_anchor import ClinicalMaterialAnchorEntity


@entity(
    description="Stock-keeping instrument row (detail / part master analogue)",
    domain=ClinicalSupplyDomain,
)
class ClinicalConsumableSkuEntity(BaseEntity):
    id: str = Field(description="SKU id")
    lifecycle: ClinicalSupplyLifecycle = Field(description="SKU lifecycle")

    material_anchor: Annotated[
        AssociationOne[ClinicalMaterialAnchorEntity],
        NoInverse(),
    ] = Rel(description="Compound / sterility anchor")  # type: ignore[assignment]

    inventory_lot_mirror: Annotated[
        AssociationOne["LotSnapshotLedgerEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Inventory lot snapshot keyed for sterile consumable traceability")  # type: ignore[assignment]


from maxitor.samples.inventory.entities.inv_lot_snapshot_ledger import (  # noqa: E402
    LotSnapshotLedgerEntity,
)

ClinicalConsumableSkuEntity.model_rebuild()
