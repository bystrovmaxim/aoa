# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/store_order_deposit_allocation.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.invoice_record import InvoiceRecordEntity
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle


@entity(description="Deposit allocation keyed to invoice artefacts instead of repeating order spine only", domain=StoreDomain)
class DepositAllocationEntity(BaseEntity):
    id: str = Field(description="Allocation id")
    lifecycle: SalesOrderLifecycle = Field(description="Deposit allocation lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    invoice: Annotated[
        AssociationOne[InvoiceRecordEntity],
        NoInverse(),
    ] = Rel(description="Target invoice artefact")  # type: ignore[assignment]


DepositAllocationEntity.model_rebuild()
