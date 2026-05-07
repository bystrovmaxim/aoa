# src/maxitor/samples/identity/entities/identity_federated_linkage.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_email_factor import IdentityEmailFactorEntity


@entity(description="Federated IdP linkage on email spine continuation", domain=IdentityDomain)
class IdentityFederatedLinkageEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Federated linkage lifecycle")
    id: str = Field(description="Linkage id")

    email_factor: Annotated[
        AssociationOne[IdentityEmailFactorEntity],
        NoInverse(),
    ] = Rel(description="Upstream email credential row")  # type: ignore[assignment]


IdentityFederatedLinkageEntity.model_rebuild()
