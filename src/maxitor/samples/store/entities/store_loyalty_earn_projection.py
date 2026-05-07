# src/maxitor/samples/store/entities/store_loyalty_earn_projection.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle


@entity(description="Loyalty earn projection keyed off invoicing artefacts (distinct from header mesh)", domain=StoreDomain)
class LoyaltyEarnProjectionEntity(BaseEntity):
    id: str = Field(description="Projection id")
    lifecycle: SalesOrderLifecycle = Field(description="Projection lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Owning invoice artefact")  # type: ignore[assignment]


LoyaltyEarnProjectionEntity.model_rebuild()
