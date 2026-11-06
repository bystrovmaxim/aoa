# packages/aoa-demo/src/aoa/demo/model/store/entities/store_order_risk_score.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.storefront_session_lifecycle import StorefrontSessionLifecycle
from aoa.demo.model.store.resources.storefront_session_cache_storage import StorefrontSessionCacheStorage


@entity(description="Per-order risk score snapshot", resource=StorefrontSessionCacheStorage)
class OrderRiskScoreCoreEntity(BaseCoreEntity):
    id: str = Field(description="OrderRiskScoreCoreEntity id")
    lifecycle: StorefrontSessionLifecycle = Field(description="OrderRiskScoreCoreEntity lifecycle")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    shipment_carrier_hint: str = Field(description="Preferred carrier mnemonic for planners")
    lineage_batch_token: str = Field(description="Correlation handle shared across mesh bridges")


OrderRiskScoreCoreEntity.model_rebuild()
