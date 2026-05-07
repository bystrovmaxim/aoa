# src/maxitor/samples/catalog/entities/catalog_acquisition_channel_ledger.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Acquisition channel attribution ledger head", domain=CatalogDomain)
class AcquisitionChannelLedgerEntity(BaseEntity):
    id: str = Field(description="Ledger id")
    lifecycle: CatalogDenseLifecycle = Field(description="Channel ledger lifecycle")


AcquisitionChannelLedgerEntity.model_rebuild()
