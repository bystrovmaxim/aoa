# packages/aoa-maxitor/src/aoa/maxitor/samples/identity/entities/identity_credential_rotation_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.identity.domain import IdentityDomain
from aoa.maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity
from aoa.maxitor.samples.identity.entities.identity_phone_factor import IdentityPhoneFactorEntity


@entity(description="Credential rotation bookkeeping for a person and phone factor", domain=IdentityDomain)
class IdentityCredentialRotationStubEntity(BaseEntity):
    id: str = Field(description="Stub id")
    lifecycle: IdentityDenseLifecycle = Field(description="Rotation stub lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    phone_factor: Annotated[
        AssociationOne[IdentityPhoneFactorEntity],
        NoInverse(),
    ] = Rel(description="Upstream phone factor row")  # type: ignore[assignment]

    person: Annotated[
        AssociationOne[IdentityPersonHubEntity],
        NoInverse(),
    ] = Rel(description="Credential owner")  # type: ignore[assignment]


IdentityCredentialRotationStubEntity.model_rebuild()
