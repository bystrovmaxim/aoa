# src/maxitor/samples/identity/entities/identity_person_hub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.identity.domain import IdentityDomain
from maxitor.samples.identity.entities.id_dense_lifecycle import IdentityDenseLifecycle


@entity(description="Person identity hub for credentials, factors, federation, and recovery", domain=IdentityDomain)
class IdentityPersonHubEntity(BaseEntity):
    id: str = Field(description="Person id")
    lifecycle: IdentityDenseLifecycle = Field(description="Person aggregate lifecycle")

    acquisition_channel_anchor: Annotated[
        AssociationOne["AcquisitionChannelLedgerEntity"],  # noqa: UP037
        NoInverse(),
    ] = Rel(description="Acquisition ledger bridge for federation and marketing checks")  # type: ignore[assignment]


from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import (  # noqa: E402
    AcquisitionChannelLedgerEntity,
)

IdentityPersonHubEntity.model_rebuild()
