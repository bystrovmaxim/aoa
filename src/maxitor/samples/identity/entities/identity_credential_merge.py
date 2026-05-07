# src/maxitor/samples/identity/entities/identity_credential_merge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_email_factor import IdentityEmailFactorEntity
from maxitor.samples.identity.entities.identity_phone_factor import IdentityPhoneFactorEntity


@entity(description="Explicit merge correlate across disjoint credential subtrees (diamond apex without radial hub)", domain=IdentityDomain)
class IdentityCredentialMergeCorrelateEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Merge correlate lifecycle")
    id: str = Field(description="Correlate id")

    email_factor: Annotated[
        AssociationOne[IdentityEmailFactorEntity],
        NoInverse(),
    ] = Rel(description="Email credential anchor")  # type: ignore[assignment]

    phone_factor: Annotated[
        AssociationOne[IdentityPhoneFactorEntity],
        NoInverse(),
    ] = Rel(description="Phone credential anchor")  # type: ignore[assignment]


IdentityCredentialMergeCorrelateEntity.model_rebuild()
