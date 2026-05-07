# src/maxitor/samples/billing/entities/billing_sat_acquirer_integrity.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.retrieval_evidence_bundle import RetrievalEvidenceBundleEntity


@entity(
    description="Acquirer integrity checkpoint between retrieval artefact and arbitration brief", domain=BillingDomain
)
class AcquirerIntegrityCheckEntity(BaseEntity):
    id: str = Field(description="Checkpoint id")
    lifecycle: BillingDenseLifecycle = Field(description="Integrity check lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    evidence_bundle: Annotated[
        AssociationOne[RetrievalEvidenceBundleEntity],
        NoInverse(),
    ] = Rel(description="Parent retrieval submission bundle")  # type: ignore[assignment]

    checkpoint_kind: str = Field(description="Integrity gate kind (PAN, CSC, MID)")
    adjudication_outcome: str = Field(description="Rule outcome shorthand")
    checked_at_iso: str = Field(description="Checkpoint evaluated at (UTC)")
    risk_score: int = Field(description="0-100 calibrated risk heuristic", ge=0, le=100)


AcquirerIntegrityCheckEntity.model_rebuild()
