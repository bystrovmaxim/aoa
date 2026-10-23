# packages/aoa-demo/src/aoa/demo/model/billing/entities/retrieval_evidence_bundle.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.chargeback_ticket import ChargebackTicketCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Retrieval / representment bundle", domain=BillingDomain)
class RetrievalEvidenceBundleCoreEntity(BaseCoreEntity):
    id: str = Field(description="Bundle id")
    lifecycle: BillingDenseLifecycle = Field(description="Bundle lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    chargeback_ticket: Annotated[
        AssociationOne[ChargebackTicketCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parent dispute ticket"
    )

    bundle_kind: str = Field(description="Evidence bundle category")
    retrieval_deadline_iso: str = Field(description="Cutoff for representment package (UTC)")
    exhibits_count: int = Field(description="Attached exhibit count", ge=0)
    sealed: bool = Field(description="Whether bundle is cryptographically sealed")


RetrievalEvidenceBundleCoreEntity.model_rebuild()
