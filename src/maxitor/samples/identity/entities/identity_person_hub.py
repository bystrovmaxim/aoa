# src/maxitor/samples/identity/entities/identity_person_hub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle


@entity(description="Person identity hub for credentials, factors, federation, and recovery", domain=IdentityDomain)
class IdentityPersonHubEntity(BaseEntity):
    id: str = Field(description="Person id")
    lifecycle: IdentityDenseLifecycle = Field(description="Person aggregate lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    acquisition_channel_anchor: Annotated[
        AssociationOne[AcquisitionChannelLedgerEntity],
        NoInverse(),
    ] = Rel(description="Acquisition ledger bridge for federation and marketing checks")  # type: ignore[assignment]

IdentityPersonHubEntity.model_rebuild()
