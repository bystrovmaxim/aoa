# src/maxitor/samples/billing/entities/retrieval_evidence_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.chargeback_ticket import ChargebackTicketEntity


@entity(description="Retrieval / representment bundle", domain=BillingDomain)
class RetrievalEvidenceBundleEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Bundle lifecycle")
    id: str = Field(description="Bundle id")

    chargeback_ticket: Annotated[
        AssociationOne[ChargebackTicketEntity],
        NoInverse(),
    ] = Rel(description="Parent dispute ticket")  # type: ignore[assignment]


RetrievalEvidenceBundleEntity.model_rebuild()
