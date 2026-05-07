# src/maxitor/samples/identity/entities/identity_email_factor.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_person_hub import IdentityPersonHubEntity


@entity(description="Email credential factor for a person identity", domain=IdentityDomain)
class IdentityEmailFactorEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Email factor lifecycle")
    id: str = Field(description="Email factor id")

    person: Annotated[
        AssociationOne[IdentityPersonHubEntity],
        NoInverse(),
    ] = Rel(description="Owning person identity")  # type: ignore[assignment]


IdentityEmailFactorEntity.model_rebuild()
