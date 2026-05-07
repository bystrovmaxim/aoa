# src/maxitor/samples/billing/entities/billing_mesh_chargeback_ingest.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestEntity
from maxitor.samples.billing.entities.chargeback_ticket import ChargebackTicketEntity


@entity(
    description="Cross-spine correlate row wiring dispute artefacts to ingestion manifests (medium mesh)",
    domain=BillingDomain,
)
class BillingChargebackIngestCorrelateEntity(BaseEntity):
    lifecycle: BillingDenseLifecycle = Field(description="Correlate lifecycle")
    id: str = Field(description="Correlate id")

    dispute: Annotated[
        AssociationOne[ChargebackTicketEntity],
        NoInverse(),
    ] = Rel(description="Dispute ticket anchor")  # type: ignore[assignment]

    ingest_manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Ingest workload anchor")  # type: ignore[assignment]


BillingChargebackIngestCorrelateEntity.model_rebuild()
