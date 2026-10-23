# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_mesh_parse_interchange.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_parse_pass import BillingParsePassCoreEntity
from aoa.demo.model.billing.entities.billing_sat_interchange_slice import InterchangeAssessmentSliceCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Bridge joining parser lifecycle with interchange economics island", domain=BillingDomain)
class BillingParseInterchangeBridgeCoreEntity(BaseCoreEntity):
    id: str = Field(description="Bridge id")
    lifecycle: BillingDenseLifecycle = Field(description="Bridge lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    parse_pass: Annotated[
        AssociationOne[BillingParsePassCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parser spine anchor"
    )

    interchange_slice: Annotated[
        AssociationOne[InterchangeAssessmentSliceCoreEntity],
        NoInverse(),
    ] = Field(
        description="Interchange economics anchor"
    )

    bridge_quality_tier: str = Field(description="Sync quality tier label")
    last_synced_at_iso: str = Field(description="Last successful bridge refresh (UTC)")
    reconcile_audit_token: str = Field(description="Cross-check token for auditors")


BillingParseInterchangeBridgeCoreEntity.model_rebuild()
