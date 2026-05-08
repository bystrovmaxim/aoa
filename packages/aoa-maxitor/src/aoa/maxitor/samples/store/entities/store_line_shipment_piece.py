# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/store_line_shipment_piece.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLineLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity, SalesOrderLineEntity


@entity(description="Shipment piece bridging line + header (dense mesh cue)", domain=StoreDomain)
class LineShipmentPieceEntity(BaseEntity):
    id: str = Field(description="Piece id")
    lifecycle: SalesOrderLineLifecycle = Field(description="Shipment piece lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order_line: Annotated[
        AssociationOne[SalesOrderLineEntity],
        NoInverse(),
    ] = Rel(description="Line anchor")  # type: ignore[assignment]

    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent order duplicate anchor")  # type: ignore[assignment]


LineShipmentPieceEntity.model_rebuild()
