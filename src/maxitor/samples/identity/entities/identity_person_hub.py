# src/maxitor/samples/identity/entities/identity_person_hub.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle


@entity(description="Person identity hub for credentials, factors, federation, and recovery", domain=IdentityDomain)
class IdentityPersonHubEntity(BaseEntity):
    id: str = Field(description="Person id")
    lifecycle: IdentityDenseLifecycle = Field(description="Person aggregate lifecycle")


IdentityPersonHubEntity.model_rebuild()
