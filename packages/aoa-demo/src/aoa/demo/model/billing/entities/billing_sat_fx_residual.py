# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_fx_residual.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sat_narrative_correction import NarrativeCorrectionCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="FX residual facet continuing ingest narrative spine", domain=BillingDomain)
class FxResidualTagCoreEntity(BaseCoreEntity):
    id: str = Field(description="Residual id")
    lifecycle: BillingDenseLifecycle = Field(description="FX residual lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    narrative: Annotated[
        AssociationOne[NarrativeCorrectionCoreEntity],
        NoInverse(),
    ] = Field(
        description="Upstream narrative correction"
    )

    quote_currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency used for hedge quote")
    base_amount_minor: int = Field(description="Amount in transactional currency minors", ge=0)
    residual_amount_minor: int = Field(description="Post-conversion rounding residual", ge=0)
    fx_feed_provider: str = Field(description="Rate feed supplier code")


FxResidualTagCoreEntity.model_rebuild()
