# packages/aoa-maxitor/src/aoa/maxitor/samples/identity/entities/identity_email_factor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.identity.domain import IdentityDomain
from aoa.maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity


@entity(description="Email credential factor for a person identity", domain=IdentityDomain)
class IdentityEmailFactorEntity(BaseEntity):
    id: str = Field(description="Email factor id")
    lifecycle: IdentityDenseLifecycle = Field(description="Email factor lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    person: Annotated[
        AssociationOne[IdentityPersonHubEntity],
        NoInverse(),
    ] = Rel(description="Owning person identity")  # type: ignore[assignment]


IdentityEmailFactorEntity.model_rebuild()
