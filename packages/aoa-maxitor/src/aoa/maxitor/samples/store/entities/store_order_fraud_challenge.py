# packages/aoa-maxitor/src/aoa/maxitor/samples/store/entities/store_order_fraud_challenge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.store.domain import StoreDomain
from aoa.maxitor.samples.store.entities.lifecycle import SalesOrderLifecycle
from aoa.maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Step-up fraud challenge", domain=StoreDomain)
class FraudChallengeTicketEntity(BaseEntity):
    id: str = Field(description="FraudChallengeTicketEntity id")
    lifecycle: SalesOrderLifecycle = Field(description="FraudChallengeTicketEntity lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Parent sales order anchor")  # type: ignore[assignment]


FraudChallengeTicketEntity.model_rebuild()
