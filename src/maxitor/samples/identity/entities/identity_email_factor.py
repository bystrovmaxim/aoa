# src/maxitor/samples/identity/entities/identity_email_factor.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle


@entity(description="Email factor subgraph root — no shared credential hub FK", domain=IdentityDomain)
class IdentityEmailFactorEntity(BaseEntity):
    lifecycle: IdentityDenseLifecycle = Field(description="Email factor lifecycle")
    id: str = Field(description="Email factor id")


IdentityEmailFactorEntity.model_rebuild()
