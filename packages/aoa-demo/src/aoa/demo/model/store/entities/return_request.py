# packages/aoa-demo/src/aoa/demo/model/store/entities/return_request.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.analytics.entities.analytics_ingress_batch import AnalyticsIngressBatchCoreEntity
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity
from aoa.demo.model.store.entities.sales_order_lifecycle import SalesOrderLifecycle
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Return request row", domain=StoreDomain)
class ReturnRequestCoreEntity(BaseCoreEntity):
    id: str = Field(description="Return request id")
    lifecycle: SalesOrderLifecycle = Field(description="Return lifecycle")
    reason: str = Field(description="Return reason")
    status: str = Field(description="Return status")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Field(
        description="Returned order"
    )

    reverse_logistics_metrics_batch: Annotated[
        AssociationOne[AnalyticsIngressBatchCoreEntity],
        NoInverse(),
    ] = Field(
        description="Analytics ingress shard for reverse-logistics telemetry"
    )


ReturnRequestCoreEntity.model_rebuild()
