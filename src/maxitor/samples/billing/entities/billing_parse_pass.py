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
    id: str = Field(description="Parse pass id")
    lifecycle: BillingPipelineLifecycle = Field(description="Parse lifecycle")

    manifest: Annotated[
        AssociationOne[BillingFileIngestManifestEntity],
        NoInverse(),
    ] = Rel(description="Source manifest")  # type: ignore[assignment]

    fx_residual_tag: Annotated[
        AssociationOne["FxResidualTagEntity"],  # noqa: F821, UP037
        NoInverse(),
    ] = Rel(description="FX residual tag linked to this parse pass")  # type: ignore[assignment]

    retrieval_evidence_bundle: Annotated[
        AssociationOne["RetrievalEvidenceBundleEntity"],  # noqa: F821, UP037
        NoInverse(),
    ] = Rel(description="Retrieval evidence bundle associated with parse outcome")  # type: ignore[assignment]

    parser_semver: str = Field(description="Parser implementation semantic version")
    pass_sequence_no: int = Field(description="Monotonic retry index for same manifest hash", ge=0)
    diagnostics_uri: str = Field(description="Pointer to diagnostics bundle")
    wallclock_elapsed_ms: int = Field(description="Observed ingest duration milliseconds", ge=0)

    bytes_scanned_total: int = Field(description="Total bytes inspected from manifest payload", ge=0)
    records_emitted_estimate: int = Field(description="Heuristic emitted logical row estimate", ge=0)
    quarantine_candidate: bool = Field(description="Parser marks output for containment review")
    parser_feature_flags_hex: str = Field(description="Bitfield of enabled parser knobs (hex string)")
    host_partition_slug: str = Field(description="Horizontal shard slug executing this pass")
