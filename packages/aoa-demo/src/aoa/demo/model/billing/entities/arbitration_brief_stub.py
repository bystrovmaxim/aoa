# packages/aoa-demo/src/aoa/demo/model/billing/entities/arbitration_brief_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_sat_acquirer_integrity import AcquirerIntegrityCheckCoreEntity


@entity(description="Arbitration brief following acquirer integrity checkpoint", domain=BillingDomain)
class ArbitrationBriefStubCoreEntity(BaseCoreEntity):
    id: str = Field(description="Brief id")
    lifecycle: BillingDenseLifecycle = Field(description="Brief lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    integrity_checkpoint: Annotated[
        AssociationOne[AcquirerIntegrityCheckCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Upstream acquirer integrity artefact"
    )  # type: ignore[assignment]

    dispute_stage: str = Field(description="Arbitration stage label")
    claimant_reference: str = Field(description="Internal claimant handle")
    respondent_reference: str = Field(description="Network / acquirer handle")
    filing_deadline_iso: str = Field(description="Submission deadline (UTC ISO-8601)")


ArbitrationBriefStubCoreEntity.model_rebuild()
