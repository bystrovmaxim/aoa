# packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_dual_entry_origin.py
"""Demo entity whose lifecycle has two distinct initial states (see ``StoreDualEntryLifecycle``)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity
from aoa.demo.model.store.entities.store_dual_entry_lifecycle import StoreDualEntryLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(
    description="Trace row for orders that may originate online or as a walk-in quote (dual-entry demo)",
    domain=StoreDomain,
)
class OrderDualEntryOriginTraceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Origin trace id")
    lifecycle: StoreDualEntryLifecycle = Field(description="Dual-entry origin lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")
    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Field(
        description="Related order aggregate for this origin trace"
    )


OrderDualEntryOriginTraceCoreEntity.model_rebuild()
