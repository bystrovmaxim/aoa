# packages/aoa-demo/src/aoa/demo/model/identity/entities/identity_org_binding_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.identity.domain import IdentityDomain
from aoa.demo.model.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from aoa.demo.model.identity.entities.identity_federated_linkage import IdentityFederatedLinkageCoreEntity
from aoa.demo.model.identity.entities.identity_person_hub import IdentityPersonHubCoreEntity


@entity(description="Organization binding for a person through a federated linkage", domain=IdentityDomain)
class IdentityOrgBindingStubCoreEntity(BaseCoreEntity):
    id: str = Field(description="Binding id")
    lifecycle: IdentityDenseLifecycle = Field(description="Org binding lifecycle")

    subject_handle: str = Field(description="Pseudonymous subject moniker for federation")
    risk_band: str = Field(description="Assurance tier surfaced to policy engines")
    last_seen_ip_hash: str = Field(description="Salted client-network fingerprint heuristic")
    mfa_saturation_pct: float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)
    recovery_budget_left: int = Field(description="Remaining recovery-token attempts envelope", ge=0)
    linkage_audit_seq: int = Field(description="Monotonic merge audit ticker", ge=0)
    federated_linkage: Annotated[
        AssociationOne[IdentityFederatedLinkageCoreEntity],
        NoInverse(),
    ] = Field(
        description="Parent federated linkage row"
    )

    person: Annotated[
        AssociationOne[IdentityPersonHubCoreEntity],
        NoInverse(),
    ] = Field(
        description="Bound person identity"
    )


IdentityOrgBindingStubCoreEntity.model_rebuild()
