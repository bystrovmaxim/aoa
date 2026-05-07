# src/maxitor/samples/billing/entities/billing_sat_acquirer_integrity.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.retrieval_evidence_bundle import RetrievalEvidenceBundleEntity


@entity(description="Acquirer integrity checkpoint between retrieval artefact and arbitration brief", domain=BillingDomain)
class AcquirerIntegrityCheckEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Integrity check lifecycle")
    id: str = Field(description="Checkpoint id")

    evidence_bundle: Annotated[
        AssociationOne[RetrievalEvidenceBundleEntity],
        NoInverse(),
    ] = Rel(description="Parent retrieval submission bundle")  # type: ignore[assignment]


AcquirerIntegrityCheckEntity.model_rebuild()
