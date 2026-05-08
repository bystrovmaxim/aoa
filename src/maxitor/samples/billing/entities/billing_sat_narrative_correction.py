# src/maxitor/samples/billing/entities/billing_sat_narrative_correction.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_canonical_row_artifact import BillingCanonicalRowArtifactEntity
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle


@entity(description="Narrative correction attached to canonical ingest row", domain=BillingDomain)
class NarrativeCorrectionEntity(BaseEntity):
    id: str = Field(description="Row id")
    lifecycle: BillingDenseLifecycle = Field(description="Correction lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    canonical_row: Annotated[
        AssociationOne[BillingCanonicalRowArtifactEntity],
        NoInverse(),
    ] = Rel(description="Parent canonical ingest artifact")  # type: ignore[assignment]

    correction_reason_code: str = Field(description="Reason vocabulary key")
    editor_actor_id: str = Field(description="Actor approving narrative delta")
    prior_narrative_hash_hex: str = Field(description="Hash of pre-correction storyline")
    corrected_at_iso: str = Field(description="Correction applied at (UTC)")


NarrativeCorrectionEntity.model_rebuild()
