# packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_credential_merge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.identity.domain import IdentityDomain
from aoa.demo.model.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.demo.model.identity.entities.identity_email_factor import IdentityEmailFactorCoreEntity
from aoa.demo.model.identity.entities.identity_person_hub import IdentityPersonHubCoreEntity
from aoa.demo.model.identity.entities.identity_phone_factor import IdentityPhoneFactorCoreEntity


@entity(description="Credential merge correlate across person, email, and phone factors", domain=IdentityDomain)
class IdentityCredentialMergeCorrelateCoreEntity(BaseCoreEntity):
    id: str = Field(description="Correlate id")
    lifecycle: IdentityDenseLifecycle = Field(description="Merge correlate lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    email_factor: Annotated[
        AssociationOne[IdentityEmailFactorCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Email credential anchor"
    )  # type: ignore[assignment]

    phone_factor: Annotated[
        AssociationOne[IdentityPhoneFactorCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Phone credential anchor"
    )  # type: ignore[assignment]

    person: Annotated[
        AssociationOne[IdentityPersonHubCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Merged person identity"
    )  # type: ignore[assignment]


IdentityCredentialMergeCorrelateCoreEntity.model_rebuild()
