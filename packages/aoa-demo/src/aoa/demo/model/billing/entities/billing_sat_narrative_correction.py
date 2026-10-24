# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_narrative_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_canonical_row_artifact import BillingCanonicalRowArtifactCoreEntity
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Narrative correction attached to canonical ingest row", domain=BillingDomain)
class NarrativeCorrectionCoreEntity(BaseCoreEntity):
    id: str = Field(description="Row id")
    lifecycle: BillingDenseLifecycle = Field(description="Correction lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    canonical_row: Annotated[
        AssociationOne[BillingCanonicalRowArtifactCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parent canonical ingest artifact"
    )

    correction_reason_code: str = Field(description="Reason vocabulary key")
    editor_actor_id: str = Field(description="Actor approving narrative delta")
    prior_narrative_hash_hex: str = Field(description="Hash of pre-correction storyline")
    corrected_at_iso: str = Field(description="Correction applied at (UTC)")


NarrativeCorrectionCoreEntity.model_rebuild()
