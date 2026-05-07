# src/maxitor/samples/identity/entities/identity_phone_factor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle


@entity(description="Phone factor subgraph root orthogonal to email spine", domain=IdentityDomain)
class IdentityPhoneFactorEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Phone factor lifecycle")
    id: str = Field(description="Phone factor id")


IdentityPhoneFactorEntity.model_rebuild()
