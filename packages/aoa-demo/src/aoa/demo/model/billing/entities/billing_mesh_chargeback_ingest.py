# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_mesh_chargeback_ingest.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestCoreEntity
from aoa.demo.model.billing.entities.chargeback_ticket import ChargebackTicketCoreEntity
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


@entity(description="Correlate row wiring dispute artefacts to ingestion manifests", domain=BillingDomain)
class BillingChargebackIngestCorrelateCoreEntity(BaseCoreEntity):
    id: str = Field(description="Correlate id")
    lifecycle: BillingDenseLifecycle = Field(description="Correlate lifecycle")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    posting_timezone: str = Field(description="Business-calendar timezone identifier")
    dispute: Annotated[
        AssociationOne[ChargebackTicketCoreEntity],
        NoInverse(),
    ] = Field(
        description="Dispute ticket anchor"
    )

    ingest_manifest: Annotated[
        AssociationOne[BillingFileIngestManifestCoreEntity],
        NoInverse(),
    ] = Field(
        description="Ingest workload anchor"
    )

    correlate_confidence_bps: int = Field(description="Heuristic linkage confidence basis points", ge=0, le=10000)
    correlate_reason_code: str = Field(description="Why entities were bridged together")
    linkage_batch_id: str = Field(description="Batch id for pairwise correlator run")


BillingChargebackIngestCorrelateCoreEntity.model_rebuild()
