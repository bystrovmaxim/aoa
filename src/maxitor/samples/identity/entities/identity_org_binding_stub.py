# src/maxitor/samples/identity/entities/identity_org_binding_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle
from maxitor.samples.identity.entities.identity_federated_linkage import IdentityFederatedLinkageEntity


@entity(description="Org binding continuing federated lineage (still no radial hub)", domain=IdentityDomain)
class IdentityOrgBindingStubEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Org binding lifecycle")
    id: str = Field(description="Binding id")

    federated_linkage: Annotated[
        AssociationOne[IdentityFederatedLinkageEntity],
        NoInverse(),
    ] = Rel(description="Parent federated linkage row")  # type: ignore[assignment]


IdentityOrgBindingStubEntity.model_rebuild()
