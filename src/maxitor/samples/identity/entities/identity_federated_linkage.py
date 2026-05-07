# src/maxitor/samples/identity/entities/identity_federated_linkage.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_email_factor import IdentityEmailFactorEntity
from maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity


@entity(description="Federated IdP linkage for a person and optional email credential factor", domain=IdentityDomain)
class IdentityFederatedLinkageEntity(BaseEntity):
    id: str = Field(description="Linkage id")
    lifecycle: IdentityDenseLifecycle = Field(description="Federated linkage lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    email_factor: Annotated[
        AssociationOne[IdentityEmailFactorEntity],
        NoInverse(),
    ] = Rel(description="Upstream email credential row")  # type: ignore[assignment]

    person: Annotated[
        AssociationOne[IdentityPersonHubEntity],
        NoInverse(),
    ] = Rel(description="Federated account owner")  # type: ignore[assignment]


IdentityFederatedLinkageEntity.model_rebuild()
