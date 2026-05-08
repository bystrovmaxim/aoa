# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_canonical_row_artifact.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.billing.domain import BillingDomain
from aoa.maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.maxitor.samples.billing.entities.billing_parse_pass import BillingParsePassEntity


@entity(description="Canonical row emitted from parser", domain=BillingDomain)
class BillingCanonicalRowArtifactEntity(BaseEntity):
    id: str = Field(description="Artifact id")
    lifecycle: BillingDenseLifecycle = Field(description="Row lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    parse_pass: Annotated[
        AssociationOne[BillingParsePassEntity],
        NoInverse(),
    ] = Rel(description="Originating parse pass")  # type: ignore[assignment]

    logical_row_key: str = Field(description="Dedup-stable business key emitted by parser")
    row_revision_no: int = Field(description="Monotonic intra-pass revision counter", ge=0)
    ingest_checksum_crc32c: str = Field(description="Payload checksum fingerprint")
    parser_profile_id: str = Field(description="Rulepack profile stamped on row")


BillingCanonicalRowArtifactEntity.model_rebuild()
