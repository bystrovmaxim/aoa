# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_acquirer_integrity.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.retrieval_evidence_bundle import RetrievalEvidenceBundleCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(
    description="Acquirer integrity checkpoint between retrieval artefact and arbitration brief", domain=BillingDomain
)
class AcquirerIntegrityCheckCoreEntity(BaseCoreEntity):
    id: str = Field(description="Checkpoint id")
    lifecycle: BillingDenseLifecycle = Field(description="Integrity check lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    evidence_bundle: Annotated[
        AssociationOne[RetrievalEvidenceBundleCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parent retrieval submission bundle"
    )

    checkpoint_kind: str = Field(description="Integrity gate kind (PAN, CSC, MID)")
    adjudication_outcome: str = Field(description="Rule outcome shorthand")
    checked_at_iso: str = Field(description="Checkpoint evaluated at (UTC)")
    risk_score: int = Field(description="0-100 calibrated risk heuristic", ge=0, le=100)


AcquirerIntegrityCheckCoreEntity.model_rebuild()
