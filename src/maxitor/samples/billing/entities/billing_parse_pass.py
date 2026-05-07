# src/maxitor/samples/billing/entities/billing_parse_pass.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingPipelineLifecycle
from maxitor.samples.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestEntity


@entity(description="Parse pass artifact on ingest manifest", domain=BillingDomain)
class BillingParsePassEntity(BaseEntity):
    lifecycle: BillingPipelineLifecycle = Field(description="Parse lifecycle")
    id: str = Field(description="Parse pass id")

    manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Source manifest")  # type: ignore[assignment]


BillingParsePassEntity.model_rebuild()
