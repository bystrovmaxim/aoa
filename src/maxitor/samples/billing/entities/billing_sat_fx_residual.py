# src/maxitor/samples/billing/entities/billing_sat_fx_residual.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_narrative_correction import NarrativeCorrectionEntity


@entity(description="FX residual facet continuing ingest narrative spine", domain=BillingDomain)
class FxResidualTagEntity(BaseEntity):
    id: str = Field(description="Residual id")
    lifecycle: BillingDenseLifecycle = Field(description="FX residual lifecycle")

    narrative: Annotated[
        AssociationOne[NarrativeCorrectionEntity],
        NoInverse(),
    ] = Rel(description="Upstream narrative correction")  # type: ignore[assignment]

    quote_currency_iso: str = Field(description="Currency used for hedge quote")
    base_amount_minor: int = Field(description="Amount in transactional currency minors", ge=0)
    residual_amount_minor: int = Field(description="Post-conversion rounding residual", ge=0)
    fx_feed_provider: str = Field(description="Rate feed supplier code")


FxResidualTagEntity.model_rebuild()
