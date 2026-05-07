# src/maxitor/samples/identity/entities/identity_person_hub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_credential_rotation_stub import (
    IdentityCredentialRotationStubEntity,
)


@entity(description="Person aggregate tail on phone/spoke chain (distinct from email chain)", domain=IdentityDomain)
class IdentityPersonHubEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Person aggregate lifecycle")
    id: str = Field(description="Person id")

    rotation_stub: Annotated[
        AssociationOne[IdentityCredentialRotationStubEntity],
        NoInverse(),
    ] = Rel(description="Upstream rotation bookkeeping row")  # type: ignore[assignment]


IdentityPersonHubEntity.model_rebuild()
