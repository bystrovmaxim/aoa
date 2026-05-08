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


@entity(description="Correlate row wiring dispute artefacts to ingestion manifests", domain=BillingDomain)
class BillingChargebackIngestCorrelateEntity(BaseEntity):
    id: str = Field(description="Correlate id")
    lifecycle: BillingDenseLifecycle = Field(description="Correlate lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    dispute: Annotated[
        AssociationOne[ChargebackTicketEntity],
        NoInverse(),
    ] = Rel(description="Dispute ticket anchor")  # type: ignore[assignment]

    ingest_manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Ingest workload anchor")  # type: ignore[assignment]

    correlate_confidence_bps: int = Field(description="Heuristic linkage confidence basis points", ge=0, le=10000)
    correlate_reason_code: str = Field(description="Why entities were bridged together")
    linkage_batch_id: str = Field(description="Batch id for pairwise correlator run")


BillingChargebackIngestCorrelateEntity.model_rebuild()
