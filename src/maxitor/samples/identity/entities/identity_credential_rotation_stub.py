# src/maxitor/samples/identity/entities/identity_credential_rotation_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity
from maxitor.samples.identity.entities.identity_phone_factor import IdentityPhoneFactorEntity


@entity(description="Credential rotation bookkeeping for a person and phone factor", domain=IdentityDomain)
class IdentityCredentialRotationStubEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Rotation stub lifecycle")
    id: str = Field(description="Stub id")

    phone_factor: Annotated[
        AssociationOne[IdentityPhoneFactorEntity],
        NoInverse(),
    ] = Rel(description="Upstream phone factor row")  # type: ignore[assignment]

    person: Annotated[
        AssociationOne[IdentityPersonHubEntity],
        NoInverse(),
    ] = Rel(description="Credential owner")  # type: ignore[assignment]


IdentityCredentialRotationStubEntity.model_rebuild()
