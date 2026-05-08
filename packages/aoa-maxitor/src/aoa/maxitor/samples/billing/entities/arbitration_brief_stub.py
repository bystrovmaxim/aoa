# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/arbitration_brief_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.billing_sat_acquirer_integrity import AcquirerIntegrityCheckEntity


@entity(description="Arbitration brief following acquirer integrity checkpoint", domain=BillingDomain)
class ArbitrationBriefStubEntity(BaseEntity):
    id: str = Field(description="Brief id")
    lifecycle: BillingDenseLifecycle = Field(description="Brief lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    integrity_checkpoint: Annotated[
        AssociationOne[AcquirerIntegrityCheckEntity],
        NoInverse(),
    ] = Rel(description="Upstream acquirer integrity artefact")  # type: ignore[assignment]

    dispute_stage: str = Field(description="Arbitration stage label")
    claimant_reference: str = Field(description="Internal claimant handle")
    respondent_reference: str = Field(description="Network / acquirer handle")
    filing_deadline_iso: str = Field(description="Submission deadline (UTC ISO-8601)")


ArbitrationBriefStubEntity.model_rebuild()
