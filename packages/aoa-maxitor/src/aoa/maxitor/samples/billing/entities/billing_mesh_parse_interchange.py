# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_mesh_parse_interchange.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.billing_parse_pass import BillingParsePassEntity
from aoa.maxitor.samples.billing.entities.billing_sat_interchange_slice import InterchangeAssessmentSliceEntity


@entity(description="Bridge joining parser lifecycle with interchange economics island", domain=BillingDomain)
class BillingParseInterchangeBridgeEntity(BaseEntity):
    id: str = Field(description="Bridge id")
    lifecycle: BillingDenseLifecycle = Field(description="Bridge lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    parse_pass: Annotated[
        AssociationOne[BillingParsePassEntity],
        NoInverse(),
    ] = Rel(description="Parser spine anchor")  # type: ignore[assignment]

    interchange_slice: Annotated[
        AssociationOne[InterchangeAssessmentSliceEntity],
        NoInverse(),
    ] = Rel(description="Interchange economics anchor")  # type: ignore[assignment]

    bridge_quality_tier: str = Field(description="Sync quality tier label")
    last_synced_at_iso: str = Field(description="Last successful bridge refresh (UTC)")
    reconcile_audit_token: str = Field(description="Cross-check token for auditors")


BillingParseInterchangeBridgeEntity.model_rebuild()
