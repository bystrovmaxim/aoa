# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/retrieval_evidence_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.chargeback_ticket import ChargebackTicketEntity


@entity(description="Retrieval / representment bundle", domain=BillingDomain)
class RetrievalEvidenceBundleEntity(BaseEntity):
    id: str = Field(description="Bundle id")
    lifecycle: BillingDenseLifecycle = Field(description="Bundle lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    chargeback_ticket: Annotated[
        AssociationOne[ChargebackTicketEntity],
        NoInverse(),
    ] = Rel(description="Parent dispute ticket")  # type: ignore[assignment]

    bundle_kind: str = Field(description="Evidence bundle category")
    retrieval_deadline_iso: str = Field(description="Cutoff for representment package (UTC)")
    exhibits_count: int = Field(description="Attached exhibit count", ge=0)
    sealed: bool = Field(description="Whether bundle is cryptographically sealed")


RetrievalEvidenceBundleEntity.model_rebuild()
